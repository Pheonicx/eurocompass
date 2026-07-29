"""
scripts/test_v2_pipeline_e2e.py

Diagnostic-only, manual-trigger script: runs v2's FULL pipeline --
collect -> validate -> store -> export -- against real bank websites,
using a real internet connection (this only works from an environment
like GitHub Actions; local sandboxes without bank-site network access
can't run this meaningfully).

Unlike scripts/test_live_collection.py (which only proves collection
works), this proves the whole chain: that collected observations
actually pass validation, round-trip through the JSONL observation
store correctly, and produce a well-formed v2_exports/latest.json --
something no test so far has verified end-to-end against real data.

Writes ONLY to a temporary directory (never core/storage's real
v2_history/ or the real v2_exports/latest.json) and prints a full
summary. Nothing is committed or pushed by this script. That's a
deliberate, separate decision for later -- this script's only job is
to answer "does the real chain actually work?"
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import traceback
from pathlib import Path

sys.path.insert(0, ".")

from core.config.loader import load_config
from core.export import build_export
from core.pipeline import run_collection_cycle


def main() -> int:
    print("=" * 70)
    print("v2 FULL PIPELINE END-TO-END DIAGNOSTIC (collect -> validate -> store -> export)")
    print("=" * 70)

    tmp_dir = Path(tempfile.mkdtemp(prefix="eurocompass_v2_e2e_"))
    print(f"\nUsing temporary storage dir: {tmp_dir}")
    print("(nothing under this run touches the real v2_history/ or v2_exports/)\n")

    exit_code = 0

    try:
        cfg = load_config()
        print(f"Config loaded: {len(cfg.banks)} banks configured: {list(cfg.banks.keys())}\n")

        print("-" * 70)
        print("STAGE 1+2+3: collect -> validate -> store")
        print("-" * 70)
        summary = run_collection_cycle(config=cfg, storage_dir=tmp_dir)

        print(f"\nCollected:  {summary.collected}")
        print(f"Accepted:   {summary.accepted}")
        print(f"Rejected:   {summary.rejected}")

        if summary.rejections:
            print("\nRejections:")
            for bank_id, reason in summary.rejections:
                print(f"  - {bank_id}: {reason}")

        if summary.collected == 0:
            print(
                "\n⚠️  WARNING: zero observations collected from ANY bank. "
                "This likely means something is wrong with the collection "
                "environment itself (network, Playwright), not a per-bank issue."
            )
            exit_code = 1

        print("\n" + "-" * 70)
        print("STAGE 4: export")
        print("-" * 70)
        export_data = build_export(config=cfg, storage_dir=tmp_dir)

        rates_summary = {
            currency: len(rates) for currency, rates in export_data["rates_by_currency"].items()
        }
        print(f"\nCurrencies with rate data: {rates_summary}")
        print(f"Recommendations generated: {len(export_data['recommendations'])}")

        if not export_data["rates_by_currency"]:
            print(
                "\n⚠️  WARNING: export produced zero currencies with rate data, "
                "even though the pipeline may have accepted observations. "
                "Check core/export.py's DEFAULT_SCENARIOS against what was "
                "actually collected (currency/product_id mismatch is the "
                "most likely cause)."
            )
            exit_code = 1

        print("\nSample of exported JSON (first recommendation, if any):")
        if export_data["recommendations"]:
            print(json.dumps(export_data["recommendations"][0], indent=2))
        else:
            print("  (none generated)")

        print("\n" + "=" * 70)
        if exit_code == 0 and summary.accepted > 0:
            print("RESULT: ✅ Full pipeline chain verified working end-to-end.")
        else:
            print("RESULT: ⚠️  Pipeline ran without crashing, but see warnings above.")
        print("=" * 70)

    except Exception:
        print("\n" + "=" * 70)
        print("RESULT: ❌ Pipeline CRASHED (did not complete)")
        print("=" * 70)
        traceback.print_exc()
        exit_code = 2

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
