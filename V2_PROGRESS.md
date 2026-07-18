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

## Status: Phase 3 — Validation & Historical Storage ✅ COMPLETE

### What was built

```
core/validation/
├── rules.py        Business validation (per-currency plausible rate
│                     range + spread, configurable — not hardcoded) and
│                     cross-field validation (rate_date can't be future)
├── historical.py    Compares a new observation to the most recent
│                     accepted one for the same bank/currency/product;
│                     rejects sudden implausible jumps (default: >5%)
└── validator.py      Orchestrates: business -> cross-field -> historical
                       -> accept/reject, with every rejection logged

core/storage/
└── observation_store.py   Append-only JSONL storage, one file per bank,
                             under v2_history/ (brand-new location —
                             v1.0's history/*.csv is completely untouched)

core/pipeline.py      run_collection_cycle(): collect -> validate -> store,
                       end to end. NOT wired to any schedule yet — it's a
                       function that exists and is tested, nothing calls
                       it automatically.
```

### Key decisions

- **Validation thresholds are evidence-based, not guessed.** Before
  picking numbers, checked real EUR/BDT (~140-145) and USD/BDT (~122-123)
  rates via web search (mid-2026). Ranges set wider than the observed
  band (EUR: 120-170, USD: 100-150) so normal market movement over
  months won't trigger false rejections, while still catching a parser
  grabbing a wildly wrong number. The reasoning is written directly into
  `core/config/banks.json` as a `_threshold_basis` field, not left as an
  unexplained magic number.
- **Immutability is enforced structurally, not just by convention.**
  `observation_store.append()` only ever opens files in append mode —
  there's no code path that can overwrite an old record, so "historical
  observations are immutable" is guaranteed by how the function is
  written, not just a rule everyone has to remember to follow. Proven
  with a dedicated test (`test_multiple_appends_never_overwrite_earlier_ones`).
- **A rejected observation never reaches storage.** Proven with a test
  that intentionally feeds in an implausible rate and confirms nothing
  gets written to disk.
- **Historical validation only rejects, never silently downgrades.**
  Per CLAUDE.md ("prefer false warnings over false confidence"), a
  suspicious jump is rejected outright rather than accepted with lower
  confidence — a rejected observation is loud and visible; a silently
  "less trusted" one could still slip into a future recommendation.
- **New bank/currency combos always get their first data point.** The
  historical check only compares against existing history — with none
  yet, it always passes, so nothing about validation blocks onboarding a
  6th bank or a 3rd currency later.

### Verified working (all run inside the sandbox before committing)

- `pytest core/tests/` → **49/49 passed** (27 new tests this phase)
- Confirmed no test run left stray data in the real repo (`v2_history/`
  doesn't exist — every test uses a temporary directory, `git status`
  shows only intended source files)
- Integration test proves a second collection cycle correctly uses the
  first cycle's stored history to catch an implausible jump — i.e. the
  full collect → validate → store loop works across separate runs, the
  way separate hourly runs would behave

---

## Status: Phase 4 — Core Intelligence (Recommendation Engine, Transfer Calculator) ✅ COMPLETE

### What was built

```
core/transfer/
├── calculator.py    calculate_transfer_cost(): deterministic total-cost
│                     math (exchange rate × amount + fees). Base unit is
│                     BDT throughout.
├── recommender.py    generate_recommendation(): ranks banks by real
│                     total cost, builds a mandatory plain-English
│                     explanation for every recommendation
└── service.py        recommend_for_amount(): the one function future
                       interfaces (dashboard/Telegram/API) should call —
                       combines the two above so business logic exists
                       exactly once
```

### The most important thing this phase addresses

