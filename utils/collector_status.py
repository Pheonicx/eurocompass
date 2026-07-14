import json
from datetime import datetime, timezone
from pathlib import Path

from utils.github_sync import upload_file


STATUS_FILE = Path("exports/collector_status.json")


def _load():
    if STATUS_FILE.exists():
        try:
            return json.loads(STATUS_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def record(bank, ok, reason=None, buy=None, sell=None):
    """
    Record the outcome of one bank's collection attempt for this run.
    Keeps the previous successful reading's timestamp even when the
    current run fails, so it's obvious how long a bank has been down,
    not just that it's down right now.
    """
    status = _load()
    now = datetime.now(timezone.utc).isoformat()

    entry = status.get(bank, {})

    entry["last_checked_at"] = now
    entry["last_status"] = "ok" if ok else "failed"

    if ok:
        entry["last_success_at"] = now
        entry["last_buy"] = buy
        entry["last_sell"] = sell
        entry["last_failure_reason"] = None
    else:
        entry["last_failure_reason"] = reason or "Unknown error"
        entry.setdefault("last_success_at", None)

    status[bank] = entry
    STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATUS_FILE.write_text(json.dumps(status, indent=2), encoding="utf-8")


def sync():
    """
    Push the status file to GitHub so failures are visible on the repo
    itself, without needing to be logged into GitHub to read Actions
    console output.
    """
    if not STATUS_FILE.exists():
        return

    content = STATUS_FILE.read_text(encoding="utf-8")

    upload_file(
        "exports/collector_status.json",
        content,
        "Update collector status",
    )
