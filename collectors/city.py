import re

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
from utils.city_api import get_exchange_rates, get_last_api_error

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
                # --no-sandbox and --disable-dev-shm-usage are standard,
                # near-mandatory flags for running headless Chromium
                # inside a Docker container (which is exactly what
                # GitHub Actions runners are) — without them, Chromium
                # can render unreliably or hang rather than error
                # outright, which matches exactly what was observed:
                # the page loaded but its JS-driven content never
                # finished appearing.
                browser = p.chromium.launch(
                    args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"]
                )
            except Exception as e:
                return _fail(f"browser launch failed (is chromium installed? {e})")

            try:
                # A realistic user agent and viewport, in case City's
                # site behaves differently for an obviously-automated
                # browser (a common, simple form of bot detection) —
                # City's page has succeeded at least once before and
                # then started timing out intermittently with no code
                # change in between, which fits a site treating headless
                # requests inconsistently more than a genuine, stable
                # rendering problem.
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                    viewport={"width": 1366, "height": 900},
                )

                # A realistic user-agent alone doesn't fool most bot
                # detection — the more common, more definitive signal is
                # the `navigator.webdriver` flag, which Playwright (and
                # Selenium) set to True by default and which many sites
                # specifically check for, even when everything else about
                # the request looks like a normal browser. This runs
                # before any of the page's own scripts, masking it for
                # the whole session. A standard, well-documented
                # mitigation — not a guess specific to City.
                context.add_init_script(
                    """
                    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                    Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
                    Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
                    """
                )

                page = context.new_page()
                page.goto(EXCHANGE_RATES_PAGE, timeout=60000, wait_until="domcontentloaded")

                # The reports list is populated by a client-side API
                # call after the initial page load — give that a chance
                # to settle before looking for the links. Not fatal if
                # this itself times out; the checks below are the real
                # gate.
                try:
                    page.wait_for_load_state("networkidle", timeout=20000)
                except Exception:
                    pass

            except Exception as e:
                browser.close()
                return _fail(f"page navigation failed/timed out: {e}")

            links = []
            last_selector_error = None

            # One retry via a full page reload — CI environments can be
            # slower and less consistent than a normal desktop browser,
            # so a single transient slow load shouldn't be treated the
            # same as the page genuinely being broken.
            for attempt in range(2):
                try:
                    # state="attached" only requires the element to exist
                    # in the DOM, not to be visually on-screen — the
                    # default ("visible") can time out even once the data
                    # has loaded, if it's rendered behind a loading
                    # overlay or off-screen momentarily, which fits City
                    # having succeeded before with no code change since.
                    page.wait_for_selector('a[href*="currency_files"]', timeout=40000, state="attached")
                    links = page.eval_on_selector_all(
                        'a[href*="currency_files"]',
                        "els => els.map(e => e.href)",
                    )
                    if links:
                        break
                except Exception as e:
                    last_selector_error = e

                if attempt == 0:
                    try:
                        page.reload(timeout=60000, wait_until="domcontentloaded")
                        page.wait_for_load_state("networkidle", timeout=20000)
                    except Exception:
                        pass

            # Last-resort fallback: bypass Playwright's element-query
            # mechanics entirely and just regex-search the raw rendered
            # HTML for the link pattern. If the data is genuinely present
            # in the page by now but some element-state check is still
            # being finicky, this still finds it.
            if not links:
                try:
                    html = page.content()
                    found = re.findall(r'href="([^"]*currency_files[^"]*\.pdf)"', html)
                    links = [f if f.startswith("http") else "https://citybankplc.com" + f for f in found]
                except Exception:
                    pass

            browser.close()

            if not links:
                return _fail(f"reports list never appeared on the page after retry: {last_selector_error}")

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
            api_reason = get_last_api_error()
            api_detail = f" ({api_reason})" if api_reason else ""
            _last_error = f"PDF method: {pdf_failure}; API fallback also failed{api_detail}"

        print("CITY: EUR data not found via either method.")
        return None

    except Exception as e:
        return _fail(f"unexpected error: {e}")


# --- v2.0 multi-currency support --------------------------------------
#
# Everything below is ADDITIVE: get_rate() above is completely untouched
# and still returns exactly what v1.0's main.py expects (EUR only, with
# its private-API fallback). get_rates() reuses the same browser-fetched
# PDF, generalized to any currency in it.

def get_rates(currencies=("EUR", "USD")):
    """
    Collect rates for multiple currencies from City's PDF in a single
    browser fetch.

    Note: unlike get_rate(), this does not fall back to City's private
    API — that fallback is EUR-specific by design (a deliberately narrow
    reverse-engineered endpoint) and isn't extended here. If the PDF/
    browser method fails, get_rates() simply returns [] for this run.
    """
    try:
        pdf_url = _get_latest_pdf_via_browser()
        if pdf_url is None:
            return []

        try:
            pdf_bytes = download_pdf(pdf_url)
        except Exception as e:
            _fail(f"found a PDF link but couldn't download it (get_rates): {e}")
            return []

        text = extract_text_from_pdf(pdf_bytes)
        tables = extract_tables_from_pdf(pdf_bytes)
        rate_date = extract_rate_date(text, filename_hint=pdf_url)

        results = []
        for currency in currencies:
            row = find_currency_row(tables, currency)
            if row is None:
                print(f"CITY: {currency} row not found (get_rates).")
                continue

            buy, sell = extract_buy_sell(row, buy_index=3, sell_index=0)
            if buy is None or sell is None:
                print(f"CITY: {currency} row found but values look wrong (get_rates): {row}")
                continue

            result = {
                "bank": "CITY",
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
        print(f"CITY ERROR (get_rates): {e}")
        return []
