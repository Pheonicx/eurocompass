"""
core/tests/test_run_v2_collection_script.py

Tests for scripts/run_v2_collection.py's control flow. collect_all is
mocked (no real network calls). Storage/export paths are redirected to
a temp directory by monkeypatching the DEFAULT_STORAGE_DIR/
DEFAULT_EXPORT_PATH module-level constants that the script reads
explicitly at call time (see the script's own docstring for why it's
built that way rather than relying on run_collection_cycle()'s and
build_export()'s own default argument values, which are bound once at
import time and wouldn't respond to monkeypatching here).
"""

import importlib
import json
from datetime import datetime, timezone
from unittest.mock import patch

from core.models import Confidence, Observation, SourceType


def _fake_observation(bank_id, currency="EUR", buy=140.0, sell=142.0):
    return Observation(
        bank_id=bank_id, currency=currency, product_id="TT",
        buy=buy, sell=sell, collected_at=datetime.now(timezone.utc),
        source_type=SourceType.PDF, confidence=Confidence.HIGH,
    )


def _run_script_with(fake_observations, tmp_path, monkeypatch):
    storage_dir = tmp_path / "v2_history"
    export_path = tmp_path / "v2_exports" / "latest.json"

    import scripts.run_v2_collection as script
    importlib.reload(script)
    monkeypatch.setattr(script.observation_store_module, "DEFAULT_STORAGE_DIR", storage_dir)
    monkeypatch.setattr(script.export_module, "DEFAULT_EXPORT_PATH", export_path)

    with patch("core.pipeline.collect_all", return_value=fake_observations):
        exit_code = script.main()

    return exit_code, storage_dir, export_path


def test_successful_cycle_writes_history_and_export(tmp_path, monkeypatch):
    exit_code, storage_dir, export_path = _run_script_with(
        [_fake_observation("BRAC"), _fake_observation("SONALI", sell=141.5)],
        tmp_path, monkeypatch,
    )

    assert exit_code == 0
    assert (storage_dir / "BRAC.jsonl").exists()
    assert (storage_dir / "SONALI.jsonl").exists()
    assert export_path.exists()

    data = json.loads(export_path.read_text())
    assert "EUR" in data["rates_by_currency"]


def test_zero_collection_returns_error_without_touching_storage(tmp_path, monkeypatch):
    exit_code, storage_dir, export_path = _run_script_with([], tmp_path, monkeypatch)

    assert exit_code == 1
    # Nothing collected -> no export should be written (existing data,
    # if any, must be left untouched rather than overwritten with an
    # empty result).
    assert not export_path.exists()


def test_partial_bank_failure_still_exits_zero(tmp_path, monkeypatch):
    """
    Only some banks producing observations (others having failed
    upstream inside collect_all, which isolates per-bank failures on
    its own) is a normal outcome, not a workflow failure.
    """
    exit_code, storage_dir, export_path = _run_script_with(
        [_fake_observation("BRAC")],  # as if 4 of 5 banks failed to collect anything
        tmp_path, monkeypatch,
    )

    assert exit_code == 0
    assert export_path.exists()
