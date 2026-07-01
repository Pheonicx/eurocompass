import re

import requests

from utils.pdf_utils import (
    download_pdf,
    extract_tables_from_pdf,
    find_currency_row,
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

        tables = extract_tables_from_pdf(pdf_bytes)

        row = find_currency_row(tables, "EUR")

        if row is None:
            print("PRIME: EUR row not found.")
            return None

        return {
            "bank": "PRIME",
            "currency": "EUR",
            "buy": float(row[3]),
            "sell": float(row[0]),
        }

    except Exception as e:
        print(f"PRIME ERROR: {e}")
        return None