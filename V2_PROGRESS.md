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

## Status: Phase 6 — COMPLETE (forecasting built; AI intentionally deferred by choice)

### What was built

```
core/forecasting/trend.py   summarize_trend(): moving average, min/max,
                              volatility (population std dev), and
                              rising/falling/stable direction, computed
                              from stored history. describe_trend():
                              template-based plain English, NOT AI —
                              a reliable fallback that never depends on
                              an external AI service being available.
```

`core/export.py` now includes a `trends_by_currency` section. Wired in
and tested, but **today's real export shows empty trend lists** — not a
bug, just honest: trends require at least 2 historical observations per
bank, and `v2_history/` currently has exactly 1 real (seeded) observation
per bank. This will start populating automatically, with zero code
changes needed, once the pipeline has actually run more than once.

### Why forecasting didn't need AI at all

Checked the spec's own language here (Ch.8.13, Ch.12.4): "forecasting"
in EuroCompass's own definition starts with moving averages, momentum,
and volatility — plain statistics — with AI listed as a *possible future
enhancement* on top, not a requirement. Built the deterministic half
first because it's free, fully testable, and needed regardless of
whether an AI layer is ever added.

### The AI half — deliberately paused for a decision, not skipped

The spec's AI chapter (Ch.12) is explicit that AI should only ever
*explain*, never replace, the deterministic numbers — which this project
already has (Phase 4's recommendation explanations, now this phase's
trend descriptions). Adding real AI-generated natural-language
explanations on top would require an Anthropic API key of your own, with
its own (small, usage-based) cost — a genuinely different category from
everything built so far, all of which has been free. Given you were
explicit early on about not having premium tooling, this isn't a
decision to make on your behalf. Asked directly in-conversation rather
than assumed.

### Decision: AI-assisted explanations — deferred by choice, not by default

Asked directly; you chose to skip AI for now and keep the deterministic,
template-based explanations (Phase 4's recommendation explanations,
Phase 6's trend descriptions) rather than take on an API key and its
cost. That's a complete, working choice, not a placeholder — nothing in
the platform depends on AI ever being added. If this changes later, the
hook point is well-defined: `core/transfer/recommender.py`'s
`_build_explanation()` and `core/forecasting/trend.py`'s
`describe_trend()` are the two places a natural-language layer would
plug in, without touching any of the underlying deterministic math.

### Verified working

- `pytest core/tests/` → **89/89 passed** (10 new trend/export tests)
- Regenerated the real `v2_exports/latest.json` after the code change —
  confirmed `trends_by_currency` is honestly empty right now (only 1
  data point per bank so far), not fabricated

---

## Full Codebase Audit (requested explicitly: "check every algorithm for bugs")

Went back through every file written across all 6 phases — models,
config, collectors, validation, storage, pipeline, calculator,
recommender, export, forecasting, and the JS worker + dashboard —
looking specifically for logic bugs, not style issues. Found and fixed
**15 real, concrete bugs**, each with a regression test proving the bug
was real and is now closed. Full list, worst-impact first:

1. **Timezone bug (real, frequent):** `check_rate_date_not_future`
   compared a rate's Bangladesh-local publish date against the raw UTC
   collection date. Since Dhaka is UTC+6, any collection running
   18:00–23:59 UTC (i.e. every single day, for ~6 hours) would wrongly
   reject a perfectly fresh, correct rate as "from the future." Proven
   with a concrete repro before fixing. Fixed by converting to Dhaka
   local time before comparing.
2. **Historical validation only checked `buy`, never `sell`** — but
   `core.transfer.calculator`'s entire cost math runs on `sell`. A
   corrupted sell value with a normal-looking buy would previously sail
   through undetected and directly corrupt every recommendation.
3. **A provable one-cent rounding inconsistency**: `total_cost_bdt` was
   computed from raw unrounded numbers while the displayed
   `gross_cost_bdt`/`fees_total_bdt` were rounded separately — found a
   concrete case (via randomized search) where the three numbers
   wouldn't add up by a cent. Fixed by summing the already-rounded parts.
4. **Negative fee amounts were silently applied as discounts** — a
   data-entry sign error could make a bank look artificially cheapest
   and corrupt the ranking. Now rejected with a note instead of applied.
5. **A single corrupted line in a history file could crash loading of
   that bank's ENTIRE history** (e.g. from a process killed mid-write),
   which would then crash the whole collection cycle. Now skipped and
   logged, everything else still loads.
6. **One observation's unexpected failure (e.g. a storage error) could
   silently stop every other bank in the same cycle from being
   processed.** Now isolated per-observation.
7. **A syntax error in any single bank's collector file would crash the
   entire collection cycle**, not just that bank — `except ImportError`
   doesn't catch `SyntaxError`. Proven with an actual broken file before
   fixing; now catches any import-time exception.
8. **Trend direction could be silently inverted**: `summarize_trend`
   trusted the caller to pass observations oldest-first, with no
   enforcement — proven with a concrete repro (reversed input reported
   "falling" for a rate that was actually rising). Now sorts internally.
9. **Explanation notes about a skipped fee were dropped exactly when
   they mattered most** — only shown when `fees_verified` was True, so a
   negative-amount or wrong-currency fee's explanatory note silently
   vanished in the one case (no fee applied) where a user most needed it.
10. **`source_urls` only had an EUR entry for every bank** — every USD
    observation was silently losing its audit source URL, even though
    USD comes from the exact same document as EUR.
11. **`product_id` always defaulted to a bank's first configured
    product**, regardless of what was actually collected — harmless
    today (one product per bank) but a silent mislabeling risk the
    moment any bank gets a second product.
12. **`recommend_for_amount` had no protection against a duplicate
    bank_id** — `breakdowns` and `observations_by_bank` could silently
    disagree about which copy's data was used.
13. **Logging setup crashed the entire `core` package at import time**
    if the working directory wasn't writable (e.g. a restricted CI
    runner) — for something as non-essential as file logging. Now falls
    back to console-only logging, verified with a forced failure, not
    just reasoned about.
