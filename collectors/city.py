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
from utils.city_api import get_exchange_rates

EXCHANGE_RATES_PAGE = "https://www.citybankplc.com/exchange-rates"

# Records the specific stage that failed, so main.py can write a precise
# reason to collector_status.json instead of a generic "no data" — no
# need to dig through GitHub Actions logs to find out why City failed.
_last_error = None


def get_last_error():
    return _last_error


def _fail(reason):
    global _last_error
    _last_error = reason
    print(f"CITY: {reason}")
    return None


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
        return _fail("playwright not installed")

    try:
        with sync_playwright() as p:
            try:
                browser = p.chromium.launch()
            except Exception as e:
                return _fail(f"browser launch failed (is chromium installed? {e})")

            try:
                page = browser.new_page()
                page.goto(EXCHANGE_RATES_PAGE, timeout=45000, wait_until="domcontentloaded")
            except Exception as e:
                browser.close()
                return _fail(f"page navigation failed/timed out: {e}")

            try:
                page.wait_for_selector('a[href*="currency_files"]', timeout=25000)
                links = page.eval_on_selector_all(
                    'a[href*="currency_files"]',
                    "els => els.map(e => e.href)",
                )
            except Exception as e:
                browser.close()
                return _fail(f"reports list never appeared on the page: {e}")

            browser.close()

        if not links:
            return _fail("page loaded but no report links were found")

        # The reports list is newest-first (confirmed visually).
        return links[0]

    except Exception as e:
        return _fail(f"unexpected browser error: {e}")


def _get_rate_via_pdf():
    pdf_url = _get_latest_pdf_via_browser()

    if pdf_url is None:
        return None

    try:
        pdf_bytes = download_pdf(pdf_url)
    except Exception as e:
        return _fail(f"found a PDF link but couldn't download it: {e}")

    text = extract_text_from_pdf(pdf_bytes)

    rate_date = extract_rate_date(text, filename_hint=pdf_url)
    student = find_student_rate(text, "EUR")

    tables = extract_tables_from_pdf(pdf_bytes)
    row = find_currency_row(tables, "EUR")

    if row is None:
        return _fail("downloaded the PDF but couldn't find an EUR row in it")

    # Verified against a real City Bank PDF: same column convention as
    # Sonali/Prime (sell first, "TT Clean" buy at index 3).
    buy, sell = extract_buy_sell(row, buy_index=3, sell_index=0)

    if buy is None or sell is None:
        return _fail(f"found an EUR row but the values look wrong: {row}")

    result = {
        "bank": "CITY",
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
    global _last_error

    try:
        result = _get_rate_via_pdf()

        if result is not None:
            return result

        pdf_failure = _last_error
        print("CITY: PDF/browser method failed, trying private API fallback.")

        result = _get_rate_via_api()

        if result is not None:
            return result

        if pdf_failure:
            _last_error = f"PDF method: {pdf_failure}; API fallback also failed"

        print("CITY: EUR data not found via either method.")
        return None

    except Exception as e:
        return _fail(f"unexpected error: {e}")
