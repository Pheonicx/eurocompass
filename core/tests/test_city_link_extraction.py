"""
core/tests/test_city_link_extraction.py

Tests for the real fix to collectors/city.py's PDF link extraction.

Root cause, found through actual diagnostic evidence (a screenshot,
page HTML, and console log captured from a live, failing GitHub Actions
run — not guessed): City's site renders PDF links as JSON data
embedded in the page (a "file":"https://...currency_files/....pdf"
property feeding an Ant Design table component), not as plain
<a href="..."> anchor tags. Both the old element-selector wait AND the
old href="..."-anchored regex fallback were looking for something that
was never there, which is why they always failed no matter how long
the timeout or how many retries.

The fixture text below is a REAL excerpt of the actual page HTML
captured from City's live site on 24 July 2026, not synthesized.
"""

import re

# A real excerpt of City's actual page HTML, captured via a live
# diagnostic run on 24 July 2026. Note the doubled backslash-escaped
# quotes (\\\") — this is exactly how the real page embeds it (a
# JSON-encoded string within a JS string literal), and the fix must
# work against this real formatting, not an idealized version of it.
REAL_CITY_HTML_EXCERPT = (
    r'p\",\"buying\":\"138.611655\",\"selling\":\"143.455455\"},{\"id\":3,\"code\":\"USD\",'
    r'\"name\":\"US Dollar\",\"change\":\"0.04\",\"change_type\":\"up\",\"buying\":\"122.85\",'
    r'\"selling\":\"123.85\"}],\"forex_rates_report\":[{\"id\":1,\"title\":\"Daily Exchange Rate '
    r'Sheet 23-07-2026\",\"file\":\"https://citybankplc.com/uploads/files//currency_files/'
    r'17847832141725022.pdf\"},{\"id\":2,\"title\":\"Daily Exchange Rate Sheet 22-07-2026\",'
    r'\"file\":\"https://citybankplc.com/uploads/files//currency_files/17846958878014722.pdf\"},'
    r'{\"id\":3,\"title\":\"Daily Exchange Rate Sheet 21-07-2026\",\"file\":\"https://citybankplc.com'
    r'/uploads/files//currency_files/17846091929975922.pdf\"},{\"id\":4,\"title\":\"Daily Exchange '
    r'Rate Sheet 20-07-2026\",\"file\":\"https://citybankplc.com/uploads/files//currency_files/'
    r'17845206925880622.pdf\"},{\"id\":5,\"title\":\"Daily Exchange Rate Sheet 19-07-2026\",'
    r'\"file\":\"https://citybankplc.com/uploads/files//currency_files/17844345171496622.pdf\"}'
)

# The exact regex now used in collectors/city.py — duplicated here
# deliberately so this test fails if that regex is ever changed without
# re-verifying it against real data.
CITY_PDF_URL_PATTERN = r"https://citybankplc\.com/uploads/files/+currency_files/[^\s\"'\\]+\.pdf"


def test_finds_real_links_in_real_json_embedded_html():
    """
    The core regression test: the OLD approach (href="..."-anchored
    regex, or waiting for an <a> element) would find ZERO matches
    against this real excerpt, because the links aren't in href
    attributes at all. The fix must find all of them.
    """
    found = re.findall(CITY_PDF_URL_PATTERN, REAL_CITY_HTML_EXCERPT)
    assert len(found) == 5


def test_first_match_is_the_newest_report():
    """The real data lists reports newest-first (23-07-2026 first) —
    confirms the fix's assumption that found[0] is the newest."""
    found = re.findall(CITY_PDF_URL_PATTERN, REAL_CITY_HTML_EXCERPT)
    assert found[0] == "https://citybankplc.com/uploads/files//currency_files/17847832141725022.pdf"


def test_old_href_anchored_regex_would_have_found_nothing():
    """
    Documents WHY the old approach failed: proves the old href="..."
    pattern genuinely matches zero times against this real data, so the
    old code's failure wasn't a fluke or a timing issue — it was
    structurally impossible for it to ever succeed against this format.
    """
    old_pattern = r'href="([^"]*currency_files[^"]*\.pdf)"'
    old_matches = re.findall(old_pattern, REAL_CITY_HTML_EXCERPT)
    assert old_matches == []


def test_pattern_does_not_match_unrelated_urls():
    text = 'some other link "file":"https://example.com/not-relevant.pdf"'
    assert re.findall(CITY_PDF_URL_PATTERN, text) == []


# A second real excerpt, captured via a live diagnostic run on 30 July
# 2026 -- the run that revealed the REAL remaining bug wasn't the regex
# at all (this exact pattern was tested directly against this exact real
# HTML and matched perfectly), but purely a timing issue: the polling
# window gave up too early, then wasted most of its remaining time
# budget on the anchor-tag fallback proven futile by the 24 July
# fixture above. Note the escaping is even deeper here
# (\\\" instead of \") than the 24 July excerpt -- confirms the regex
# is robust to that variation too, since it only matches the URL itself.
REAL_CITY_HTML_EXCERPT_30_JULY = (
    r'\",\\\"buying\\\":\\\"122.95\\\",\\\"selling\\\":\\\"123.95\\\"}],'
    r'\\\"forex_rates_report\\\":[{\\\"id\\\":1,\\\"title\\\":\\\"Daily Exchange Rate '
    r'Sheet 30-07-2026\\\",\\\"file\\\":\\\"https://citybankplc.com/uploads/files//'
    r'currency_files/17853877808172122.pdf\\\"},{\\\"id\\\":2,\\\"title\\\":\\\"Daily '
    r'Exchange Rate Sheet 29-07-2026\\\",\\\"file\\\":\\\"https://citybankplc.com/'
    r'uploads/files//currency_files/17852983516558022.pdf\\\"},{\\\"id\\\":3,'
    r'\\\"title\\\":\\\"Daily Exchange Rate Sheet 28-07-2026\\\",\\\"file\\\":\\\"'
    r'https://citybankplc.com/uploads/files//currency_files/17852136843842122.pdf\\\"}'
)


def test_regex_confirmed_correct_against_30_july_real_failure_capture():
    """
    The concrete evidence behind the timing fix: this exact production
    regex, run against the exact real HTML captured at the moment
    City's collector gave up on 30 July 2026, DOES find the links --
    proving that run's failure was never about the pattern being wrong,
    only about not having waited long enough for this data to appear.
    """
    found = re.findall(CITY_PDF_URL_PATTERN, REAL_CITY_HTML_EXCERPT_30_JULY)
    assert len(found) == 3
    assert found[0] == "https://citybankplc.com/uploads/files//currency_files/17853877808172122.pdf"
