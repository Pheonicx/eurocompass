"""
core/tests/test_exporter_import_safety.py

Regression test for utils/exporter.py.

EXPORT_DIR.mkdir(exist_ok=True) previously ran at MODULE IMPORT TIME
(top-level, not inside a function). Any environment where the working
directory is read-only or restricted (a locked-down CI runner, a
sandboxed test run) would crash the entire module on `import
utils.exporter` -- before any of its functions were even called. This is
the identical bug class already found and fixed in
core/logging_setup.py; this file had the same problem and had not yet
been through that fix.
"""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest


def test_import_does_not_crash_when_mkdir_fails():
    sys.modules.pop("utils.exporter", None)

    with patch.object(Path, "mkdir", side_effect=PermissionError("Read-only file system")):
        import utils.exporter  # noqa: F401 -- must not raise


def test_export_json_still_warns_but_does_not_crash_when_dir_unwritable(tmp_path, monkeypatch):
    sys.modules.pop("utils.exporter", None)
    import utils.exporter as exporter

    monkeypatch.setattr(exporter, "EXPORT_DIR", tmp_path / "exports")

    with patch.object(Path, "mkdir", side_effect=PermissionError("Read-only file system")):
        # mkdir fails, but since tmp_path itself is writable and already
        # exists, the actual file write still succeeds -- the point is
        # that _ensure_export_dir()'s failure doesn't propagate.
        exporter._ensure_export_dir()  # must not raise


def test_export_json_and_csv_still_work_normally(tmp_path, monkeypatch):
    sys.modules.pop("utils.exporter", None)
    import utils.exporter as exporter

    monkeypatch.setattr(exporter, "EXPORT_DIR", tmp_path / "exports")

    results = [{"bank": "BRAC", "currency": "EUR", "buy": 140.0, "sell": 142.0}]
    summary = {"banks_processed": 1}

    exporter.export_json(results, summary)
    exporter.export_csv(results)

    assert (tmp_path / "exports" / "latest.json").exists()
    assert (tmp_path / "exports" / "latest.csv").exists()
