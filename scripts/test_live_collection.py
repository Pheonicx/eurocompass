"""
scripts/test_live_collection.py

Manual diagnostic script: runs the real v2 collection + validation
pipeline against every configured bank, and prints a clear,
human-readable summary of what happened.

This is deliberately NOT part of the production pipeline and does NOT
write anything to v2_history/ or anywhere else — it only collects and
validates, then reports. Nothing is persisted, nothing is pushed. It
exists purely to answer one question: "does live collection actually
work right now, against real bank websites?" — something that can only
be tested from an environment with real internet access and (for City
Bank specifically) a real browser, neither of which exist in Claude's
own sandbox.

Run it with:
    python scripts/test_live_collection.py
"""

from __future__ import annotations

from core.collectors.registry import collect_all
from core.config.loader import load_config
from core.validation.validator import validate


def main() -> None:
    config = load_config()

    print("=" * 70)
    print("EuroCompass v2 — Live Collection Test")
    print("=" * 70)
    print(f"Testing {len(config.banks)} banks: {', '.join(config.banks)}")
    print("(This is a diagnostic run only — nothing is saved or pushed.)")
    print()

    observations = collect_all(config)

    by_bank: dict[str, list] = {bank_id: [] for bank_id in config.banks}
    for obs in observations:
        by_bank[obs.bank_id].append(obs)

    all_ok = True

    for bank_id in config.banks:
        obs_list = by_bank[bank_id]

        if not obs_list:
            print(f"❌ {bank_id}: NO DATA COLLECTED — see the log above this line for the specific error")
            all_ok = False
            continue

        print(f"✅ {bank_id}: collected {len(obs_list)} observation(s)")
        for obs in obs_list:
            result = validate(obs, config, recent_history=[])
            status = "ACCEPTED" if result.accepted else f"REJECTED ({result.reason})"
            print(f"    {obs.currency}: buy={obs.buy}  sell={obs.sell}  ->  {status}")
            if not result.accepted:
                all_ok = False

    print()
    print("=" * 70)
    if all_ok:
        print("✅ ALL BANKS: data collected and validated successfully.")
    else:
        print("⚠️  Some banks had problems — see the details above.")
    print("=" * 70)


if __name__ == "__main__":
    main()
