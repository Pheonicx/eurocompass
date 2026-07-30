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


# The exact real text extracted from Sonali's actual PDF on 30 July 2026,
# captured via a live GitHub Actions diagnostic run
# (scripts/test_v2_pipeline_e2e.py). This run revealed a DIFFERENT
# garbling pattern than REAL_SONALI_TEXT above: rather than just
# mangling punctuation between otherwise-intact letters ("u.s.DoLLAR"),
# this PDF's font encoding dropped a letter entirely --
# "U.S.DOL|-AR" normalizes to "USDOLAR" (one letter short of
# "USDOLLAR") -- which the exact-match-after-normalization logic didn't
# tolerate. Fixed with a small edit-distance allowance for longer
# aliases (utils.pdf_utils._label_matches_any_alias).
REAL_SONALI_TEXT_DROPPED_LETTER = (
    "SONALI BANK PLC | TREASURY MANAGEMENT OIVISION (FRONT OFFICE) | HEAD OFFICE. DHAKA | "
    "www.sonalibank.com,bd (lNDlcATlvE oNLY : Raes may very ln ttre same day) | "
    "E-mail: dgmtmd@sonalibank.com.bd, fxdealing@sonalibank.com.bd | No: | "
    "Daily Foreign Exchange Rate Circular 20261136 | : 30.07.2026 | "
    "DATED EFFECTIVE DATE: 3OU JULY TO lST AUGUST, 2026 | "
    "NOTE;'FROM ISTJULY 2023, LIBOR IS BEING REPI.AGED BY SOFR, SONIA, ESTR ETC. | "
    "1. CROSS RATES lN TOKYO, HONGKONG EXCHANGE MARKET AS ON 30/07/2026 AT 10:07 A.M. (LOCAL) | "
    "US$ PER US$ PER CAD PER CHF PER JPY PER AED PER | "
    "GBP 1.00 EUR 1.00 US$ 1.00 US$ 1.00 US$ 1.00 US$ 1.00 | "
    "SELL|NG 1.3348 1.1452 1.4051 0.8155 16i:i.5100 3.6725 | "
    "BUYTNG 1.3v4 1.1450 'r.40s4 0.8156 163.5200 3.6727 | "
    "2.a) SONALI BANK PLC oEALING RATES TO PUBLIC (8.TAKA FOR ONE UNIT OF FOREIGN CURRENCY) | "
    "SPOTSELLING | SPOTBUYING | O.D. SIGHT O. D. | TT/OD B . C . CURRENCY TT CLEAN EXPORT BILLS TRANSFER | "
    "123.9500 123.9500 U.S.DOL|-AR 122.9500 122.8300 | 122.6800 | "
    "'t67.',t029 167.1029 G.B.POUND 164.0645 163.9044 163.7U2 | "
    "143.3670 143.3670 EURo 140.7778 140.6404 ',140.4686 | "
    "88.6554 88.6554 CANAD|AN DOL|-AR 87.0466 86.9616 86.8554"
)


def test_usd_dropped_letter_variant_now_matches():
    """
    The specific bug found in the 30 July 2026 live run: "U.S.DOL|-AR"
    (one letter short of "USDOLLAR" after normalization) previously
    failed to match at all.
    """
    matches = find_all_currency_token_windows(REAL_SONALI_TEXT_DROPPED_LETTER, "USD")
    assert len(matches) >= 1


def test_usd_extracted_correctly_from_dropped_letter_variant():
    buy, sell = _extract_via_text_fallback(REAL_SONALI_TEXT_DROPPED_LETTER, "USD")
    assert buy == 122.95
    assert sell == 123.95


def test_eur_still_extracted_correctly_from_dropped_letter_variant():
    # EUR wasn't broken by this particular PDF's corruption ("EURo" is
    # still an exact match after normalization) -- confirms the fix
    # didn't regress the currency that was already working.
    buy, sell = _extract_via_text_fallback(REAL_SONALI_TEXT_DROPPED_LETTER, "EUR")
    assert buy == 140.7778
    assert sell == 143.367


def test_fuzzy_matching_does_not_cross_match_different_currencies():
    """
    Safety check for the new edit-distance tolerance: short aliases
    ("EUR", "USD", "GBP") must still require an exact match -- a 1-edit
    tolerance on a 3-letter code would be far too permissive. This text
    contains "CANAD|AN DOL|-AR" (Canadian Dollar, an unrelated currency
    Sonali also lists) right next to the real USD row; confirms it's
    never picked up as a false USD or EUR match.
    """
    usd_matches = find_all_currency_token_windows(REAL_SONALI_TEXT_DROPPED_LETTER, "USD")
    # Every match's surrounding numbers should trace back to the real
    # USD row (122.95xx / 123.95xx), never the Canadian Dollar row
    # (86.xx / 87.xx / 88.xx).
    for tokens_before, _ in usd_matches:
        floats = [_to_float(t) for t in tokens_before if _to_float(t) is not None]
        assert all(f > 100 for f in floats), (
            f"USD match unexpectedly picked up Canadian Dollar-range numbers: {floats}"
        )


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
