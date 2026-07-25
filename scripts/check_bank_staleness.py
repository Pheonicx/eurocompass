"""
scripts/check_bank_staleness.py

Checks exports/collector_status.json for any bank that's been failing
for longer than a threshold, and sends a Telegram alert if so.

Reuses existing infrastructure rather than building new: the same
collector_status.json the platform already maintains every hourly run
(utils/collector_status.py), the same Telegram sender the daily report
already uses (telegram_bot/sender.py), and the same GitHub-sync utility
(utils/github_sync.py) to persist alert state back to the repo, since
GitHub Actions runners are ephemeral and don't remember anything
between runs on their own.

Exists specifically because of a real, confirmed gap this project hit:
City Bank was silently broken in production for over a week before
anyone noticed — purely by chance, during an unrelated investigation.
Nothing before this would have surfaced that on its own.

Avoids spamming: only alerts once per distinct outage (tracked in
exports/alert_state.json), and sends a "recovered" message when a
previously-alerted bank comes back — so silence isn't the only signal
that something's fixed.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

STATUS_FILE = Path("exports/collector_status.json")
ALERT_STATE_FILE = Path("exports/alert_state.json")

# How long a bank can fail before it's worth interrupting someone about.
# Collection runs hourly, so 3 hours means at least 2-3 consecutive
# missed cycles — enough to rule out a single transient blip (a slow
# server, a brief network hiccup — confirmed to happen occasionally,
# e.g. Prime Bank's one-off timeout during earlier testing) without
# waiting so long that a real outage goes unnoticed for most of a day.
STALE_THRESHOLD_HOURS = 3.0


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _hours_since(iso_timestamp: Optional[str]) -> Optional[float]:
    if not iso_timestamp:
        return None
    try:
        then = datetime.fromisoformat(iso_timestamp)
    except ValueError:
        return None
    if then.tzinfo is None:
        then = then.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    return (now - then).total_seconds() / 3600


def check_and_alert(status: dict, alert_state: dict, send_notification) -> dict:
    """
    Pure-ish core logic, separated from file I/O and the real Telegram
    call so it can be tested directly with plain dicts and a fake
    notifier — no GitHub Actions environment or real network needed to
    verify the actual alerting decisions are correct.

    Returns the updated alert_state (caller is responsible for persisting it).
    """
    new_state = dict(alert_state)
    new_alerts = []
    recoveries = []

    for bank, entry in status.items():
        last_success_at = entry.get("last_success_at")
        hours_down = _hours_since(last_success_at)
        # last_success_at is None only if a bank has NEVER once
        # succeeded (e.g. brand new) — treat that as maximally stale too.
        is_stale = last_success_at is None or (hours_down is not None and hours_down > STALE_THRESHOLD_HOURS)

        never_alerted_before = bank not in new_state
        previously_alerted_for = new_state.get(bank, {}).get("alerted_for_last_success_at")

        if is_stale:
            if never_alerted_before or previously_alerted_for != last_success_at:
                new_alerts.append((bank, entry, hours_down))
                new_state[bank] = {"alerted_for_last_success_at": last_success_at}
        else:
            if bank in new_state:
                recoveries.append(bank)
                del new_state[bank]

    if new_alerts:
        lines = ["🚨 EuroCompass — collection problem detected", ""]
        for bank, entry, hours_down in new_alerts:
            reason = entry.get("last_failure_reason") or "Unknown error"
            if hours_down is None:
                lines.append(f"• {bank}: has never successfully collected")
            else:
                lines.append(f"• {bank}: down for {hours_down:.1f}+ hours")
            lines.append(f"  Reason: {reason}")
        lines.append("")
        lines.append("Other banks are unaffected — this is specific to the bank(s) listed above.")
        send_notification("\n".join(lines))

    if recoveries:
        lines = ["✅ EuroCompass — collection recovered", ""]
        for bank in recoveries:
            lines.append(f"• {bank} is collecting successfully again")
        send_notification("\n".join(lines))

    if not new_alerts and not recoveries:
        print("No staleness changes to report.")

    return new_state


def main() -> None:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from telegram_bot.sender import send_notification
    from utils.github_sync import upload_file

    status = _load_json(STATUS_FILE)
    alert_state = _load_json(ALERT_STATE_FILE)

    if not status:
        print("No collector_status.json found or it's empty — nothing to check.")
        return

    updated_state = check_and_alert(status, alert_state, send_notification)

    if updated_state != alert_state:
        upload_file(
            "exports/alert_state.json",
            json.dumps(updated_state, indent=2),
            "Update alert state",
        )


if __name__ == "__main__":
    main()
