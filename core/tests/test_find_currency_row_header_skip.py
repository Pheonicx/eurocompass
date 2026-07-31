"""
core/tests/test_find_currency_row_header_skip.py

Regression test for utils.pdf_utils.find_currency_row.

Root cause, found via a live run's full table-structure dump (31 July
2026, collectors/city.py's temporary diagnostic): City's Bank PLC PDF
has an earlier "CASH FOREIGN CURRENCIES" section whose header row lists
full currency names as column labels
(['', 'US Dollar', 'GB Pound', 'Euro', ...]). Before this fix,
find_currency_row matched that row immediately (it contains a cell that
matches the "EUR"/"USD" aliases) and returned it -- well before ever
reaching the correct TT-rates table further down the page
("INDICATIVE DEALING RATES OF FOREIGN CURRENCY TO THE CUSTOMER") that
has the real numeric buy/sell data. extract_buy_sell correctly rejected
the header row's non-numeric values, but by then find_currency_row had
already stopped searching -- so City's EUR/USD collection failed with
"row found but values look wrong" even though a valid row existed
further down.

The two table fixtures below are the exact real structures captured
from that live run, not synthesized.
"""

from utils.pdf_utils import extract_buy_sell, find_currency_row

# Real table 0 from City's PDF (31 July 2026): the "CASH FOREIGN
# CURRENCIES" section. Row 3 is a HEADER row with currency full names
# as column labels -- this must NOT be returned as a currency row.
REAL_CITY_TABLE_CASH_RATES = [
    [
        "City Bank PLC.\nTreasury & Market Risk Division\nEXCHANGE RATE SHEET FOR USE OF AUTHORIZED DEALER BRANCHES\n"
        "FEX RATE CIRCULAR NO. TD/FER/2026/138 DATE 30/Jul/26",
        None, None, None, None, None, None, None, None, None, None,
    ],
    [
        "FEX RATE CIRCULAR NO. TD/FER/2026/138",
        None, None, None, None, None, None, None, None, "DATE", "30/Jul/26",
    ],
    ["CASH FOREIGN CURRENCIES", None, None, None, None, None, None, None, None, None, None],
    [
        "", "US Dollar", "GB Pound", "Euro", "Saudi Riyal", "Canadian\nDollar",
        "Kuwaiti Dinar", "UAE\nDirham", "Singapore\nDollar", "Australian\ndollar", "Swiss Franc",
    ],
    ["BUYING", "123.50", "164.79", "141.37", "32.89", "87.89", "398.35", "33.63", "95.69", "85.83", "151.46"],
    ["SELLING", "124.75", "167.88", "144.10", "33.51", "93.34", "399.30", "34.27", "97.52", "87.43", "154.22"],
]

# Real table 2 from the same PDF: "INDICATIVE DEALING RATES OF FOREIGN
# CURRENCY TO THE CUSTOMER" -- the actual TT-rates table with real
# numeric data, same column convention as other banks
# (buy_index=3, sell_index=0).
REAL_CITY_TABLE_TT_RATES = [
    ["INDICATIVE DEALING RATES OF FOREIGN CURRENCY TO THE CUSTOMER", None, None, None, None, None],
    ["SELLING", None, "", "BUYING", None, None],
    ["TT & OD", "BC SELLING", "CURRENCY", "TT CLEAN", "TT DOC", "OD SIGHT"],
    ["123.9500", "123.9500", "USD", "122.9500", "122.9500", "122.9500"],
    ["167.2953", "167.2953", "GBP", "162.2079", "162.2079", "162.2079"],
    ["143.7448", "143.7448", "EUR", "138.8966", "138.8966", "138.8966"],
]

REAL_CITY_TABLES = [REAL_CITY_TABLE_CASH_RATES, REAL_CITY_TABLE_TT_RATES]


def test_eur_finds_the_real_data_row_not_the_header():
    row = find_currency_row(REAL_CITY_TABLES, "EUR")
    assert row == ["143.7448", "143.7448", "EUR", "138.8966", "138.8966", "138.8966"]


def test_usd_finds_the_real_data_row_not_the_header():
    row = find_currency_row(REAL_CITY_TABLES, "USD")
    assert row == ["123.9500", "123.9500", "USD", "122.9500", "122.9500", "122.9500"]


def test_eur_extracted_buy_sell_are_correct_and_sensible():
    row = find_currency_row(REAL_CITY_TABLES, "EUR")
    buy, sell = extract_buy_sell(row, buy_index=3, sell_index=0)
    assert buy == 138.8966
    assert sell == 143.7448
    assert sell > buy  # sanity: sell should always exceed buy


def test_usd_extracted_buy_sell_are_correct_and_sensible():
    row = find_currency_row(REAL_CITY_TABLES, "USD")
    buy, sell = extract_buy_sell(row, buy_index=3, sell_index=0)
    assert buy == 122.95
    assert sell == 123.95
    assert sell > buy


def test_header_only_table_returns_none_rather_than_a_bad_match():
    """
    If the ONLY table available is the cash-rates header table (no real
    data row exists anywhere), the function must return None rather
    than falling back to the header row it correctly rejected.
    """
    row = find_currency_row([REAL_CITY_TABLE_CASH_RATES], "EUR")
    assert row is None
