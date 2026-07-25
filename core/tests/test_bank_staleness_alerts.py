"""
core/tests/test_bank_staleness_alerts.py

Tests for scripts/check_bank_staleness.py's core decision logic.
Uses plain dicts (matching collector_status.json's real shape) and a
fake notifier that just records what it was called with — no real
Telegram calls, no real GitHub Actions environment needed to verify the
actual alerting decisions are correct.
"""

from datetime import datetime, timedelta, timezone

from scripts.check_bank_staleness import STALE_THRESHOLD_HOURS, check_and_alert


def _iso(hours_ago: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(hours=hours_ago)).isoformat()


class FakeNotifier:
    def __init__(self):
        self.messages = []

    def __call__(self, message):
        self.messages.append(message)


def test_no_alert_when_all_banks_healthy():
    status = {
        "BRAC": {"last_success_at": _iso(0.5), "last_status": "ok"},
        "EBL": {"last_success_at": _iso(1.0), "last_status": "ok"},
    }
    notifier = FakeNotifier()

    new_state = check_and_alert(status, {}, notifier)

    assert notifier.messages == []
    assert new_state == {}


def test_no_alert_for_a_recent_single_failure():
    """A bank that failed once an hour ago (well under the threshold)
    shouldn't trigger an alert — that's normal, expected noise."""
    status = {
        "PRIME": {
            "last_success_at": _iso(1.0),
            "last_status": "failed",
            "last_failure_reason": "timeout",
        },
    }
    notifier = FakeNotifier()

    new_state = check_and_alert(status, {}, notifier)

    assert notifier.messages == []
    assert new_state == {}


def test_alert_sent_when_bank_crosses_threshold():
    status = {
        "CITY": {
            "last_success_at": _iso(STALE_THRESHOLD_HOURS + 1),
            "last_status": "failed",
            "last_failure_reason": "reports list never appeared",
        },
    }
    notifier = FakeNotifier()

    new_state = check_and_alert(status, {}, notifier)

    assert len(notifier.messages) == 1
    assert "CITY" in notifier.messages[0]
    assert "reports list never appeared" in notifier.messages[0]
    assert "CITY" in new_state


def test_never_succeeded_bank_is_treated_as_stale():
    status = {
        "NEWBANK": {"last_success_at": None, "last_status": "failed", "last_failure_reason": "no config"},
    }
    notifier = FakeNotifier()

    new_state = check_and_alert(status, {}, notifier)

    assert len(notifier.messages) == 1
    assert "never successfully collected" in notifier.messages[0]


def test_does_not_alert_twice_for_the_same_ongoing_outage():
    """The core anti-spam guarantee: once alerted for a given outage,
    staying down shouldn't trigger a new alert every time this runs."""
    fixed_last_success = _iso(STALE_THRESHOLD_HOURS + 1)
    status = {
        "CITY": {"last_success_at": fixed_last_success, "last_status": "failed", "last_failure_reason": "x"},
    }
    notifier = FakeNotifier()

    # First check: alerts and records state.
    state_after_first = check_and_alert(status, {}, notifier)
    assert len(notifier.messages) == 1

    # Second check, same ongoing outage (same last_success_at): must NOT alert again.
    state_after_second = check_and_alert(status, state_after_first, notifier)
    assert len(notifier.messages) == 1  # still just the one


def test_recovery_message_sent_and_state_cleared():
    previously_down = {"CITY": {"alerted_for_last_success_at": _iso(10)}}
    status = {
        "CITY": {"last_success_at": _iso(0.1), "last_status": "ok"},
    }
    notifier = FakeNotifier()

    new_state = check_and_alert(status, previously_down, notifier)

    assert len(notifier.messages) == 1
    assert "recovered" in notifier.messages[0]
    assert "CITY" in new_state.get("CITY", {}).get("alerted_for_last_success_at", "CITY") or "CITY" not in new_state
    assert "CITY" not in new_state


def test_new_outage_after_recovery_alerts_again():
    """A bank that recovered and broke again (a genuinely NEW outage,
    different last_success_at) must alert again, not be silenced
    forever by the earlier outage's alert record."""
    old_outage_state = {"CITY": {"alerted_for_last_success_at": _iso(20)}}
    # Recovered in between (not reflected in state, simulating the gap
    # between the old alert and a fresh new failure)
    status = {
        "CITY": {
            "last_success_at": _iso(STALE_THRESHOLD_HOURS + 0.5),  # a new, more recent last-good time
            "last_status": "failed",
            "last_failure_reason": "new problem",
        },
    }
    notifier = FakeNotifier()

    new_state = check_and_alert(status, old_outage_state, notifier)

    assert len(notifier.messages) == 1
    assert "new problem" in notifier.messages[0]


def test_multiple_simultaneous_failures_combine_into_one_message():
    """Two banks down at once should produce ONE combined alert, not
    two separate messages — less noisy for whoever receives it."""
    status = {
        "CITY": {"last_success_at": _iso(10), "last_status": "failed", "last_failure_reason": "a"},
        "SONALI": {"last_success_at": _iso(5), "last_status": "failed", "last_failure_reason": "b"},
        "BRAC": {"last_success_at": _iso(0.2), "last_status": "ok"},
    }
    notifier = FakeNotifier()

    check_and_alert(status, {}, notifier)

    assert len(notifier.messages) == 1
    assert "CITY" in notifier.messages[0]
    assert "SONALI" in notifier.messages[0]
    assert "BRAC" not in notifier.messages[0]
