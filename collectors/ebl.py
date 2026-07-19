import datetime

from bs4 import BeautifulSoup
from utils import http_client
from utils.pdf_utils import (
    download_pdf,
    extract_text_from_pdf,
    extract_rate_date,
    find_student_rate,
    is_plausible_student_rate,
    is_stale,
)

# EBL's dated rate-sheet PDF, confirmed to follow a predictable filename
# pattern: Exchange_Rate_{day}_{Month}_{year}.pdf. Used only to pull the
# student-file rate and rate date — EBL's normal buy/sell already comes
# reliably from the HTML page below, so this is a pure bonus: if it
# fails for any reason, EBL's core rate is completely unaffected.
PDF_URL_PATTERN = "https://www.ebl.com.bd/assets/other/exchange/Exchange_Rate_{day}_{month}_{year}.pdf"


def _today_dhaka():
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    return (now_utc + datetime.timedelta(hours=6)).date()


def _get_student_and_date(normal_buy, normal_sell):
    today = _today_dhaka()

    for days_back in (0, 1, 2):
        d = today - datetime.timedelta(days=days_back)
        url = PDF_URL_PATTERN.format(day=d.day, month=d.strftime("%B"), year=d.year)

        try:
            pdf_bytes = download_pdf(url, retries=2)
        except Exception:
            continue

        text = extract_text_from_pdf(pdf_bytes)
        rate_date = extract_rate_date(text, filename_hint=url)
        student = find_student_rate(text, "EUR")

        extras = {}
        if rate_date:
            extras["rate_date"] = rate_date.isoformat()
            extras["is_stale"] = is_stale(rate_date)
        if student and is_plausible_student_rate(student, normal_buy, normal_sell):
            extras["student"] = student

        return extras

    return {}


def get_rate():
    url = "https://www.ebl.com.bd/forexrate"

    response = http_client.get(url)

    if response is None:
        return None

    soup = BeautifulSoup(response.text, "html.parser")

    rows = soup.find_all("tr")

    for row in rows:
        cells = row.find_all("td")

        if len(cells) >= 3:
            currency = cells[0].text.strip()

            if currency == "EUR":
                buying = cells[1].text.strip()
                selling = cells[2].text.strip()

                result = {
                    "bank": "EBL",
                    "currency": "EUR",
                    "buy": float(buying),
                    "sell": float(selling),
                }

                try:
                    extras = _get_student_and_date(result["buy"], result["sell"])
                    result.update(extras)
                except Exception as e:
                    print(f"EBL: student-rate/date bonus fetch failed (core rate unaffected): {e}")

                return result

    return None


# --- v2.0 multi-currency support --------------------------------------
#
# Everything below is ADDITIVE: get_rate() above is completely untouched
# and still returns exactly what v1.0's main.py expects (EUR only).
# get_rates() reuses the same HTML rates page, generalized to any
# currency listed in it.

def _get_student_and_date_for(currency, normal_buy, normal_sell):
    today = _today_dhaka()

    for days_back in (0, 1, 2):
        d = today - datetime.timedelta(days=days_back)
        url = PDF_URL_PATTERN.format(day=d.day, month=d.strftime("%B"), year=d.year)

        try:
            pdf_bytes = download_pdf(url, retries=2)
        except Exception:
            continue

        text = extract_text_from_pdf(pdf_bytes)
        rate_date = extract_rate_date(text, filename_hint=url)
        student = find_student_rate(text, currency)

        extras = {}
        if rate_date:
            extras["rate_date"] = rate_date.isoformat()
            extras["is_stale"] = is_stale(rate_date)
        if student and is_plausible_student_rate(student, normal_buy, normal_sell):
            extras["student"] = student

        return extras

    return {}


def get_rates(currencies=("EUR", "USD")):
    """
    Collect rates for multiple currencies from EBL's HTML rates table in
    a single page fetch.
    """
    try:
        url = "https://www.ebl.com.bd/forexrate"

        response = http_client.get(url)
        if response is None:
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        rows = soup.find_all("tr")

        found = {}
        for row in rows:
            cells = row.find_all("td")
            if len(cells) >= 3:
                currency = cells[0].text.strip()
                if currency in currencies and currency not in found:
                    try:
                        buy = float(cells[1].text.strip())
                        sell = float(cells[2].text.strip())
                    except ValueError:
                        continue
                    found[currency] = {"bank": "EBL", "currency": currency, "buy": buy, "sell": sell}

        results = []
        for currency in currencies:
            result = found.get(currency)
            if result is None:
                print(f"EBL: {currency} row not found (get_rates).")
                continue

            try:
                extras = _get_student_and_date_for(currency, result["buy"], result["sell"])
                result.update(extras)
            except Exception as e:
                print(f"EBL: student-rate/date bonus fetch failed for {currency} (core rate unaffected): {e}")

            results.append(result)

        return results

    except Exception as e:
        print(f"EBL ERROR (get_rates): {e}")
        return []
