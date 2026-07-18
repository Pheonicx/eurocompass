import re

from utils import http_client
from utils.pdf_utils import (
    download_pdf,
    extract_tables_from_pdf,
    extract_text_from_pdf,
    extract_buy_sell,
    extract_buy_sell_by_repetition,
    extract_rate_date,
    find_currency_row,
    find_student_rate,
    is_plausible_student_rate,
    is_stale,
    to_float,
)

TREASURY_URL = "https://www.bracbank.com/en/treasury/foreign-exchange"


def _get_pdf_url():
    """
    BRAC's treasury page links to their daily rate PDF (hosted on S3,
    filename embeds the date) from its footer — this is real, static
    HTML, not behind their site's client-side rendering, so it can be
    scraped directly.
    """
    response = http_client.get(TREASURY_URL, timeout=20)

    if response is None:
        return None

    match = re.search(
        r'https://brackweb\.s3[^\s"\')]+?Daily_Exchange_Rate[^\s"\')]+?\.pdf',
        response.text,
    )

    if not match:
        return None

    return match.group(0)


def _numbers_from_eur_line(text):
    """
    Finds the line of text starting at "EUR" and pulls out every
    plausible-looking decimal number on it. Kept separate from row
    parsing since BRAC's table is dense enough that pdfplumber's column
    boundaries aren't fully reliable — working from the flat list of
    numbers on the EUR line and letting the repetition pattern decide
    which are buy/sell has proven more robust in practice than trusting
    fixed positions.
    """
    match = re.search(r"EUR\b(.{0,150})", text)
    if not match:
        return []
    return [to_float(n) for n in re.findall(r"-?[0-9][0-9,]*\.[0-9]+", match.group(1))]


def _extract_eur_buy_sell(row, text):
    """
    Tries three strategies in order of reliability, verified against
    BRAC's actual PDF structure:
      1. Repetition pattern across the EUR row's own cells (most
         reliable — BRAC repeats identical TT rates across 2-3 columns).
      2. Repetition pattern across the raw EUR text line (same idea,
         used when table extraction doesn't cleanly split into a row).
      3. Fixed-index fallback as a last resort.
    """
    if row:
        row_numbers = [to_float(c) for c in row]
        buy, sell = extract_buy_sell_by_repetition(row_numbers)
        if buy is not None:
            return buy, sell

    line_numbers = _numbers_from_eur_line(text)
    buy, sell = extract_buy_sell_by_repetition(line_numbers)
    if buy is not None:
        return buy, sell

    if row:
        return extract_buy_sell(row, buy_index=3, sell_index=0)

    return None, None


def _get_rate_via_pdf():
    pdf_url = _get_pdf_url()

    if pdf_url is None:
        return None

    pdf_bytes = download_pdf(pdf_url)
    text = extract_text_from_pdf(pdf_bytes)

    rate_date = extract_rate_date(text, filename_hint=pdf_url)
    student = find_student_rate(text, "EUR")

    tables = extract_tables_from_pdf(pdf_bytes)
    row = find_currency_row(tables, "EUR")

    buy, sell = _extract_eur_buy_sell(row, text)

    if buy is None or sell is None:
        return None

    result = {
        "bank": "BRAC",
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


def _get_rate_via_embedded_json():
    """
    Older fallback method: BRAC's marketing page used to embed rate data
    directly as JSON inside the page. Kept as a second path in case the
    PDF link ever moves, since this has independently worked before.
    """
    response = http_client.get(TREASURY_URL, timeout=20)

    if response is None:
        return None

    html = response.text

    pattern = (
        r'\\\"currency\\\":\\\"EUR\\\",'
        r'\\\"buy\\\":([0-9.]+),'
        r'\\\"sell\\\":([0-9.]+)'
    )

    match = re.search(pattern, html)

    if not match:
        return None

    return {
        "bank": "BRAC",
        "currency": "EUR",
        "buy": float(match.group(1)),
        "sell": float(match.group(2)),
    }


def get_rate():
    """
    Collect EUR exchange rate from BRAC Bank.

    Returns:
        dict | None
    """

    try:
        result = _get_rate_via_pdf()

        if result is not None:
            return result

        print("BRAC: PDF method failed, trying embedded-JSON fallback.")

        result = _get_rate_via_embedded_json()

        if result is not None:
            return result

        print("BRAC: EUR data not found via either method.")
        return None

    except Exception as e:
        print(f"BRAC ERROR: {e}")
        return None


# --- v2.0 multi-currency support --------------------------------------
#
# Everything below is ADDITIVE: get_rate() above is completely untouched
# and still returns exactly what v1.0's main.py expects (EUR only).
# get_rates() reuses the same PDF fetch and the same proven extraction
# strategy, generalized to any currency in the PDF, so USD support costs
# zero extra requests to BRAC's servers.

def _numbers_from_currency_line(text, currency):
    match = re.search(rf"{re.escape(currency)}\b(.{{0,150}})", text)
    if not match:
        return []
    return [to_float(n) for n in re.findall(r"-?[0-9][0-9,]*\.[0-9]+", match.group(1))]


def _extract_currency_buy_sell(row, text, currency):
    if row:
        row_numbers = [to_float(c) for c in row]
        buy, sell = extract_buy_sell_by_repetition(row_numbers)
        if buy is not None:
            return buy, sell

    line_numbers = _numbers_from_currency_line(text, currency)
    buy, sell = extract_buy_sell_by_repetition(line_numbers)
    if buy is not None:
        return buy, sell

    if row:
        return extract_buy_sell(row, buy_index=3, sell_index=0)

    return None, None


def get_rates(currencies=("EUR", "USD")):
    """
    Collect rates for multiple currencies from BRAC's daily PDF in a
    single fetch.

    Returns:
        list[dict] — one entry per currency successfully extracted.
        A currency BRAC's PDF doesn't contain, or that fails to parse,
        is simply omitted, not treated as an error (same "prefer false
        warnings over false confidence" spirit as get_rate() above).
    """
    try:
        pdf_url = _get_pdf_url()
        if pdf_url is None:
            print("BRAC: PDF link not found (get_rates).")
            return []

        pdf_bytes = download_pdf(pdf_url)
        text = extract_text_from_pdf(pdf_bytes)
        tables = extract_tables_from_pdf(pdf_bytes)
        rate_date = extract_rate_date(text, filename_hint=pdf_url)

        results = []
        for currency in currencies:
            row = find_currency_row(tables, currency)
            buy, sell = _extract_currency_buy_sell(row, text, currency)

            if buy is None or sell is None:
                print(f"BRAC: {currency} row not found or unparsable (get_rates).")
                continue

            result = {
                "bank": "BRAC",
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
        print(f"BRAC ERROR (get_rates): {e}")
        return []
