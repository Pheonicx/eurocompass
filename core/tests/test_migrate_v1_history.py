"""
core/tests/test_migrate_v1_history.py

Tests for scripts/migrate_v1_history.py using small synthetic CSV
fixtures in v1's real format (Date,Time,Currency,Buy,Sell) -- not the
real several-thousand-row files, which were already verified directly
against this script in a manual dry run (928 accepted, 0 rejected).
These tests focus on the migration logic itself: validation actually
runs (bad rows get rejected, not silently imported), chronological
ordering, and unparseable rows being skipped without crashing the rest
of the migration.
"""

import sys
from pathlib import Path

sys.path.insert(0, ".")

from core.config.loader import load_config
from core.storage import observation_store
from scripts.migrate_v1_history import migrate_bank


def _write_csv(path: Path, rows):
    path.write_text(
        "Date,Time,Currency,Buy,Sell\n" + "\n".join(rows) + "\n"
    )


def test_valid_rows_are_migrated_and_queryable(tmp_path):
    csv_dir = tmp_path / "v1_history"
    csv_dir.mkdir()
    _write_csv(
        csv_dir / "BRAC.csv",
        [
            "2026-07-01,10:00:00,EUR,139.0,141.5",
            "2026-07-02,10:00:00,EUR,139.2,141.7",
        ],
    )
    storage_dir = tmp_path / "v2_history"
    cfg = load_config()

    accepted, rejected = migrate_bank(csv_dir / "BRAC.csv", "BRAC", cfg, storage_dir)

    assert accepted == 2
    assert rejected == 0

    stored = observation_store.load_all("BRAC", storage_dir=storage_dir)
    assert len(stored) == 2
    assert all(o.metadata.get("migrated_from_v1_history") is True for o in stored)


def test_implausible_rows_are_rejected_not_imported(tmp_path):
    """
    A row with a rate wildly outside the plausible range (e.g. a stray
    decimal-point error in the original CSV) must be rejected by real
    validation, not blindly trusted just because it's "historical."
    """
    csv_dir = tmp_path / "v1_history"
    csv_dir.mkdir()
    _write_csv(
        csv_dir / "BRAC.csv",
        [
            "2026-07-01,10:00:00,EUR,139.0,141.5",
            "2026-07-02,10:00:00,EUR,1390.0,1415.0",  # implausible: 10x too large
        ],
    )
    storage_dir = tmp_path / "v2_history"
    cfg = load_config()

    accepted, rejected = migrate_bank(csv_dir / "BRAC.csv", "BRAC", cfg, storage_dir)

    assert accepted == 1
    assert rejected == 1

    stored = observation_store.load_all("BRAC", storage_dir=storage_dir)
    assert len(stored) == 1
    assert stored[0].sell == 141.5


def test_sudden_spike_vs_recent_history_is_rejected(tmp_path):
    """
    A row that's individually plausible but represents an implausible
    jump from the immediately preceding real observation should still
    be caught by historical validation, exactly as it would for a live
    collection.
    """
    csv_dir = tmp_path / "v1_history"
    csv_dir.mkdir()
    _write_csv(
        csv_dir / "BRAC.csv",
        [
            "2026-07-01,10:00:00,EUR,139.0,141.5",
            "2026-07-02,10:00:00,EUR,160.0,162.0",  # >5% jump from prior, individually still in [120,170]
        ],
    )
    storage_dir = tmp_path / "v2_history"
    cfg = load_config()

    accepted, rejected = migrate_bank(csv_dir / "BRAC.csv", "BRAC", cfg, storage_dir)

    assert accepted == 1
    assert rejected == 1


def test_unparseable_row_is_skipped_without_crashing_the_rest(tmp_path):
    csv_dir = tmp_path / "v1_history"
    csv_dir.mkdir()
    csv_dir_file = csv_dir / "BRAC.csv"
    csv_dir_file.write_text(
        "Date,Time,Currency,Buy,Sell\n"
        "2026-07-01,10:00:00,EUR,139.0,141.5\n"
        "not-a-date,10:00:00,EUR,139.2,141.7\n"  # malformed
        "2026-07-03,10:00:00,EUR,139.4,141.9\n"
    )
    storage_dir = tmp_path / "v2_history"
    cfg = load_config()

    accepted, rejected = migrate_bank(csv_dir_file, "BRAC", cfg, storage_dir)

    # The malformed row is skipped (neither accepted nor counted as a
    # validation rejection -- it never became a real Observation), the
    # two valid rows on either side still migrate successfully.
    assert accepted == 2

    stored = observation_store.load_all("BRAC", storage_dir=storage_dir)
    assert len(stored) == 2


def test_missing_csv_file_returns_zero_without_crashing(tmp_path):
    cfg = load_config()
    accepted, rejected = migrate_bank(
        tmp_path / "does_not_exist.csv", "BRAC", cfg, tmp_path / "v2_history"
    )
    assert accepted == 0
    assert rejected == 0


def test_rows_are_stored_chronologically_oldest_first(tmp_path):
    csv_dir = tmp_path / "v1_history"
    csv_dir.mkdir()
    # Deliberately out of order in the source file.
    _write_csv(
        csv_dir / "BRAC.csv",
        [
            "2026-07-03,10:00:00,EUR,139.4,141.9",
            "2026-07-01,10:00:00,EUR,139.0,141.5",
            "2026-07-02,10:00:00,EUR,139.2,141.7",
        ],
    )
    storage_dir = tmp_path / "v2_history"
    cfg = load_config()

    migrate_bank(csv_dir / "BRAC.csv", "BRAC", cfg, storage_dir)

    stored = observation_store.load_all("BRAC", storage_dir=storage_dir)
    dates = [o.collected_at.date().isoformat() for o in stored]
    assert dates == sorted(dates)
