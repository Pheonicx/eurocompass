import re

from utils import http_client
from utils.pdf_utils import (
    download_pdf,
    extract_tables_from_pdf,
    extract_text_from_pdf,
    extract_buy_sell,
    extract_rate_date,
    find_currency_row,
    find_student_rate,
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


def _extract_from_row(row):
    """
    BRAC's rate table has an extra leading "Cash Notes" column that
    Sonali/Prime's tables don't have, so the generic buy_index=3,
    sell_index=0 convention is wrong here — it would silently pick the
    cash-note sell rate instead of the TT&OD sell rate. Verified against
    a real BRAC PDF: correct positions are index 1 (TT&OD sell) and
    index 3 (T.T. Clean buy).
    """
    if row is None or len(row) < 4:
        return None, None

    sell = to_float(row[1])
    buy = to_float(row[3])

    if sell is not None and buy is not None and 50.0 <= sell <= 300.0 and 50.0 <= buy <= 300.0:
        return buy, sell

    # Fall back to the generic defensive extractor in case BRAC ever
    # simplifies their table to match the other banks' layout.
    return extract_buy_sell(row, buy_index=3, sell_index=0)


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

    buy, sell = _extract_from_row(row) if row else (None, None)

    if buy is None or sell is None:
        # Table extraction can fail on BRAC's denser multi-section PDF —
        # fall back to a direct text scan for a clean "EUR <numbers>" row.
        # Column order verified against a real BRAC PDF: skip the first
        # (Cash Notes) number, sell is the 2nd, buy is the 4th.
        match = re.search(
            r"EUR\s+([0-9]+\.[0-9]+)\s+([0-9]+\.[0-9]+)\s+([0-9]+\.[0-9]+)\s+([0-9]+\.[0-9]+)",
            text,
        )
        if match:
            nums = [float(g) for g in match.groups()]
            sell = nums[1]
            buy = nums[3]

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

    if student:
        result["student"] = student

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