14. **EBL's `get_rates()` was the only one of 5 collectors without a
    protective try/except**, an inconsistency vs. the other four.
15. **The dashboard's rates table was hardcoded to show EUR only** —
    once real USD data starts flowing in, it would never have appeared.
    Now renders one table per currency actually present in the data.
16. **None of the new `/v2/*` API routes or Telegram commands handled a
    v2-data load failure** — an API caller got a bare, unhelpful 500;
    a Telegram user got total silence. Now both return/send a clear,
    friendly message instead.

All fixes verified: 105/105 Python tests passing (up from 89 — 16 new
regression tests added specifically for these bugs), 16/16 JS tests
passing, both suites run for real, not assumed. `git diff --stat`
confirms every fix is a targeted, reviewable change — no unrelated
churn.

---

## Live Test Run — 20 July 2026

Attempted a real test against actual bank websites, worked around the
sandbox's network restriction to bank domains by using web search + web
fetch (general internet access) to pull real, current bank pages/PDFs,
then running the *actual* production parsing/validation code from this
repo against that real content. Not a full end-to-end run (the real
`requests`-based download step inside each collector was substituted),
but a genuine test of whether today's real bank data still parses
correctly with today's code — which is the part most likely to have
quietly broken.

### BRAC — ✅ Confirmed working
Fetched the live treasury page, found today's real PDF link via the
exact regex the collector uses (matched correctly), fetched the PDF
(dated 14 Jul 2026), and ran `_extract_currency_buy_sell` — the real
function — against the real extracted text. Result: EUR buy=138.7303
sell=141.4886, USD buy=122.70 sell=123.70. Both plausible, both passed
real validation. Date extraction ("Date 14-Jul-26") also parsed
correctly and correctly flagged as stale.

### EBL — ✅ Confirmed working
The live `/forexrate` page embeds the rate table directly (USD
122.75/123.75, EUR 138.87/143.74, dated 16 Jul 2026). The EUR figures
match v1.0's own last real snapshot *exactly* — strong cross-confirmation
this is genuinely the same live data source v1.0 already uses. Both
currencies passed real validation.

### PRIME — ✅ Confirmed working
Found today's real PDF (dated 16 Jul 2026, filename contains a literal
space — checked separately whether Python's `requests` library handles
this safely, and confirmed it does, auto-encoding it to `%20` when
sending the request, so no code change was needed here). Applied
the real `buy_index=3, sell_index=0` convention to the real row: EUR
buy=139.9964 sell=143.0550 — matches v1.0's last known real value
*exactly*. USD buy=122.75 sell=123.75. Both passed real validation.

### SONALI — ⚠️ Strong circumstantial confirmation, not fully live-tested
The `fxrate-DD-MM-YYYY.pdf` URL pattern was confirmed accurate as
recently as 5 days ago (a real indexed PDF at that exact pattern), and
the table structure/column layout is consistent across many months of
real historical PDFs (checked Jan through July 2026 examples). However,
older dated PDFs appear to get removed from Sonali's server after a few
days — the 5-days-ago URL returned a 404 when fetched directly — and my
tool can't fetch a URL for *today's* exact date without it first
appearing in a search result, which it won't have yet. Genuinely
untested today, but nothing found suggests it's broken; this collector's
own `_candidate_urls_by_date()` fallback (try today, then 1-2 days back)
is already designed for exactly this kind of gap.

### CITY — ❌ Could not test (real limitation, not a bug)
City's collector uses Playwright (a real, JavaScript-executing browser)
specifically because the PDF link isn't present in static HTML — it's
rendered client-side. Neither this sandbox nor the web-fetch tools used
above can execute JavaScript, so this is a genuine blind spot in what
could be verified from here. Every real PDF found for City via search
was weeks-to-months old (cached/indexed, not current), consistent with
the current link never appearing in static HTML at all. **This can only
be confirmed by an actual run in an environment with a real browser** —
i.e. your GitHub Actions, which already has this working today in v1.0.