Checked v1.0's actual calculator (`services/calculator.py`): it computes
`sell_rate × amount` and nothing else — **no fee data exists anywhere in
the system**, for any bank. That's precisely the gap the specification
calls out repeatedly ("exchange rates alone are not enough... choosing
the bank with the best exchange rate does not necessarily produce the
lowest total cost"). This phase builds a calculator that's fully
fee-aware (flat fees, percentage fees, multiple fees combined) — but
since no real fee data has been collected from any bank yet, it does
NOT pretend fees are zero. Every result carries a `fees_verified` flag,
and a recommendation with unverified fees explicitly says so in its
explanation ("No verified fee data is available yet for this bank...")
and has its confidence capped at MEDIUM even if the underlying exchange
rate was collected with HIGH confidence. This is a deliberate trust
decision, not an oversight — a confident-looking total built on an
unverified assumption is exactly what CLAUDE.md's "prefer false warnings
over false confidence" principle warns against.

### Every recommendation explains itself (spec 9.11 requirement)

Each `Recommendation.explanation` is auto-generated plain text covering:
which bank and why, the exact numbers behind the total cost, whether
fees were actually included, how much more the next-best option would
cost, all other options considered, a stale-rate warning if relevant,
and the overall confidence level. This isn't a template filled in
later — it's produced by the same function that ranks the banks, so an
explanation can't accidentally go missing from a real recommendation.

### A real bug my own tests caught before it shipped

`fees_verified` was originally set based on whether fee objects were
*supplied* to the calculator, not whether any were actually *applied* to
the total. A fee stated in an unsupported currency gets skipped (with a
note) rather than converted — but the original code still marked the
result as "fees verified" even though nothing was actually added to the
total. `test_fee_in_unsupported_currency_is_skipped_with_a_note` caught
this immediately; fixed to check `len(applied) > 0` instead of
`len(fees) > 0`. Left in V2_PROGRESS.md deliberately, as a concrete
example of why the test-before-commit habit matters here, not just a
box-ticking exercise.

### Verified working (all run inside the sandbox before committing)

- `pytest core/tests/` → **74/74 passed** (25 new tests this phase)
- Confirmed no stray files or test data leaked into the real repo

---

## Status: Phase 5 — User Interfaces — IN PROGRESS (Dashboard done; Telegram + API not started)

### What was built

```
core/export.py          Turns validated observations + recommendations
                          into a plain JSON file (v2_exports/latest.json),
                          following v1.0's exact zero-server pattern:
                          Python computes once, writes JSON, a static
                          page reads it — no paid hosting needed.

site/v2/index.html       A NEW dashboard page (v1.0's site/index.html is
                          untouched). Shows explained recommendations and
                          a rate comparison table. Matches v1.0's visual
                          style (same gold/navy palette, same fonts) so
                          it doesn't feel like a different product.
```

### Important architecture decision

v1.0's dashboard is a static site on Cloudflare — deliberately zero
server cost. Phase 5 follows that same pattern rather than introducing a
paid backend: `core/export.py` writes a plain JSON file, and
`site/v2/index.html` fetches it directly from GitHub's raw file server
(same trick v1.0's own dashboard already uses). No new hosting, no new
cost, nothing that requires Claude Code or any paid tool to keep running.

### Real data, honestly labeled

`v2_history/` now contains real EUR rates for BRAC, EBL, PRIME, and
SONALI — but these were **seeded from v1.0's last actual collection**
(2026-07-16, taken from the live `exports/latest.json`), not from a live
v2.0 pipeline run. Every seeded observation's metadata says exactly
this (`"seeded_from": "v1.0 exports/latest.json, 2026-07-16..."`), so
nobody looking at this data later mistakes it for a confirmed v2.0
collection. City Bank has no seed data because it wasn't present in
v1.0's last snapshot either (its collector is the most complex/fragile
of the five — a known v1.0 characteristic, not something Phase 5 caused).

`v2_exports/latest.json` was generated for real from that seed data —
it's not a mockup. It correctly shows BRAC as cheapest, a MEDIUM
confidence (capped because fees aren't verified yet AND the seed data is
flagged stale), and a full plain-English explanation.

### Not done yet in Phase 5

- **This page isn't live/viewable yet.** It's pushed to `v2-dev`, but
  Cloudflare only auto-deploys from `main` (confirmed back when we
  decided to use a branch instead of a separate repo). It'll become
  viewable once merged, or you can check whether Cloudflare happens to
  create an automatic preview URL for non-main branches (depends on
  account settings I can't see from here).
- **The USD scenario was skipped** in this export — no USD data has
  actually been collected/seeded yet, only EUR. Once Phase 2's USD
  collectors run for real, USD will appear automatically (no code
  change needed).
- Telegram bot integration and a public API — next up.

### Verified working (all run inside the sandbox before committing)

- `pytest core/tests/` → **79/79 passed** (5 new tests this phase)
- `core/export.py` run for real against seeded data — output inspected
  by hand, numbers check out (e.g. BRAC total = 1000 × 142.4326 =
  142,432.60 BDT, matches exactly)
- Dashboard's embedded JavaScript syntax-checked with Node
- Confirmed `git status` shows only new, intended files — nothing in
  v1.0's `site/`, `exports/`, or `history/` was touched

---

## Status: Phase 5 — Telegram + API — ✅ COMPLETE (correcting an earlier mistake)

### A correction, stated plainly

The previous entry said "Telegram bot integration, Public API — NOT
STARTED." That was **wrong** — I hadn't yet looked closely at
`worker/telegram-worker/`. v1.0 already has a live, working Telegram bot
AND a public API, both running as a single Cloudflare Worker
(`worker/telegram-worker/src/index.js`):
- Telegram commands: `/start`, `/help`, `/rates`, `/status`, `/recommend <amount>`
- Public HTTP API: `/health`, `/rates`, `/summary`, `/banks`, `/best`

This is genuinely well-built for a zero-cost setup: no server, reads
straight from `exports/latest.json` on GitHub. Correcting the record
here rather than quietly moving on, since an inaccurate status entry
would mislead whoever (including me, next session) reads this file next.

### What was actually built this phase

Rather than building a second bot/API from scratch, extended the
existing one — same additive discipline as every other phase:

- `worker/telegram-worker/src/formatter.js` (was an empty, unused file):
  pure formatting functions for v2 data. No business logic — the actual
  recommendation math still lives only in Python (`core/transfer/`);
  these functions just turn already-computed JSON into readable text.
- `worker/telegram-worker/src/index.js`: added three new HTTP routes
  (`/v2/health`, `/v2/rates`, `/v2/recommendations`) and three new
  Telegram commands (`/v2`, `/v2rates`, `/v2recommend <currency> <amount>`),
  reading from `v2_exports/latest.json`. All of v1's existing
  routes/commands are untouched — confirmed with `git diff --stat`:
  134 insertions, 0 deletions.

### A real bug my own tests caught here too

My first attempt placed the new `/v2/*` route checks *after* the line
where v1's code unconditionally loads v1's data (`const data = await
loadData()`) for any path that isn't `/` or `/health`. That meant a
request to `/v2/rates` would first try (and could fail on) loading v1
data it didn't even need. `index.test.js` caught this immediately
(tests failed with "Unable to load market data" even though the test
never touched v1's data source). Fixed by moving the v2 route checks
before that line. Left in here on purpose, same as the fees_verified
bug in Phase 4 — this is what the tests are for.

### Known, honest limitation

`/v2recommend` only works for the handful of amounts already
pre-computed into `v2_exports/latest.json` (currently 1,000 EUR, 12,208
EUR, 1,000 USD) — it can't compute a brand-new arbitrary amount on the
spot the way v1's `/recommend` can, because the real fee-aware
recommendation math lives in Python, not in this JavaScript worker, and
there's no live bridge between them yet. Today this doesn't cost
anything in practice (no fees exist anywhere yet, so v1's simpler EUR-only
math and v2's math currently produce identical numbers) — but this is a
real architectural gap to solve before v2 fully replaces v1's `/recommend`:
either pre-compute more amounts, or build a proper on-demand compute
path. Not solved today; flagged honestly instead of papered over.

### Verified working

- `pytest core/tests/` → 79/79 (unchanged this phase, no Python edits)
- `npx vitest run` in `worker/telegram-worker/` → **16/16 passed**,
  running in the real Cloudflare Workers test runtime (not a plain Node
  approximation) — 11 for the pure formatter functions, 5 integration
  tests hitting the actual routing logic with mocked network calls
- Confirmed v1's existing routes still behave identically (explicit
  test: `existing v1 routes are untouched by these additions`)
- `git diff --stat` on both changed files: purely additive, 0 deletions

---

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
