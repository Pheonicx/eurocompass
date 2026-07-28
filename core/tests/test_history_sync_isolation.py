"""
core/tests/test_history_sync_isolation.py

Regression test for utils/history_sync.py.

sync_history() loops over every bank's local CSV and calls upload_file()
per file with no error isolation. upload_file() (utils/github_sync.py)
can raise for perfectly ordinary transient reasons -- a GitHub API rate
limit, a momentary 5xx, a network blip. Previously, if that happened on
any bank partway through the loop, the exception propagated straight out
of sync_history(), meaning every bank later in iteration order never got
its history CSV synced that cycle at all -- directly contradicting the
project's own stated principle that one bank's failure must never stop
processing of the others (CLAUDE.md, spec Ch.13.11).

Concretely: this crashes main.py's whole run (sync_history() is called
unguarded), even though every bank's local data/*.csv had already been
written successfully -- turning one GitHub API hiccup into a full
platform failure for that cycle.
"""

from pathlib import Path
from unittest.mock import patch

from utils import history_sync


def test_one_bank_upload_failure_does_not_block_the_others(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    history_dir = tmp_path / "history"
    data_dir.mkdir()

    # Three banks' local CSVs, all written successfully.
    for bank in ("BRAC", "CITY", "EBL"):
        (data_dir / f"{bank}.csv").write_text("Date,Buy,Sell\n2026-07-28,140.0,142.0\n")

    monkeypatch.setattr(history_sync, "DATA_DIR", data_dir)
    monkeypatch.setattr(history_sync, "HISTORY_DIR", history_dir)

    calls = []

    def fake_upload(path, content, message):
        calls.append(path)
        if "CITY" in path:
            raise RuntimeError("GitHub API rate limit exceeded")
        return True

    with patch("utils.history_sync.upload_file", side_effect=fake_upload):
        history_sync.sync_history()  # must not raise

    # All three banks must have been attempted, not just the ones before
    # the failing one in iteration order.
    attempted_banks = {Path(p).stem for p in calls}
    assert attempted_banks == {"BRAC", "CITY", "EBL"}

    # The two banks whose upload succeeded should still have their local
    # history file copy in place.
    assert (history_dir / "BRAC.csv").exists()
    assert (history_dir / "EBL.csv").exists()


def test_normal_case_still_uploads_everything(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    history_dir = tmp_path / "history"
    data_dir.mkdir()

    for bank in ("BRAC", "EBL"):
        (data_dir / f"{bank}.csv").write_text("Date,Buy,Sell\n2026-07-28,140.0,142.0\n")

    monkeypatch.setattr(history_sync, "DATA_DIR", data_dir)
    monkeypatch.setattr(history_sync, "HISTORY_DIR", history_dir)

    with patch("utils.history_sync.upload_file", return_value=True) as mock_upload:
        history_sync.sync_history()

    assert mock_upload.call_count == 2


def test_sync_latest_failure_does_not_crash(tmp_path, monkeypatch):
    export_file = tmp_path / "latest.json"
    export_file.write_text('{"banks": []}')

    monkeypatch.setattr(history_sync, "EXPORT_FILE", export_file)

    with patch(
        "utils.history_sync.upload_file",
        side_effect=RuntimeError("GitHub API rate limit exceeded"),
    ):
        history_sync.sync_latest()  # must not raise
