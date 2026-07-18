import datetime
import re

import requests

from utils.pdf_utils import (
    download_pdf,
    extract_tables_from_pdf,
    extract_text_from_pdf,
    extract_buy_sell,
    extract_rate_date,
    find_currency_row,
    find_student_rate,
    is_plausible_student_rate,
    is_stale,
)

HOME_URL = "https://www.sonalibank.com.bd/"

# Confirmed by inspecting Sonali's actual published PDFs across many
# months (Jan/Apr/Jun/Sep/Dec examples all fit): the URL is fully
# predictable from the date. Constructing it directly is far more
# reliable than scraping the homepage for a link, which breaks the
# moment Sonali redesigns their homepage layout.
PDF_URL_PATTERN = "https://www.sonalibank.com.bd/upload/fxrate-{day:02d}-{month:02d}-{year}.pdf"


def _today_dhaka():
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    return (now_utc + datetime.timedelta(hours=6)).date()


def _candidate_urls_by_date():
    """
    Try today's date first, then yesterday's, in case the bank hasn't
    published today's sheet yet (common before their morning cutoff, or
    on a day the office was closed). Each candidate is paired with the
    date it corresponds to, so a fallback hit is correctly labeled as
    stale rather than mistaken for today's rate.
    """
    today = _today_dhaka()
    candidates = []
    for days_back in (0, 1, 2):
        d = today - datetime.timedelta(days=days_back)
        url = PDF_URL_PATTERN.format(day=d.day, month=d.month, year=d.year)
        candidates.append((url, d))
    return candidates


def get_latest_pdf_from_homepage():
    """
    Fallback discovery method: scrape the homepage for a PDF link.
    Only used if none of the predictable date-based URLs work — e.g.
    Sonali changes their upload path convention entirely.
    """
    response = requests.get(HOME_URL, timeout=20)
    response.raise_for_status()
    html = response.text

    match = re.search(
        r'href="(/upload/[^"]+?\.pdf)"',
        html,
        re.IGNORECASE,
    )

    if not match:
        return None

    return HOME_URL.rstrip("/") + match.group(1)


def get_rate():
    """
    Collect EUR exchange rate from Sonali Bank.
    """

    try:

        pdf_bytes = None
        pdf_url = None
        rate_date_hint = None

        # 1. Try the predictable date-based URL for today, then a couple
        #    of days back, before falling back to homepage scraping.
        for url, candidate_date in _candidate_urls_by_date():
            try:
                pdf_bytes = download_pdf(url, retries=2)
                pdf_url = url
                rate_date_hint = candidate_date.isoformat()
                break
            except requests.RequestException:
                continue

        # 2. Last resort: scrape the homepage for whatever link is there.
        if pdf_bytes is None:
            pdf_url = get_latest_pdf_from_homepage()
            if pdf_url is None:
                print("SONALI: No PDF found via date pattern or homepage.")
                return None
            pdf_bytes = download_pdf(pdf_url)

        text = extract_text_from_pdf(pdf_bytes)
        rate_date = extract_rate_date(text, filename_hint=pdf_url or rate_date_hint)
        student = find_student_rate(text, "EUR")

        # Sonali's table spells the currency out as "EURO" rather than the
        # ISO code "EUR" — find_currency_row now checks both, so this
        # should reliably succeed instead of falling through to the text
        # fallback below on every single run.
        tables = extract_tables_from_pdf(pdf_bytes)
        row = find_currency_row(tables, "EUR")

        buy = sell = None

        if row:
            buy, sell = extract_buy_sell(row, buy_index=3, sell_index=0)
            if buy is None or sell is None:
                print(f"SONALI: EUR row found but values look wrong: {row}")

        if buy is None or sell is None:
            # -----------------------------
            # Fallback for Sonali text PDF
            # -----------------------------
            # Only reached if the table itself couldn't be parsed at all
            # (e.g. Sonali switches to an image-only or non-tabular PDF).
            # The rate_validator sanity check still guards whatever this
            # produces before it can reach the site.
            pattern = (
                r"([0-9]+\.[0-9]+)\s+"
                r"([0-9]+\.[0-9]+)\s+"
                r"EURO\s+"
                r"([0-9]+\.[0-9]+)"
            )
            match = re.search(pattern, text, re.IGNORECASE)

            if not match:
                print("SONALI: EUR row not found.")
                return None

            sell = float(match.group(1))
            buy = float(match.group(3))

        result = {
            "bank": "SONALI",
            "currency": "EUR",
            "buy": buy,
            "sell": sell,
            "rate_date": rate_date.isoformat() if rate_date else None,
            "is_stale": is_stale(rate_date),
        }

        if student and is_plausible_student_rate(student, result["buy"], result["sell"]):
            result["student"] = student
        elif student:
            print(f"{result['bank']}: student rate found but looks implausible next to the normal rate, discarding: {student}")

        return result

    except Exception as e:
        print(f"SONALI ERROR: {e}")
        return None


# --- v2.0 multi-currency support --------------------------------------
#
# Everything below is ADDITIVE: get_rate() above is completely untouched
# and still returns exactly what v1.0's main.py expects (EUR only).
# get_rates() reuses the same PDF fetch, generalized to any currency in
# it. Note: Sonali's last-resort text-regex fallback (for when table
# extraction fails entirely) is written specifically for "EURO" and is
# not generalized here — if the table method fails, get_rates() simply
# omits whichever currency couldn't be found via the table, rather than
# guessing with a currency-specific regex that wasn't built for this.

def get_rates(currencies=("EUR", "USD")):
    """
    Collect rates for multiple currencies from Sonali's daily PDF in a
    single fetch.
    """
    try:
        pdf_bytes = None
        pdf_url = None
        rate_date_hint = None

        for url, candidate_date in _candidate_urls_by_date():
            try:
                pdf_bytes = download_pdf(url, retries=2)
                pdf_url = url
                rate_date_hint = candidate_date.isoformat()
                break
            except requests.RequestException:
                continue

        if pdf_bytes is None:
            pdf_url = get_latest_pdf_from_homepage()
            if pdf_url is None:
                print("SONALI: No PDF found via date pattern or homepage (get_rates).")
                return []
            pdf_bytes = download_pdf(pdf_url)

        text = extract_text_from_pdf(pdf_bytes)
        rate_date = extract_rate_date(text, filename_hint=pdf_url or rate_date_hint)
        tables = extract_tables_from_pdf(pdf_bytes)

        results = []
        for currency in currencies:
            row = find_currency_row(tables, currency)

            if row is None:
                print(f"SONALI: {currency} row not found (get_rates).")
                continue

            buy, sell = extract_buy_sell(row, buy_index=3, sell_index=0)

            if buy is None or sell is None:
                print(f"SONALI: {currency} row found but values look wrong (get_rates): {row}")
                continue

            result = {
                "bank": "SONALI",
                "currency": currency,
                "buy": buy,
                "sell": sell,
                "rate_date": rate_date.isoformat() if rate_date else None,
                "is_stale": is_stale(rate_date),
            }

            student = find_student_rate(text, currency)
            if student and is_plausible_student_rate(student, buy, sell):
                result["student"] = student

            results.append(result)

        return results

    except Exception as e:
        print(f"SONALI ERROR (get_rates): {e}")
        return []
