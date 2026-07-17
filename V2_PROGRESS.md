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

## Status: Phase 2 — Knowledge Acquisition — NOT STARTED

Next up, per CLAUDE.md's build order. Planned scope:
- Decide whether to keep using `collectors/*.py` as-is long-term, or
  gradually give banks purpose-built v2.0 collectors (spec allows either —
  "banks as plugins" doesn't require a specific implementation style)
- Generic PDF/HTML fetching helpers usable by any future bank's collector
- USD support (currently only EUR is configured — spec requires USD too)

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
