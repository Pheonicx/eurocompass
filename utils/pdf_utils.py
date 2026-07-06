import io

import pdfplumber
import requests


def download_pdf(url, timeout=20):
    """
    Download a PDF and return its bytes.
    """
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    return response.content


def extract_tables_from_pdf(pdf_bytes):
    """
    Extract every table from every page.

    Returns:
        list[list]
    """
    tables = []

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            page_tables = page.extract_tables()

            if page_tables:
                tables.extend(page_tables)

    return tables


def find_currency_row(tables, currency):
    """
    Search all extracted tables for a currency row.

    Example:
        currency = "EUR"

    Returns:
        row | None
    """
    currency = currency.upper()

    for table in tables:
        for row in table:
            if not row:
                continue

            for cell in row:
                if cell and str(cell).strip().upper() == currency:
                    return row

    return None

import re


def extract_text_from_pdf(pdf_bytes):
    """
    Extract all text from a PDF.

    Returns:
        str
    """

    text = ""

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:

        for page in pdf.pages:

            page_text = page.extract_text()

            if page_text:
                text += page_text + "\n"

    return text