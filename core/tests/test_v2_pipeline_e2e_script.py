"""
core/tests/test_v2_pipeline_e2e_script.py

Tests for scripts/test_v2_pipeline_e2e.py's exit-code logic. The script
itself needs real bank-site network access to be meaningful (that's the
whole point of it), so these tests mock core.pipeline.collect_all to
verify the script's own control flow -- success/warning/crash exit codes
-- is correct, independent of network conditions.
"""

import importlib
from datetime import datetime, timezone
from unittest.mock import patch

from core.models import Confidence, Observation, SourceType


def _fake_observation(bank_id, currency="EUR", buy=140.0, sell=142.0):
    return Observation(
        bank_id=bank_id,
        currency=currency,
        product_id="TT",
        buy=buy,
        sell=sell,
        collected_at=datetime.now(timezone.utc),
        source_type=SourceType.PDF,
        confidence=Confidence.HIGH,
    )


def _run_script_with(fake_observations):
    with patch("core.pipeline.collect_all", return_value=fake_observations):
        import scripts.test_v2_pipeline_e2e as e2e

        importlib.reload(e2e)
        return e2e.main()


def test_successful_run_returns_zero(capsys):
    exit_code = _run_script_with(
        [_fake_observation("BRAC"), _fake_observation("SONALI", sell=141.5)]
    )
    out = capsys.readouterr().out
    assert exit_code == 0
    assert "✅" in out
    assert "Accepted:   2" in out


def test_zero_collected_returns_warning_exit_code(capsys):
    exit_code = _run_script_with([])
    out = capsys.readouterr().out
    assert exit_code == 1
    assert "zero observations collected" in out


def test_collection_crash_returns_error_exit_code(capsys):
    with patch("core.pipeline.collect_all", side_effect=RuntimeError("network exploded")):
        import scripts.test_v2_pipeline_e2e as e2e

        importlib.reload(e2e)
        exit_code = e2e.main()

    out = capsys.readouterr().out
    assert exit_code == 2
    assert "CRASHED" in out


def test_temp_storage_dir_is_cleaned_up_after_run():
    import shutil
    import tempfile

    created_dirs = []
    real_mkdtemp = tempfile.mkdtemp

    def tracking_mkdtemp(*args, **kwargs):
        d = real_mkdtemp(*args, **kwargs)
        created_dirs.append(d)
        return d

    with patch("tempfile.mkdtemp", side_effect=tracking_mkdtemp):
        _run_script_with([_fake_observation("BRAC")])

    assert len(created_dirs) == 1
    from pathlib import Path

    assert not Path(created_dirs[0]).exists()
