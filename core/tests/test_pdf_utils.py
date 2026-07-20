"""
core/tests/test_pdf_utils.py

Tests for utils/pdf_utils.py — specifically find_currency_row(), which
had a real, confirmed production bug: Sonali Bank's live rate collection
had been silently failing (confirmed via the actual GitHub Actions run
and v1.0's own history/SONALI.csv, which stopped updating), because
their PDFs render currency labels with inconsistent OCR-style
punctuation ("u.s DoLLAR", "u.s.DOLl-AR") that a plain exact-match
comparison against a fixed alias list couldn't handle.

These test cases use the EXACT real text confirmed via live research
against Sonali's actual PDFs (not synthetic/imagined examples), so this
test would have failed against the old code and passes against the fix.
"""

from utils.pdf_utils import find_currency_row


def test_clean_exact_currency_code_still_matches():
    """The most basic, already-working case must keep working."""
    tables = [[["EUR", "142.50", "145.30"]]]
    assert find_currency_row(tables, "EUR") == ["EUR", "142.50", "145.30"]


def test_clean_alias_still_matches():
    tables = [[["EURO", "142.50", "145.30"]]]
    assert find_currency_row(tables, "EUR") == ["EURO", "142.50", "145.30"]


def test_real_sonali_garbled_usd_variant_1_now_matches():
    """
    Real text confirmed from an actual Sonali PDF (25-06-2026):
    "u.s DoLLAR · 122.3500 122.2300 · 122.0800"
    This is exactly the kind of row that was previously invisible to
    find_currency_row(), silently breaking USD collection.
    """
    tables = [[["u.s DoLLAR", "122.3500", "122.2300", "122.0800"]]]
    row = find_currency_row(tables, "USD")
    assert row is not None
    assert row[0] == "u.s DoLLAR"


def test_real_sonali_garbled_usd_variant_2_now_matches():
    """Real text confirmed from another actual Sonali PDF (15-07-2026)-style extraction."""
    tables = [[["u.s.DOLl-AR", "123.7500", "123.7500", "122.7500"]]]
    row = find_currency_row(tables, "USD")
    assert row is not None


def test_period_and_space_variants_of_usd_all_match():
    variants = ["U.S.DOLLAR", "U.S DOLLAR", "U.S. DOLLAR", "us-dollar", "USDOLLAR"]
    for variant in variants:
        tables = [[[variant, "122.75", "123.75"]]]
        row = find_currency_row(tables, "USD")
        assert row is not None, f"Expected {variant!r} to match USD"


def test_unrelated_currency_does_not_false_positive_match():
    """The normalization must not become so loose that it matches the
    wrong currency."""
    tables = [[["GBP", "160.00", "165.00"]]]
    assert find_currency_row(tables, "USD") is None
    assert find_currency_row(tables, "EUR") is None


def test_no_matching_row_returns_none():
    tables = [[["JPY", "0.75", "0.80"]]]
    assert find_currency_row(tables, "EUR") is None


def test_searches_across_multiple_tables_and_rows():
    tables = [
        [["Header", "Buy", "Sell"], ["GBP", "160.0", "165.0"]],
        [["USD", "122.75", "123.75"]],
    ]
    row = find_currency_row(tables, "USD")
    assert row == ["USD", "122.75", "123.75"]


def test_empty_and_none_rows_are_skipped_safely():
    tables = [[None, [], ["EUR", "140.0", "143.0"]]]
    row = find_currency_row(tables, "EUR")
    assert row == ["EUR", "140.0", "143.0"]
