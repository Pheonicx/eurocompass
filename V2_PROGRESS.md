# EuroCompass v2.0 — Progress Log

**Read this file first at the start of every new session.** It's the
single source of truth for what's been built, what decisions were made
and why, and what comes next — so work can resume without re-explaining
context or re-doing anything.

Branch: `v2-dev`. `main` is untouched and keeps running v1.0 exactly as before.

---

## Status: Phase 1 — Foundation ✅ COMPLETE

### What was built

A new `core/` package, sitting *alongside* the existing v1.0 code without
modifying any of it:

```
core/
├── models.py                     Domain models: Currency, Product, Fee,
│                                  Bank, Observation (immutable)
├── config/
│   ├── banks.json                 Data-driven bank/currency/product registry
│   └── loader.py                  Loads + validates banks.json
├── collectors/
│   ├── base.py                    Collector plugin interface
│   ├── legacy_adapter.py          Wraps v1.0's collectors/*.py get_rate()
│   │                               functions — calls them AS-IS, translates
│   │                               their dict result into an Observation
│   └── registry.py                collect_all() / collect_one(bank_id) —
│                                   the one entry point everything downstream
│                                   should use
├── logging_setup.py               Structured logging (separate from v1.0's
│                                   utils/logger.py, doesn't touch it)
└── tests/                         17 tests, all passing
```

### Key decisions

- **Additive, not a rewrite.** Nothing under `collectors/`, `config/`,
  `services/`, `site/`, `telegram_bot/`, `worker/`, `main.py` was changed.
  v1.0's hourly GitHub Action and live dashboard keep working exactly as
  before, on `main`, completely unaffected by this branch.
- **Legacy collectors wrapped, not rewritten.** `core/collectors/legacy_adapter.py`
  imports the *existing* `collectors/brac.py` (etc.) and calls the
  *existing* `get_rate()` function. The scraping/PDF-parsing logic itself
  was not touched. If a bank's collector breaks, the fix belongs in that
  bank's own file, same as today.
- **Config over hardcoding.** `core/config/banks.json` replaces the
  hardcoded `BANKS = [...]` list conceptually — adding a 6th bank later
  means adding one JSON entry + one collector file, not touching the
  registry or any downstream code.
- **All 5 banks currently marked `source_type: pdf`**, confirmed by
  checking which collectors import `utils/pdf_utils`.
- **Confidence scoring is intentionally simple for now**: MEDIUM by
  default, LOW if the bank's own `is_stale` flag is set. Phase 3
  (Validation) will make this more rigorous — this was a deliberate
  "simplest solution that works" choice per CLAUDE.md, not an oversight.

### Verified working (all run inside the sandbox before committing)

- `pytest core/tests/` → **17/17 passed**
- Confirmed `core/config/loader.py` correctly loads and validates all 5
  real banks from `banks.json`
- Confirmed every configured bank's `collector` path (`collectors.brac`,
  `collectors.city`, etc.) actually imports and has a `get_rate()`
  function — the wiring to the real v1.0 code is correct
- Confirmed `config/banks.py` (v1.0's original file) and `main.py` still
  import without error — nothing broke

**Not yet tested:** actually calling `get_rate()` against the real bank
websites (this sandbox can't reach bank sites — only a small allowlist of
domains). That should be verified from your machine or CI before we trust
live collection through the new adapter.

---

## Status: Phase 2 — Knowledge Acquisition ✅ COMPLETE (USD support)

### What was built

USD support for all 5 banks, added the safest way possible: **every
change is a pure addition — zero existing lines in any collector file
were modified.** Verified with `git diff --stat`: 368 insertions, 0
deletions, across `collectors/brac.py`, `city.py`, `ebl.py`, `prime.py`,
`sonali.py`.

- Each collector got a new `get_rates(currencies=("EUR","USD"))` function,
  added *below* the original `get_rate()`. `get_rate()` itself was not
  touched — v1.0's `main.py` calls it exactly as before and gets exactly
  what it always got.
- `get_rates()` reuses the **same already-downloaded PDF/HTML** that
  `get_rate()` would fetch — extracting an extra currency row costs zero
  extra requests to any bank's servers. This was possible because all 5
  banks' documents already contain multiple currencies in one table/page;
  we're just reading one more row, not fetching a new document.
- `core/collectors/legacy_adapter.py` now prefers a collector's
  `get_rates()` when present, and only falls back to the old single-
  currency `get_rate()` path for a collector that hasn't been upgraded.
  This means upgrading banks one at a time (already done for all 5 here)
  never breaks anything for banks that haven't been touched yet.
- `core/config/banks.json`: all 5 banks now list `["EUR", "USD"]`.

### Known limitations (documented honestly, not hidden)

- **Not yet verified against live bank websites.** This sandbox cannot
  reach bank domains (only a small safe allowlist). Every extraction
  helper used is the same one already proven to work for EUR
  (`find_currency_row`, `extract_buy_sell`, `extract_buy_sell_by_repetition`),
  now just also being pointed at the USD row — so the *risk* is low, but
  it is not the same as a confirmed live result. **Before fully trusting
  USD data**, run collection for real (locally, or via a manual GitHub
  Actions run) and sanity-check the USD numbers against what each bank's
  site actually shows.
- City's `get_rates()` does not fall back to the private reverse-engineered
  API the way `get_rate()` does — that fallback was written narrowly for
  EUR only. If City's PDF/browser method fails, `get_rates()` returns `[]`
  for that run (get_rate() is unaffected either way).
- Sonali's last-resort plain-text fallback (used only if table extraction
  fails completely) is written specifically for the word "EURO" and was
  not generalized to USD. If Sonali's table extraction fails, USD is
  simply omitted for that run rather than guessed at.
- All 22 tests pass (`pytest core/tests/`), including new tests that
  confirm the adapter prefers `get_rates()` when available, falls back
  correctly when it isn't, survives a crashing collector, and that all 5
  real collector modules do expose the new function — but these tests
  use fake/mocked data, not live bank responses, for the reason above.

### Verified working (all run inside the sandbox before committing)

- `pytest core/tests/` → **22/22 passed**
- `git diff --stat collectors/` → 368 insertions, 0 deletions (provably
  additive-only change)
- All 5 collector files + the adapter compile cleanly
- Config loads correctly with `USD` added to all 5 banks

---

## Status: Phase 2 — remaining scope — NOT STARTED
- Decide whether to keep using `collectors/*.py` as the long-term home
  for bank logic, or gradually give banks purpose-built v2.0 collectors
  (spec allows either — "banks as plugins" doesn't require a specific
  implementation style)
- Generic PDF/HTML fetching helpers as a shared utility, if useful beyond
  what `utils/pdf_utils.py` already provides

## Status: Phase 3 — Validation & Historical Storage — NOT STARTED
## Status: Phase 4 — Core Intelligence (Recommendation Engine, Transfer Calculator) — NOT STARTED
## Status: Phase 5 — User Interfaces (Dashboard, Telegram, API) — NOT STARTED
## Status: Phase 6 — Intelligence Enhancements (Forecasting, AI) — NOT STARTED

---

## For the non-technical project owner

Plain-language summary of Phase 1: EuroCompass now has a proper internal
"vocabulary" (what a Bank is, what a Currency is, what an Observation is)
that every future part of the platform will share, instead of each part
inventing its own version. Your 5 existing bank collectors were plugged
into this new structure without changing what they actually do — think of
it as building a proper filing cabinet around documents that already
existed, not rewriting the documents. Everything was tested and confirmed
working before being pushed. Your live site was not touched.
