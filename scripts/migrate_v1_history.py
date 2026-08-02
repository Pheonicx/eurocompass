"""
scripts/migrate_v1_history.py

One-time migration: v1's history/*.csv files have several real weeks of
actual collected EUR rates (running since project inception). Rather
than starting v2's history from zero, this migrates that data in --
but NOT blindly. Historical CSV rows never passed v2's validation
pipeline (it didn't exist yet when most of them were collected), and
this project has already found and fixed real extraction bugs
(Sonali's USD garbling, City's various issues) during this session
alone -- it's entirely possible some historical rows are wrong. Every
row is run through the actual validation pipeline
(core.validation.rules + core.validation.historical), in chronological
order, exactly as if it had just been collected live. Rows that fail
are reported and skipped, not silently dropped and not force-accepted.

Honesty about what we don't know: v1's CSV doesn't record HOW each
row was collected (which fallback method, API vs PDF vs HTML) or an
independent confidence assessment. Rather than guess a specific source
type we can't verify per-row, migrated observations are marked
SourceType.OTHER with Confidence.MEDIUM and a clear metadata flag --
an honest "this is real historical data, migrated, not independently
re-verified" characterization, not an invented one.
"""

from __future__ import annotations

import csv
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, ".")

from core.config.loader import load_config
from core.models import Confidence, Observation, SourceType
from core.storage import observation_store
from core.validation.historical import check_against_recent_history
from core.validation.rules import check_business_rules

PRODUCT_ID = "TT"
SOURCE_NOTE = "Migrated from v1 history/*.csv — original per-row source method not recorded"


def _parse_row(bank_id: str, row: dict) -> Observation | None:
    try:
        dt = datetime.strptime(
            f"{row['Date']} {row['Time']}", "%Y-%m-%d %H:%M:%S"
        ).replace(tzinfo=timezone.utc)  # main.py ran on GitHub Actions runners, which default to UTC
        return Observation(
            bank_id=bank_id,
            currency=row["Currency"],
            product_id=PRODUCT_ID,
            buy=float(row["Buy"]),
            sell=float(row["Sell"]),
            collected_at=dt,
            source_type=SourceType.OTHER,
            confidence=Confidence.MEDIUM,
            raw_source=SOURCE_NOTE,
            metadata={"migrated_from_v1_history": True},
        )
    except (ValueError, KeyError) as e:
        print(f"  SKIPPED (unparseable row): {row} — {e}")
        return None


def migrate_bank(csv_path: Path, bank_id: str, cfg, storage_dir: Path) -> tuple[int, int]:
    if not csv_path.exists():
        print(f"{bank_id}: no history file found, skipping")
        return 0, 0

    accepted = 0
    rejected = 0
    recent_by_currency: dict[str, list[Observation]] = {}

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = [_parse_row(bank_id, row) for row in reader]

    rows = [r for r in rows if r is not None]
    rows.sort(key=lambda o: o.collected_at)  # chronological, oldest first, so validation sees real history in order

    for obs in rows:
        currency_cfg = cfg.currencies.get(obs.currency)
        if currency_cfg is None:
            print(f"  REJECTED [{obs.collected_at.date()}]: unknown currency '{obs.currency}'")
            rejected += 1
            continue

        reason = check_business_rules(obs, currency_cfg)
        if reason is None:
            recent = recent_by_currency.get(obs.currency, [])
            reason = check_against_recent_history(obs, recent)

        if reason:
            print(f"  REJECTED [{obs.collected_at.date()}]: {reason}")
            rejected += 1
            continue

        observation_store.append(obs, storage_dir=storage_dir)
        recent_by_currency.setdefault(obs.currency, []).insert(0, obs)  # most-recent-first, matching load_recent's contract
        accepted += 1

    print(f"{bank_id}: {accepted} accepted, {rejected} rejected (of {len(rows)} parsed rows)")
    return accepted, rejected


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/migrate_v1_history.py <v1_history_dir> [storage_dir]")
        sys.exit(1)

    v1_history_dir = Path(sys.argv[1])
    storage_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else observation_store.DEFAULT_STORAGE_DIR

    cfg = load_config()
    total_accepted = 0
    total_rejected = 0

    print("=" * 70)
    print(f"Migrating v1 history from {v1_history_dir} into {storage_dir}")
    print("=" * 70)

    for bank_id in cfg.banks.keys():
        csv_path = v1_history_dir / f"{bank_id}.csv"
        accepted, rejected = migrate_bank(csv_path, bank_id, cfg, storage_dir)
        total_accepted += accepted
        total_rejected += rejected

    print("=" * 70)
    print(f"TOTAL: {total_accepted} accepted, {total_rejected} rejected")
    print("=" * 70)


if __name__ == "__main__":
    main()
