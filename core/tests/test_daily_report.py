"""
core/tests/test_daily_report.py

Regression test for telegram_bot/daily_report.py.

Covers a real bug: if every bank collector fails in a cycle, `data["banks"]`
can legitimately be an empty list. The original code unconditionally did
`banks[0]` / `banks[-1]`, which raises IndexError and crashes the daily
report entirely -- meaning no message is sent at all, precisely during the
kind of widespread failure when a warning matters most.

No real Telegram calls are made; requests.post is mocked throughout.
"""

import json
from unittest.mock import MagicMock, patch

from telegram_bot import daily_report


def _write_export(tmp_path, banks):
    export = {
        "banks": banks,
        "generated_at": "2026-07-28T09:00:00+06:00",
    }
    export_file = tmp_path / "latest.json"
    export_file.write_text(json.dumps(export))
    return str(export_file)


def test_empty_banks_sends_warning_instead_of_crashing(tmp_path, monkeypatch):
    export_file = _write_export(tmp_path, banks=[])

    monkeypatch.setattr(daily_report, "EXPORT_FILE", export_file)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "fake-chat")

    with patch("telegram_bot.daily_report.requests.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=200)
        daily_report.main()  # must not raise IndexError

    assert mock_post.called
    sent_text = mock_post.call_args.kwargs["json"]["text"]
    assert "No bank data available" in sent_text


def test_normal_case_is_unaffected(tmp_path, monkeypatch):
    export_file = _write_export(
        tmp_path,
        banks=[
            {"bank": "Sonali", "sell": 128.50},
            {"bank": "BRAC", "sell": 129.00},
        ],
    )

    monkeypatch.setattr(daily_report, "EXPORT_FILE", export_file)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "fake-chat")

    with patch("telegram_bot.daily_report.requests.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=200)
        daily_report.main()

    sent_text = mock_post.call_args.kwargs["json"]["text"]
    assert "Sonali" in sent_text
    assert "No bank data available" not in sent_text
