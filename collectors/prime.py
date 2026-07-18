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

ARCHIVE_URL = "https://www.primebank.com.bd/exchange-rate"


def get_latest_pdf():
    """
    Find the newest Prime Bank exchange-rate PDF.
    """

    response = requests.get(ARCHIVE_URL, timeout=20)
    response.raise_for_status()

    html = response.text

    pdfs = re.findall(
        r'https://www\.primebank\.com\.bd/assets/foreign-exchange/[^"]+?\.pdf',
        html,
    )

    if not pdfs:
        return None

    # Archive is newest first
    return pdfs[0]


def get_rate():
    """
    Collect EUR exchange rate from Prime Bank.

    Returns:
        dict | None
    """

    try:
        pdf_url = get_latest_pdf()

        if pdf_url is None:
            print("PRIME: Latest PDF not found.")
            return None

        pdf_bytes = download_pdf(pdf_url)

        text = extract_text_from_pdf(pdf_bytes)

        # Prime's filenames embed a human-readable date, e.g.
        # ".../1759038149-Rate%20Sheet%2028%20Sep%202025.pdf" — that's
        # a more reliable date source than anything printed in the body.
        rate_date = extract_rate_date(text, filename_hint=pdf_url)
        student = find_student_rate(text, "EUR")

        tables = extract_tables_from_pdf(pdf_bytes)

        row = find_currency_row(tables, "EUR")

        if row is None:
            print("PRIME: EUR row not found.")
            return None

        buy, sell = extract_buy_sell(row, buy_index=3, sell_index=0)

        if buy is None or sell is None:
            print(f"PRIME: EUR row found but values look wrong: {row}")
            return None

        result = {
            "bank": "PRIME",
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
        print(f"PRIME ERROR: {e}")
        return None


# --- v2.0 multi-currency support --------------------------------------
#
# Everything below is ADDITIVE: get_rate() above is completely untouched
# and still returns exactly what v1.0's main.py expects (EUR only).
# get_rates() reuses the same PDF fetch, generalized to any currency in it.

def get_rates(currencies=("EUR", "USD")):
    """
    Collect rates for multiple currencies from Prime Bank's daily PDF in
    a single fetch.
    """
    try:
        pdf_url = get_latest_pdf()

        if pdf_url is None:
            print("PRIME: Latest PDF not found (get_rates).")
            return []

        pdf_bytes = download_pdf(pdf_url)
        text = extract_text_from_pdf(pdf_bytes)
        rate_date = extract_rate_date(text, filename_hint=pdf_url)
        tables = extract_tables_from_pdf(pdf_bytes)

        results = []
        for currency in currencies:
            row = find_currency_row(tables, currency)

            if row is None:
                print(f"PRIME: {currency} row not found (get_rates).")
                continue

            buy, sell = extract_buy_sell(row, buy_index=3, sell_index=0)

            if buy is None or sell is None:
                print(f"PRIME: {currency} row found but values look wrong (get_rates): {row}")
                continue

            result = {
                "bank": "PRIME",
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
        print(f"PRIME ERROR (get_rates): {e}")
        return []
