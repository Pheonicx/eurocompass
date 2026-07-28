"""
core/tests/test_sender_markdown_fallback.py

Regression test for a real bug: telegram_bot/sender.py hardcodes
parse_mode="Markdown", but its only real caller
(scripts/check_bank_staleness.py) sends raw exception text and
validation-rejection reasons -- e.g. `str(e)` from main.py, or
"Rejected: <reason>" -- as the message body. Real exception messages very
commonly contain unbalanced Markdown special characters (a single
underscore in a variable/URL, a stray `[` from a list repr), which
Telegram's legacy Markdown parser rejects with HTTP 400. Since sender.py
called response.raise_for_status() unconditionally, that 400 propagated
as an uncaught exception, crashing the entire staleness-alert run --
during a real outage, exactly when the alert matters most -- and also
meant alert_state.json never got persisted.

No real network calls are made; requests.post is mocked throughout.
"""

from unittest.mock import MagicMock, patch

import pytest
import requests

from telegram_bot import sender


TELEGRAM_MARKDOWN_400 = {
    "ok": False,
    "error_code": 400,
    "description": (
        "Bad Request: can't parse entities: Can't find end of "
        "Italic entity at byte offset 42"
    ),
}


def _fake_response(status_code, json_body):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_body
    if status_code >= 400:
        resp.raise_for_status.side_effect = requests.HTTPError(
            f"{status_code} Client Error", response=resp
        )
    else:
        resp.raise_for_status.return_value = None
    return resp


def test_realistic_exception_text_no_longer_crashes(monkeypatch):
    """
    A realistic str(e) message with an unbalanced underscore (very common
    in Python identifiers, URLs, dict keys) must not crash the whole call --
    it should fall back to plain text and still deliver the alert.
    """
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "fake-chat")

    message = (
        "🚨 EuroCompass — collection problem detected\n\n"
        "• CITY: down for 3.2+ hours\n"
        "  Reason: KeyError: 'buy_rate' not found in extracted_row"
    )

    markdown_fail = _fake_response(400, TELEGRAM_MARKDOWN_400)
    plain_success = _fake_response(200, {"ok": True, "result": {"message_id": 1}})

    with patch(
        "telegram_bot.sender.requests.post",
        side_effect=[markdown_fail, plain_success],
    ) as mock_post:
        result = sender.send_notification(message)  # must not raise

    assert result == {"ok": True, "result": {"message_id": 1}}
    assert mock_post.call_count == 2

    first_call_payload = mock_post.call_args_list[0].kwargs["json"]
    second_call_payload = mock_post.call_args_list[1].kwargs["json"]

    assert first_call_payload["parse_mode"] == "Markdown"
    assert "parse_mode" not in second_call_payload
    # The actual alert text must be preserved exactly on the fallback.
    assert second_call_payload["text"] == message


def test_normal_markdown_message_still_sends_once(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "fake-chat")

    ok_response = _fake_response(200, {"ok": True, "result": {"message_id": 2}})

    with patch(
        "telegram_bot.sender.requests.post", return_value=ok_response
    ) as mock_post:
        result = sender.send_notification("A perfectly normal message.")

    assert result == {"ok": True, "result": {"message_id": 2}}
    assert mock_post.call_count == 1


def test_genuine_non_markdown_400_still_raises(monkeypatch):
    """
    A 400 for an unrelated reason (e.g. bad chat_id) must not be silently
    swallowed by the fallback -- only a Markdown-parse failure should
    trigger the plain-text retry.
    """
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "wrong-chat-id")

    other_400 = _fake_response(
        400,
        {"ok": False, "error_code": 400, "description": "Bad Request: chat not found"},
    )

    with patch(
        "telegram_bot.sender.requests.post", return_value=other_400
    ) as mock_post:
        with pytest.raises(requests.HTTPError):
            sender.send_notification("Doesn't matter what this says.")

    # Should not have retried for an unrelated error.
    assert mock_post.call_count == 1
