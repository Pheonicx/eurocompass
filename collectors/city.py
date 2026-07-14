from utils.pdf_utils import (
    download_pdf,
    extract_tables_from_pdf,
    extract_text_from_pdf,
    extract_buy_sell,
    extract_rate_date,
    find_currency_row,
    find_student_rate,
    is_stale,
)
from utils.city_api import get_exchange_rates

EXCHANGE_RATES_PAGE = "https://www.citybankplc.com/exchange-rates"


def _get_latest_pdf_via_browser():
    """
    City's exchange-rates page is entirely client-side rendered — a
    plain HTTP request returns an empty shell, confirmed by testing.
    A real headless browser (Playwright) is needed to let the page's
    JavaScript actually run and populate the reports list, the same way
    a person's browser does.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("CITY: playwright not installed, skipping browser method.")
        return None

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(EXCHANGE_RATES_PAGE, timeout=30000)
            page.wait_for_selector('a[href*="currency_files"]', timeout=20000)

            links = page.eval_on_selector_all(
                'a[href*="currency_files"]',
                "els => els.map(e => e.href)",
            )

            browser.close()

        if not links:
            return None

        # The reports list is newest-first (confirmed visually).
        return links[0]

    except Exception as e:
        print(f"CITY: browser method failed: {e}")
        return None


def _get_rate_via_pdf():
    pdf_url = _get_latest_pdf_via_browser()

    if pdf_url is None:
        return None

    pdf_bytes = download_pdf(pdf_url)
    text = extract_text_from_pdf(pdf_bytes)

    rate_date = extract_rate_date(text, filename_hint=pdf_url)
    student = find_student_rate(text, "EUR")

    tables = extract_tables_from_pdf(pdf_bytes)
    row = find_currency_row(tables, "EUR")

    if row is None:
        print("CITY: EUR row not found in PDF.")
        return None

    # Verified against a real City Bank PDF: same column convention as
    # Sonali/Prime (sell first, "TT Clean" buy at index 3).
    buy, sell = extract_buy_sell(row, buy_index=3, sell_index=0)

    if buy is None or sell is None:
        print(f"CITY: EUR row found but values look wrong: {row}")
        return None

    result = {
        "bank": "CITY",
        "currency": "EUR",
        "buy": buy,
        "sell": sell,
        "rate_date": rate_date.isoformat() if rate_date else None,
        "is_stale": is_stale(rate_date),
    }

    if student:
        result["student"] = student

    return result


def _get_rate_via_api():
    """
    Older fallback: City's private, reverse-engineered admin API. Kept
    as a second path since it has worked before — but it depends on
    hardcoded credentials that can be rotated or revoked without notice,
    which is exactly why the PDF method above is now tried first.
    """
    try:
        rates = get_exchange_rates()

        if not rates:
            return None

        for rate in rates:
            if rate.get("code") == "EUR":
                return {
                    "bank": "CITY",
                    "currency": "EUR",
                    "buy": float(rate["buying"]),
                    "sell": float(rate["selling"]),
                }

        return None

    except Exception as e:
        print(f"CITY API ERROR: {e}")
        return None


def get_rate():
    """
    Collect EUR exchange rate from City Bank.
    """

    try:
        result = _get_rate_via_pdf()

        if result is not None:
            return result

        print("CITY: PDF/browser method failed, trying private API fallback.")

        result = _get_rate_via_api()

        if result is not None:
            return result

        print("CITY: EUR data not found via either method.")
        return None

    except Exception as e:
        print(f"CITY ERROR: {e}")
        return None