### Bottom line
3 of 5 banks (BRAC, EBL, Prime) confirmed genuinely working against
real, current data, through the actual production code, not just
reasoned about. 1 (Sonali) has strong indirect evidence and a known,
already-designed-for gap in what could be tested from here. 1 (City) is
a real, structural blind spot for this kind of remote testing — it needs
an actual browser-capable run to confirm, which this repo's existing
GitHub Actions workflow already provides.

---

## Investigating the two live production failures (City, Sonali)

The live test run above surfaced something important beyond just
testing v2: **v1.0's actual live production system currently has two
real, active failures.** Checked `history/CITY.csv` and
`history/SONALI.csv` directly:
- **City Bank**: last successful collection was **13 July** — over a
  week of silent failures, invisible because nothing alerts on this.
- **Sonali Bank**: last successful collection was **1:18 AM on 20 July**
  — a fresh break, only hours old at the time of investigation.

### Sonali — second attempt, grounded in real diagnostic data
The diagnostic output revealed the real cause: `extract_tables_from_pdf`
finds **zero tables** in Sonali's PDF at all — pdfplumber's line-based
table detector doesn't recognize any structure in it, despite the PDF
clearly containing a rate table visually. This meant the first fix
(normalizing currency-label punctuation) never even got a chance to run
— there were no table cells to search. The real fix needed to work on
raw text instead, the same approach BRAC already uses, which Sonali's
`get_rates()` had deliberately been built without.

Built from the actual real text captured in the diagnostic dump, not
guessed:
- `utils/pdf_utils.py`: `find_all_currency_token_windows()` — a generic
  text-based currency-label finder (the free-text equivalent of
  `find_currency_row`), returning every occurrence with its surrounding
  tokens, since a currency code can legitimately appear more than once
  in a document for unrelated reasons (Sonali's PDF has an earlier
  "cross rates" reference section that also uses "EUR" as a mere unit
  label). Caught and fixed a real bug in this function before it
  shipped: normalization strips digits along with punctuation, which let
  pure numeric tokens silently vanish into a multi-token label match
  ("123.7500 123.7500 u.s.DoLLAR" collapsing into one 3-token match) —
  fixed by excluding numeric tokens from multi-token combining.
- `collectors/sonali.py`: `_extract_via_text_fallback()` — Sonali-
  specific interpretation of the real confirmed row structure
  (`sell, sell, LABEL, buy, ...` — the sell rate appears twice
  immediately before the label), used to disambiguate the real dealing-
  rate row from the unrelated cross-rates section.

Verified against the actual real text from the live failing run (not
synthetic examples): correctly extracts EUR buy=140.07 sell=142.6482,
USD buy=122.75 sell=123.75 — both pass real validation. 8 new tests
using this real fixture text, including a specific regression test for
the numeric-token-swallowing bug caught during development.

122/122 tests passing. **Not yet re-verified against another live
run** — that's the next step, and the honest confirmation this actually
works in production, not just against the one captured sample.



### City — attempted fix, confidence NOT claimed, still failing as of last test
Investigated whether City's PDF URL pattern
(`/uploads/files/currency_files/...`) had changed, since it changed
once before historically. Found real examples of that exact pattern
still in use as recently as 11 June 2026 — fairly close to the 13 July
last-success date, weakening the "pattern changed" theory. Fetched the
raw (non-JS) page directly and confirmed it's genuinely just a
near-empty client-rendered shell, not a bot-detection wall — no new
smoking gun there either.

Added one well-reasoned, standard mitigation: masked
`navigator.webdriver` (a common, well-documented automation "tell" that
Playwright sets by default and that many sites specifically check,
regardless of how realistic the user-agent looks) — something the
existing code's own comments already suspected as a cause but never
fully addressed. **Re-ran the live workflow — City still failed with
the same timeout.** This fix may still be worth keeping (low-risk,
standard practice), but it did not resolve the issue, and that's being
stated plainly rather than glossed over. City's root cause remains
genuinely undiagnosed — properly debugging a client-rendered site's
automation failure really needs to watch an actual browser session
(e.g. Playwright's own trace/screenshot tooling), which isn't something
achievable through this chat-based workflow.

## For the non-technical project owner

Plain-language summary of Phase 1: EuroCompass now has a proper internal
"vocabulary" (what a Bank is, what a Currency is, what an Observation is)
that every future part of the platform will share, instead of each part
inventing its own version. Your 5 existing bank collectors were plugged
into this new structure without changing what they actually do — think of
it as building a proper filing cabinet around documents that already
existed, not rewriting the documents. Everything was tested and confirmed
working before being pushed. Your live site was not touched.
