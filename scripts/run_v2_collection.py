"""
scripts/run_v2_collection.py

The real, scheduled entrypoint for v2's collection pipeline — what
.github/workflows/update_v2_rates.yml actually runs. Collects from
every configured bank, validates, permanently stores accepted
observations in v2_history/, and writes v2_exports/latest.json.

Distinct from scripts/test_v2_pipeline_e2e.py and
scripts/test_v2_collection.yml's script, both of which are diagnostic-
only and deliberately never write to the real storage locations. This
script is the real thing — every observation it accepts is stored
permanently.

Reads storage_dir/export_path from core.storage.observation_store and
core.export's module-level constants explicitly at call time, and
passes them through to run_collection_cycle()/build_export() rather
than relying on those functions' own default argument values. Default
argument values in Python are bound once, at function-definition
(import) time — relying on that binding would mean this script (and
tests of it) couldn't change where data goes without editing those
modules directly. Reading the constant fresh each call and passing it
explicitly avoids that entirely.

Exit code reflects whether anything was actually accepted this cycle:
0 if at least one observation was accepted (a partial cycle, e.g. only
3 of 5 banks succeeding, is still a normal, expected outcome and exits
0 — one bank failing must never fail the whole workflow run). Exits 1
only if literally nothing was collected from any bank, which likely
means something is wrong with the environment itself, not a single
bank's site.
"""

from __future__ import annotations

import json
import sys

sys.path.insert(0, ".")

import core.export as export_module
import core.storage.observation_store as observation_store_module
from core.config.loader import load_config
from core.export import build_export
from core.pipeline import run_collection_cycle

# NOTE: this script only writes files locally (v2_history/, v2_exports/).
# Committing and pushing them to git is handled by the GitHub Actions
# workflow itself (a plain git commit + push after this script runs),
# not by this script. utils.github_sync.upload_file() -- what v1's
# main.py uses -- has no branch parameter and implicitly targets the
# repo's default branch (main); using it here would risk silently
# writing v2's pipeline output onto the live production branch instead
# of v2-dev. A plain git push, operating on whatever branch the
# workflow already checked out, avoids that risk entirely rather than
# adding branch-targeting logic to shared v1 infrastructure.


def main() -> int:
    print("=" * 70)
    print("v2 COLLECTION CYCLE")
    print("=" * 70)

    cfg = load_config()
    storage_dir = observation_store_module.DEFAULT_STORAGE_DIR
    export_path = export_module.DEFAULT_EXPORT_PATH

    summary = run_collection_cycle(config=cfg, storage_dir=storage_dir)

    print(f"\nCollected:  {summary.collected}")
    print(f"Accepted:   {summary.accepted}")
    print(f"Rejected:   {summary.rejected}")

    if summary.rejections:
        print("\nRejections:")
        for bank_id, reason in summary.rejections:
            print(f"  - {bank_id}: {reason}")

    if summary.collected == 0:
        print(
            "\n⚠️  Nothing was collected from ANY bank this cycle. This "
            "likely means something is wrong with the collection "
            "environment itself (network, Playwright), not a per-bank "
            "issue — worth investigating even though no data was lost "
            "(existing history is untouched)."
        )
        return 1

    print("\n" + "-" * 70)
    print("Building export...")
    export_data = build_export(config=cfg, storage_dir=storage_dir)

    export_path.parent.mkdir(parents=True, exist_ok=True)
    export_path.write_text(json.dumps(export_data, indent=2))

    rates_summary = {
        currency: len(rates) for currency, rates in export_data["rates_by_currency"].items()
    }
    print(f"Currencies exported: {rates_summary}")
    print(f"Recommendations: {len(export_data['recommendations'])}")
    print("\n✅ Cycle complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
