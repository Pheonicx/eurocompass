"""
core/tests/test_publish_result_gist.py

Tests for scripts/publish_result_gist.py's diagnostic-file collection
and fallback logic — mocking the actual network call, since this script
talks to a real external API.
"""

import base64
import os
from unittest import mock

from scripts.publish_result_gist import (
    MAX_SCREENSHOT_BASE64_CHARS,
    _collect_city_diagnostic_files,
    _publish_gist,
    main,
)


def test_oversized_screenshot_is_skipped_not_included(tmp_path, monkeypatch):
    """
    Regression test for a real gap: the screenshot previously had no
    size cap at all (unlike the other diagnostic files), risking the
    whole gist payload failing if it were unusually large. Must now be
    skipped gracefully instead.
    """
    diagnostic_dir = tmp_path / "city_diagnostics"
    diagnostic_dir.mkdir()

    # Write a fake "screenshot" whose base64 form will exceed the cap.
    raw_size_needed = int(MAX_SCREENSHOT_BASE64_CHARS * 0.8)  # base64 inflates ~4/3
    (diagnostic_dir / "screenshot.png").write_bytes(os.urandom(raw_size_needed))

    monkeypatch.setattr("scripts.publish_result_gist.CITY_DIAGNOSTIC_DIR", str(diagnostic_dir))

    files = _collect_city_diagnostic_files()

    assert "city_screenshot_base64.txt" not in files


def test_normal_sized_screenshot_is_included(tmp_path, monkeypatch):
    diagnostic_dir = tmp_path / "city_diagnostics"
    diagnostic_dir.mkdir()
    (diagnostic_dir / "screenshot.png").write_bytes(os.urandom(1000))

    monkeypatch.setattr("scripts.publish_result_gist.CITY_DIAGNOSTIC_DIR", str(diagnostic_dir))

    files = _collect_city_diagnostic_files()

    assert "city_screenshot_base64.txt" in files
    # Confirm it round-trips correctly
    decoded = base64.b64decode(files["city_screenshot_base64.txt"]["content"])
    assert len(decoded) == 1000


def test_no_diagnostic_files_when_city_did_not_fail(tmp_path, monkeypatch):
    diagnostic_dir = tmp_path / "city_diagnostics"  # deliberately not created
    monkeypatch.setattr("scripts.publish_result_gist.CITY_DIAGNOSTIC_DIR", str(diagnostic_dir))

    files = _collect_city_diagnostic_files()

    assert files == {}


def test_falls_back_to_result_only_when_full_payload_fails(tmp_path, monkeypatch):
    """
    Regression test for a real design gap: everything was published in
    ONE api call, so a failure caused by a diagnostic file (e.g. an
    oversized payload) would previously have lost even the basic
    result.txt summary along with it. Must retry with just that.
    """
    log_file = tmp_path / "test_output.log"
    log_file.write_text("some real test output")

    call_log = []

    def fake_publish(files, token):
        call_log.append(set(files.keys()))
        # Simulate the full payload (with an extra 'extra.txt' file) failing,
        # but a result-only payload succeeding.
        return "extra.txt" not in files

    monkeypatch.setattr("scripts.publish_result_gist._publish_gist", fake_publish)
    monkeypatch.setattr(
        "scripts.publish_result_gist._collect_city_diagnostic_files",
        lambda: {"extra.txt": {"content": "diagnostic stuff"}},
    )
    monkeypatch.setenv("GIST_TOKEN", "fake-token")
    monkeypatch.setattr("sys.argv", ["publish_result_gist.py", str(log_file)])

    main()

    assert len(call_log) == 2  # first attempt (with extra.txt) then fallback
    assert "extra.txt" in call_log[0]
    assert call_log[1] == {"result.txt"}  # fallback dropped the extra file


def test_missing_gist_token_skips_gracefully(tmp_path, monkeypatch, capsys):
    log_file = tmp_path / "test_output.log"
    log_file.write_text("output")

    monkeypatch.delenv("GIST_TOKEN", raising=False)
    monkeypatch.setattr("sys.argv", ["publish_result_gist.py", str(log_file)])

    main()  # must not raise

    assert "skipping gist publish" in capsys.readouterr().out
