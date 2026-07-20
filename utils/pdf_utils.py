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


def _normalize_currency_label(text: str) -> str:
    """
    Strip everything except letters, then uppercase — so "U.S. Dollar",
    "U.S-DOLLAR", "u.s DoLLAR", and "USDOLLAR" all normalize to the same
    "USDOLLAR". This absorbs the kind of font-encoding/OCR noise seen in
    some banks' PDFs (confirmed in Sonali's: real extracted text showed
    variants like "u.s DoLLAR" and "u.s.DOLl-AR" for what should read
    "USD"), without needing to hand-enumerate every punctuation variant.

    This can only make matching MORE permissive than a plain string
    comparison — anything that matched before still matches (normalizing
    both sides the same way is idempotent for already-clean text like
    "EUR" or "USD"), and some things that previously failed to match now
    correctly will.
    """
    return re.sub(r"[^A-Za-z]", "", text).upper()


def find_currency_row(tables, currency):
    """
    Search all extracted tables for a currency row.

    Matches against every known label for the given currency (e.g. "EUR"
    also matches a cell that literally says "EURO"), not just the exact
    ISO code, since banks are inconsistent about which they print — and
    matches after normalizing away punctuation/spacing noise, since some
    banks' PDFs render labels with inconsistent OCR-style formatting
    (e.g. "u.s DoLLAR" instead of a clean "USD").

    Example:
        currency = "EUR"

    Returns:
        row | None
    """
    aliases = set(
        _normalize_currency_label(a)
        for a in CURRENCY_ALIASES.get(currency.upper(), [currency.upper()])
    )

    for table in tables:
        for row in table:
            if not row:
                continue

            for cell in row:
                if cell and _normalize_currency_label(str(cell)) in aliases:
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


def extract_buy_sell_by_repetition(numbers, min_rate=50.0, max_rate=300.0):
    """
    Some banks (BRAC, notably) quote the same TT rate across several
    columns at once (e.g. "TT Clean," "TT Doc," and "OD Sight" buying
    are identical numbers repeated three times; "TT & OD" and "B.C."
    selling repeated twice). That repetition is a far more reliable
    signal than any fixed column position, which breaks the moment a
    row has one extra or one fewer column than expected — exactly what
    happened with a fixed-index approach in practice.

    Groups the row's plausible numbers by value; if exactly two distinct
    values each appear 2+ times, the lower one is buy and the higher is
    sell (a bank's sell rate is always above its buy rate).

    Returns (buy, sell) or (None, None) if the pattern doesn't hold —
    callers should fall back to a different strategy in that case, not
    guess.
    """
    from collections import Counter

    plausible = [n for n in numbers if n is not None and min_rate <= n <= max_rate]
    counts = Counter(round(n, 4) for n in plausible)
    repeated = sorted(v for v, c in counts.items() if c >= 2)

    if len(repeated) == 2:
        return repeated[0], repeated[1]

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

