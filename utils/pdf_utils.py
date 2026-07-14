import io
import re
import time

import pdfplumber
import requests


# Different banks label the same currency differently in their PDFs.
# Sonali, for example, spells it out as "EURO" rather than the ISO code
# "EUR" — matching only the exact code was silently forcing Sonali's
# collector through a much less reliable fallback parser on every run.
CURRENCY_ALIASES = {
    "EUR": ["EUR", "EURO"],
    "USD": ["USD", "US DOLLAR", "USDOLLAR"],
    "GBP": ["GBP", "STERLING", "POUND STERLING"],
}


def download_pdf(url, timeout=20, retries=3, backoff=2.0):
    """
    Download a PDF and return its bytes. Retries on transient network
    failures (timeouts, connection resets) before giving up, since a
    single blip shouldn't count as "the bank changed their PDF."
    """
    last_error = None

    for attempt in range(1, retries + 1):
        try:
            response = requests.get(url, timeout=timeout)
            response.raise_for_status()
            return response.content

        except requests.RequestException as e:
            last_error = e
            if attempt < retries:
                time.sleep(backoff * attempt)

    raise last_error


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

    Matches against every known label for the given currency (e.g. "EUR"
    also matches a cell that literally says "EURO"), not just the exact
    ISO code, since banks are inconsistent about which they print.

    Example:
        currency = "EUR"

    Returns:
        row | None
    """
    aliases = set(a.upper() for a in CURRENCY_ALIASES.get(currency.upper(), [currency.upper()]))

    for table in tables:
        for row in table:
            if not row:
                continue

            for cell in row:
                if cell and str(cell).strip().upper() in aliases:
                    return row

    return None


def to_float(cell):
    """
    Parse a table cell into a float, tolerating the formatting junk that
    commonly shows up in bank PDFs: thousands separators, currency
    symbols, non-breaking spaces, stray whitespace.

    Returns None instead of raising, so callers can detect "this cell
    wasn't actually a number" and react (reject/fallback) instead of
    crashing or silently propagating a wrong value.
    """
    if cell is None:
        return None

    text = str(cell).strip()
    text = text.replace(",", "").replace("\u00a0", "").replace("৳", "").strip()

    if not re.fullmatch(r"-?[0-9]+(\.[0-9]+)?", text):
        return None

    try:
        return float(text)
    except ValueError:
        return None


def extract_buy_sell(row, buy_index, sell_index, min_rate=50.0, max_rate=300.0):
    """
    Pull buy/sell values out of a table row using the bank's normal
    column positions, but verify both are actually plausible numbers
    before trusting them. If the expected columns don't hold sane
    values (e.g. because the bank reordered their table), falls back to
    scanning the whole row for exactly two numbers in a plausible rate
    range, rather than confidently returning garbage.

    Returns (buy, sell) or (None, None) if nothing trustworthy is found.
    """
    buy = to_float(row[buy_index]) if buy_index < len(row) else None
    sell = to_float(row[sell_index]) if sell_index < len(row) else None

    if buy is not None and sell is not None and min_rate <= buy <= max_rate and min_rate <= sell <= max_rate:
        return buy, sell

    # Expected columns weren't usable — scan the row for plausible candidates.
    candidates = [v for v in (to_float(c) for c in row) if v is not None and min_rate <= v <= max_rate]

    if len(candidates) == 2:
        return min(candidates), max(candidates)

    return None, None


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


# --- Rate date extraction -------------------------------------------------
#
# Some banks publish today's rate. Some publish yesterday's rate under
# today's date, or reuse a PDF for a day or two over a weekend/holiday.
# Every bank we've checked prints the date somewhere (in the filename, or
# in the document text, usually both) — this pulls it out so the site can
# show it and flag when a rate isn't actually from today.

_MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}

# Ordered from most to least specific/reliable.
_DATE_PATTERNS = [
    # 13/May/26, 13-May-2026, 13 May 2026
    (re.compile(r"\b(\d{1,2})[/\-\s]([A-Za-z]{3,9})[/\-\s](\d{2,4})\b"), "dmy_named"),
    # 13.05.2026, 13-05-2026, 13/05/2026
    (re.compile(r"\b(\d{1,2})[./\-](\d{1,2})[./\-](\d{2,4})\b"), "dmy_numeric"),
    # 2026-05-13
    (re.compile(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b"), "ymd_numeric"),
]


def _to_full_year(y):
    y = int(y)
    if y < 100:
        return 2000 + y
    return y


def parse_date_loose(text):
    """
    Best-effort extraction of a date from a short string or filename
    fragment. Returns a datetime.date, or None if nothing recognizable
    was found. Deliberately tolerant of the inconsistent, sometimes
    OCR-mangled formatting seen across different banks' PDFs.
    """
    import datetime

    if not text:
        return None

    for pattern, kind in _DATE_PATTERNS:
        m = pattern.search(text)
        if not m:
            continue

        try:
            if kind == "dmy_named":
                day, mon_name, year = m.groups()
                mon = _MONTHS.get(mon_name.strip().lower()[:3])
                if not mon:
                    continue
                return datetime.date(_to_full_year(year), mon, int(day))

            if kind == "dmy_numeric":
                day, mon, year = m.groups()
                mon, day = int(mon), int(day)
                if mon > 12 and day <= 12:
                    mon, day = day, mon
                return datetime.date(_to_full_year(year), mon, day)

            if kind == "ymd_numeric":
                year, mon, day = m.groups()
                return datetime.date(int(year), int(mon), int(day))

        except (ValueError, TypeError):
            continue

    return None


def extract_rate_date(pdf_text, filename_hint=None):
    """
    Determine the date a rate sheet was actually issued for.

    Tries the filename first (usually the cleanest, most structured
    source — e.g. "fxrate-13-05-2026.pdf"), then falls back to scanning
    the PDF's own text for a date near words like "DATE", "DATED",
    "EFFECTIVE", or "CIRCULAR".

    Returns a datetime.date, or None if no date could be determined —
    callers should treat None as "unknown," not "today."
    """
    if filename_hint:
        d = parse_date_loose(filename_hint)
        if d:
            return d

    if not pdf_text:
        return None

    for keyword in ("EFFECTIVE DATE", "DATED", "DATE"):
        idx = pdf_text.upper().find(keyword)
        if idx != -1:
            snippet = pdf_text[idx: idx + 40]
            d = parse_date_loose(snippet)
            if d:
                return d

    # Last resort: any date-like text anywhere in the first 500 characters,
    # where these circulars conventionally put their header/date.
    return parse_date_loose(pdf_text[:500])


def is_stale(rate_date, reference_date=None, tz_offset_hours=6):
    """
    Whether a rate_date is older than "today" in Bangladesh (UTC+6 by
    default, since that's the market this project serves). Returns True
    if rate_date is unknown (None) — better to flag "unknown, treat with
    caution" than silently claim a rate is current when we can't tell.
    """
    import datetime

    if rate_date is None:
        return True

    if reference_date is None:
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        local_now = now_utc + datetime.timedelta(hours=tz_offset_hours)
        reference_date = local_now.date()

    return rate_date < reference_date


# --- Student-rate extraction ----------------------------------------------

_STUDENT_SECTION_KEYWORDS = ("STUDENT FILE", "STUDENT FILES", "STUDENT RATE")


def find_student_rate(pdf_text, currency="EUR"):
    """
    Look for a dedicated "student file" rate section and pull out the
    rate for the given currency, if the bank publishes one at all.

    Handles two layouts seen in practice across real bank PDFs:

      - Column-list layout (Prime Bank): a "CURRENCY" row listing several
        currency codes in order, followed by a "RATE" (or "BUYING" /
        "SELLING") row listing values in the same order — the value's
        *position* in the list is what ties it to a currency, not
        adjacency in the raw text.
          e.g. "CURRENCY USD GBP EUR ... RATE 122.20 164.95 143.86 ..."

      - Row layout: each currency is immediately followed by its own
        number(s) on the same line.
          e.g. "EUR 140.82 140.10 139.39 ..."

    Returns a dict like {"rate": 143.86} or {"buy": x, "sell": y},
    or None if no student-rate section was found for this currency —
    that's a normal, expected result for most banks, not an error.
    """
    if not pdf_text:
        return None

    text_upper = pdf_text.upper()
    section_idx = None

    for kw in _STUDENT_SECTION_KEYWORDS:
        idx = text_upper.find(kw)
        if idx != -1:
            section_idx = idx
            break

    if section_idx is None:
        return None

    window = pdf_text[section_idx: section_idx + 700]
    window_upper = window.upper()

    currency = currency.upper()
    aliases = CURRENCY_ALIASES.get(currency, [currency])

    result = _find_student_rate_columnar(window, window_upper, aliases)
    if result:
        return result

    return _find_student_rate_row(window, window_upper, aliases)


def _currency_token_positions(window_upper, currency_codes):
    """
    Finds every recognizable currency-code token in order of appearance
    and returns their (start_index, code) pairs, so we can establish a
    stable left-to-right ordering for the column-list layout.
    """
    positions = []
    for code in currency_codes:
        start = 0
        while True:
            idx = window_upper.find(code, start)
            if idx == -1:
                break
            before_ok = idx == 0 or not window_upper[idx - 1].isalpha()
            after_ok = idx + len(code) >= len(window_upper) or not window_upper[idx + len(code)].isalpha()
            if before_ok and after_ok:
                positions.append((idx, code))
            start = idx + len(code)
    positions.sort()
    return positions


def _find_student_rate_columnar(window, window_upper, aliases):
    known_codes = ["USD", "GBP", "EUR", "JPY", "CAD", "AUD", "CHF", "SAR", "AED", "CNY", "SGD"]

    cur_label_idx = window_upper.find("CURRENCY")
    if cur_label_idx == -1:
        return None

    value_labels = []
    for label in ("RATE", "SELLING", "BUYING"):
        idx = window_upper.find(label, cur_label_idx + len("CURRENCY"))
        if idx != -1:
            value_labels.append((idx, label))
    if not value_labels:
        return None
    value_labels.sort()
    first_value_idx, _ = value_labels[0]

    currency_zone_upper = window_upper[cur_label_idx:first_value_idx]
    codes_in_order = [code for _, code in _currency_token_positions(currency_zone_upper, known_codes)]

    if not codes_in_order:
        return None

    target_index = None
    for alias in aliases:
        if alias in codes_in_order:
            target_index = codes_in_order.index(alias)
            break
    if target_index is None:
        return None

    results = {}
    for idx, label in value_labels:
        segment = window[idx + len(label): idx + len(label) + 400]
        numbers = [to_float(n) for n in re.findall(r"-?[0-9][0-9,]*\.[0-9]+", segment)]
        numbers = [n for n in numbers if n is not None]
        if target_index < len(numbers):
            val = numbers[target_index]
            if 50.0 <= val <= 300.0:
                results[label] = val

    if "RATE" in results:
        return {"rate": results["RATE"]}
    if "BUYING" in results and "SELLING" in results:
        return {"buy": min(results["BUYING"], results["SELLING"]), "sell": max(results["BUYING"], results["SELLING"])}

    return None


def _find_student_rate_row(window, window_upper, aliases):
    cur_idx = None
    for alias in aliases:
        idx = window_upper.find(alias)
        if idx != -1:
            cur_idx = idx
            break

    if cur_idx is None:
        return None

    tail = window[cur_idx: cur_idx + 200]
    numbers = [to_float(n) for n in re.findall(r"-?[0-9][0-9,]*\.[0-9]+", tail)]
    numbers = [n for n in numbers if n is not None and 50.0 <= n <= 300.0]

    if not numbers:
        return None

    if len(numbers) == 1:
        return {"rate": numbers[0]}

    buy, sell = numbers[0], numbers[1]
    return {"buy": min(buy, sell), "sell": max(buy, sell)}
