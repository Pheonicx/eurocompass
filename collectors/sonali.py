import re

import requests

from utils.pdf_utils import (
    download_pdf,
    extract_tables_from_pdf,
    find_currency_row,
)

HOME_URL = "https://www.sonalibank.com.bd/"


def get_latest_pdf():
    """
    Find today's Sonali Bank FX-rate PDF.
    """

    response = requests.get(
        HOME_URL,
        timeout=20,
    )

    response.raise_for_status()

    html = response.text

    match = re.search(
        r'href="(/upload/fxrate-[^"]+?\.pdf)"',
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

        pdf_url = get_latest_pdf()

        if pdf_url is None:
            print("SONALI: Latest PDF not found.")
            return None

        pdf_bytes = download_pdf(pdf_url)

        # First try normal table extraction
        tables = extract_tables_from_pdf(pdf_bytes)

        row = find_currency_row(
            tables,
            "EUR",
        )

        if row:

            return {
                "bank": "SONALI",
                "currency": "EUR",
                "buy": float(row[3]),
                "sell": float(row[0]),
            }

        # -----------------------------
        # Fallback for Sonali text PDF
        # -----------------------------

        from utils.pdf_utils import extract_text_from_pdf

        text = extract_text_from_pdf(pdf_bytes)

        pattern = (
            r"([0-9]+\.[0-9]+)\s+"
            r"([0-9]+\.[0-9]+)\s+"
            r"EURO\s+"
            r"([0-9]+\.[0-9]+)"
        )

        match = re.search(
            pattern,
            text,
            re.IGNORECASE,
        )

        if not match:
            print("SONALI: EUR row not found.")
            return None

        sell = float(match.group(1))
        buy = float(match.group(3))

        return {
            "bank": "SONALI",
            "currency": "EUR",
            "buy": buy,
            "sell": sell,
        }

    except Exception as e:
        print(f"SONALI ERROR: {e}")
        return None