# Ordered from most to least specific/reliable. No \b anchors here —
# \b doesn't create a boundary next to an underscore (underscore counts
# as a "word" character to Python's regex engine), which silently broke
# matching on underscore-separated filenames like BRAC's
# "..._as_on_14_Jul_2026...". No trailing digit guard either — BRAC's
# filename has a hash suffix glued directly onto the year with no
# separator ("20266a55c75fd5040"), which a "not followed by a digit"
# check would incorrectly reject. The separator classes before each
# group, plus real-month-name validation in parse_date_loose, are
# specific enough on their own.
_DATE_PATTERNS = [
    # 13/May/26, 13-May-2026, 13 May 2026, 13_May_2026 (filenames)
    (re.compile(r"(\d{1,2})[/\-\s_]([A-Za-z]{3,9})[/\-\s_](\d{2,4})"), "dmy_named"),
    # 13.05.2026, 13-05-2026, 13/05/2026
    (re.compile(r"(\d{1,2})[./\-](\d{1,2})[./\-](\d{2,4})"), "dmy_numeric"),
    # 2026-05-13
    (re.compile(r"(\d{4})-(\d{1,2})-(\d{1,2})"), "ymd_numeric"),
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
        # URLs often have %20 etc. instead of real spaces — decode first
        # so a date like "Rate%20Sheet%2028%20Sep%202025" parses the
        # same way "Rate Sheet 28 Sep 2025" would.
        import urllib.parse
        decoded_hint = urllib.parse.unquote(filename_hint)
        d = parse_date_loose(decoded_hint)
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


def is_plausible_student_rate(student, normal_buy, normal_sell, max_diff=8.0):
    """
    Sanity-checks an extracted student rate against the bank's own
    normal buy/sell for the same day. Student rates are a modest
    preferential adjustment (typically within a taka or two of the
    normal rate) — not a different number entirely. A large mismatch
    almost always means the extraction grabbed a different currency's
    figures by mistake (exactly what happened once already: a bank's
    "student" section got matched against unrelated USD/GBP numbers).

    Returns True if the student rate is close enough to the bank's own
    normal rate to trust; False if it should be discarded.
    """
    if student is None:
        return False

    if "rate" in student:
        return abs(student["rate"] - normal_sell) <= max_diff or abs(student["rate"] - normal_buy) <= max_diff

    if "buy" in student and "sell" in student:
        return abs(student["buy"] - normal_buy) <= max_diff and abs(student["sell"] - normal_sell) <= max_diff

    return False


def find_student_rate(pdf_text, currency="EUR"):
    """
    Look for a dedicated "student file" rate section and pull out the
    rate for the given currency, if the bank publishes one at all.

    Verified against real student-rate tables from four different banks
    (Prime, BRAC, City, EBL) — every one of them uses the same
    underlying shape: a run of currency codes listed together, followed
    immediately by a run of numeric values in the same order. Some
    banks label it explicitly ("CURRENCY ... RATE ..."), others don't
    (just "USD/BDT GBP/BDT EUR/BDT ..." then the numbers on the next
    line) — this doesn't depend on those labels being present, only on
    the position of each currency code within its run of codes matching
    the position of its value within the following run of numbers.

    Wide tables that wrap across multiple code/value groups (as EBL's
    does) are handled by finding *all* such runs and using whichever one
    actually contains the requested currency.

    Returns a dict like {"rate": 143.86}, or None if no student-rate
    section was found for this currency — a normal, expected result for
    most banks, not an error.
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

    window = pdf_text[section_idx: section_idx + 1200]
    window_upper = window.upper()

    currency = currency.upper()
    aliases = CURRENCY_ALIASES.get(currency, [currency])

    result = _find_student_rate_by_position(window, window_upper, aliases)
    if result:
        return result

    return _find_student_rate_row(window, window_upper, aliases)


_KNOWN_CURRENCY_CODES = [
    "USD", "GBP", "EUR", "JPY", "CAD", "AUD", "CHF", "SAR", "AED", "CNY",
    "SGD", "MYR", "NZD", "DKK", "NOK", "CZK", "KRW", "THB", "INR", "HKD",
    "RUB", "SEK", "PLN", "OMR", "QAR", "BHD",
]

_NUMBER_RE = re.compile(r"-?[0-9][0-9,]*\.[0-9]+")


def _currency_token_positions(text_upper, currency_codes):
    """
    Finds every recognizable currency-code token in order of appearance
    and returns their (start_index, code) pairs. Matches "EUR" whether
    it's standalone or written as "EUR/BDT" — only checks that it isn't
    part of a longer alphabetic word.
    """
    positions = []
    for code in currency_codes:
        start = 0
        while True:
            idx = text_upper.find(code, start)
            if idx == -1:
                break
            before_ok = idx == 0 or not text_upper[idx - 1].isalpha()
            after_ok = idx + len(code) >= len(text_upper) or not text_upper[idx + len(code)].isalpha()
            if before_ok and after_ok:
                positions.append((idx, code))
            start = idx + len(code)
    positions.sort()
    return positions


def _find_student_rate_by_position(window, window_upper, aliases):
    code_positions = _currency_token_positions(window_upper, _KNOWN_CURRENCY_CODES)
    if len(code_positions) < 2:
        return None

    number_positions = [(m.start(), m.group()) for m in _NUMBER_RE.finditer(window)]
    if not number_positions:
        return None

    # Group currency codes into runs — a run breaks wherever a number
    # appears between two consecutive codes (that number belongs to a
    # different section/value-list, not the header list we're reading).
    runs = [[code_positions[0]]]
    for prev, curr in zip(code_positions, code_positions[1:]):
        interrupted = any(prev[0] < npos < curr[0] for npos, _ in number_positions)
        if interrupted:
            runs.append([curr])
        else:
            runs[-1].append(curr)

    # Only runs of 2+ codes look like a real currency-header list rather
    # than a stray one-off mention of a currency elsewhere in the text.
    runs = [r for r in runs if len(r) >= 2]

    for run in runs:
        codes_in_order = [code for _, code in run]

        target_index = None
        for alias in aliases:
            if alias in codes_in_order:
                target_index = codes_in_order.index(alias)
                break
        if target_index is None:
            continue

        run_end = run[-1][0]
        following_numbers = [
            to_float(txt) for pos, txt in number_positions if pos > run_end
        ]
        following_numbers = [n for n in following_numbers if n is not None]

        if target_index < len(following_numbers):
            val = following_numbers[target_index]
            if 50.0 <= val <= 300.0:
                return {"rate": val}

    return None


def _find_student_rate_row(window, window_upper, aliases):
    """
    Last-resort fallback for a currency immediately followed by its own
    number(s) on the same line (e.g. "EUR 140.82 140.10"). Verified
    real-world student-rate tables (Prime, BRAC, City, EBL) all use the
    positional column-list layout above instead, so this mainly exists
    as a safety net for a bank format not yet seen.
    """
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
