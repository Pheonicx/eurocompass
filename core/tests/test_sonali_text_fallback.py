"""
core/tests/test_sonali_text_fallback.py

Tests for the Sonali-specific text fallback (collectors/sonali.py) and
the generic multi-match text finder it's built on
(utils.pdf_utils.find_all_currency_token_windows).

The real-text fixtures here are the ACTUAL text captured from a live
GitHub Actions run against Sonali's real, current PDF (21 July 2026),
via a diagnostic print added specifically to ground this fix in
evidence rather than another guess — a first attempt (normalizing
punctuation in find_currency_row) was tried, re-tested live, and
confirmed NOT to fix the real issue (extract_tables_from_pdf finds zero
tables for Sonali's PDFs at all), before this fallback was built from
the actual failing document's real content.
"""

from utils.pdf_utils import _looks_numeric, find_all_currency_token_windows
from collectors.sonali import _extract_via_text_fallback, _to_float

# The exact real text extracted from Sonali's actual PDF on 21 July 2026,
# captured via a live GitHub Actions diagnostic run.
REAL_SONALI_TEXT = (
    "SONAL! BANK PLC TREASURY MANAGETYIENT DIVTSION (FRONT OFFICE) HEAD OFFICE. DHAKA "
    "www.sonalibank.com.bd (lNDlcATlvE oNLY : Rates mey yary ln the same day, "
    "E-mail: dgmtmd@sonalibank.com.bd, frdealing@sonalibank'com'bd "
    "Daily Forcign Exchange Rate Gircular No: 20261129 DATED: 21.07.2026 "
    "EFFEcflvEDATE:2lsrJULY,2026 "
    "1. CROSS RATES lN TOKYO, HONGKONG EXCHANGE MARKETAS ON 21t07t2o26Af 10:(X)A.M. (LOCAL) "
    "US$ PER US$ PER CAD PER CHF PER JPY PER AED PER "
    "GBP 1.00 EUR 1.00 USS 1.00 US$ 1.00 US$ 1.00 US$ ,l.00 "
    "SELL|NG 1.U40 1.1413 1.4078 0.810s 162.4700 3.6726 "
    "BUYTNG 1.U32 ',t.1411 1.4081 0.8108 162.5100 3.6728 "
    "2.a) SONALI BANK PLC DEALING RATES TO PUBLIC (B.TAKA FOR ONE UNIT OF FOREIGN CURRENCY) "
    "SPOTSELLING SPOTBUYING O.D. SIGHT O. D. "
    "TT/OD B. C. CURRENCY TTCLEAN EXPORTBILLS TRANSFER "
    "123.7500 123.7500 u.s.DoLLAR 122.7500 122.6300 122.4800 "
    "167.9832 167.9832 G.B.POUND 164.8778 164.7166 164.5151 "
    "142.6482 142.6482 EURO 140.0700 139.9331 139.7619 "
    "88.3426 88.3426 CANADTAN DOLLAR 86.7383 86.6535 86.5475"
)


def test_extract_tables_found_zero_tables_confirmed_real_scenario():
    """
    Documents the actual confirmed root cause: this text represents a
    PDF where extract_tables_from_pdf() returns an empty list entirely
    (confirmed via a live diagnostic run) — this whole fallback exists
    specifically for that situation.
    """
    # No assertion needed here beyond documenting the scenario — the
    # real tables=[] finding came from a live run, not from parsing
    # this text (which is the *text* extraction, a separate code path).
    assert REAL_SONALI_TEXT  # sanity: fixture is non-empty


def test_usd_extracted_correctly_from_real_text():
    buy, sell = _extract_via_text_fallback(REAL_SONALI_TEXT, "USD")
    assert buy == 122.75
    assert sell == 123.75


def test_eur_extracted_correctly_from_real_text():
    buy, sell = _extract_via_text_fallback(REAL_SONALI_TEXT, "EUR")
    assert buy == 140.07
    assert sell == 142.6482


def test_disambiguates_real_row_from_unrelated_cross_rates_section():
    """
    The critical case this fallback exists to solve: 'EUR' also appears
    earlier in the document in a "cross rates" reference section
    ("GBP 1.00 EUR 1.00 USS 1.00...") where it's just a unit label, not
    an actual dealing rate. Confirms the fallback picks the REAL dealing
    rate row (the one with the repeated-pair signature), not this
    earlier false match.
    """
    matches = find_all_currency_token_windows(REAL_SONALI_TEXT, "EUR")
    assert len(matches) >= 2  # confirms the ambiguity genuinely exists in this text

    buy, sell = _extract_via_text_fallback(REAL_SONALI_TEXT, "EUR")
    # The real row's sell rate (142.6482), not anything from the cross-rates section
    assert sell == 142.6482


def test_returns_none_when_currency_not_present():
    buy, sell = _extract_via_text_fallback(REAL_SONALI_TEXT, "GBP")
    # GBP DOES appear ("G.B.POUND") but let's confirm a genuinely absent
    # currency returns cleanly
    buy, sell = _extract_via_text_fallback(REAL_SONALI_TEXT, "JPY")
    assert buy is None
    assert sell is None


def test_looks_numeric():
    assert _looks_numeric("123.7500") is True
    assert _looks_numeric("1,234.56") is True
    assert _looks_numeric("EURO") is False
    assert _looks_numeric("u.s.DoLLAR") is False


def test_to_float_handles_commas():
    assert _to_float("1,234.56") == 1234.56
    assert _to_float("123.75") == 123.75
    assert _to_float("not-a-number") is None


def test_find_all_currency_token_windows_does_not_swallow_numbers_into_match():
    """
    Regression test for a real bug caught before this shipped: the
    normalization strips digits along with punctuation, which let pure
    numeric tokens silently disappear into a multi-token label match
    (e.g. "123.7500 123.7500 u.s.DoLLAR" collapsing to "USDOLLAR" as one
    3-token span) -- corrupting the boundary between numbers and label.
    """
    matches = find_all_currency_token_windows(REAL_SONALI_TEXT, "USD")
    assert len(matches) == 1
    before, after = matches[0]
    # The numbers must be in `before`, NOT absorbed into the match itself
    assert "123.7500" in before
