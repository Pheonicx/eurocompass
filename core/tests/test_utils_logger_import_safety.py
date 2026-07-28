"""
core/tests/test_utils_logger_import_safety.py

utils/logger.py previously called LOG_DIR.mkdir(exist_ok=True) and
logging.basicConfig(filename=...) at MODULE IMPORT TIME. Any environment
with a read-only or restricted working directory would crash on
`import utils.logger` before any function was called -- the same bug
class already fixed in core/logging_setup.py and utils/exporter.py.
Currently dead code (nothing in the live codebase calls it), but fixed
for the same reason those two were: cheap, safe, and removes a landmine
for whoever revives this file later.
"""

import sys
from pathlib import Path
from unittest.mock import patch


def test_import_does_not_crash_when_mkdir_fails():
    sys.modules.pop("utils.logger", None)

    with patch.object(Path, "mkdir", side_effect=PermissionError("Read-only file system")):
        import utils.logger  # noqa: F401 -- must not raise


def test_log_functions_do_not_crash_when_filesystem_unwritable():
    sys.modules.pop("utils.logger", None)
    import utils.logger as logger_module

    logger_module._configured = False

    with patch.object(Path, "mkdir", side_effect=PermissionError("Read-only file system")):
        logger_module.log_start()  # must not raise
        logger_module.log_success("BRAC", 140.0, 142.0)
        logger_module.log_failed("CITY")


def test_log_functions_still_work_normally(tmp_path, monkeypatch):
    sys.modules.pop("utils.logger", None)
    import utils.logger as logger_module

    logger_module._configured = False
    monkeypatch.setattr(logger_module, "LOG_DIR", tmp_path / "logs")

    logger_module.log_start()
    logger_module.log_success("BRAC", 140.0, 142.0)

    assert (tmp_path / "logs").exists()
