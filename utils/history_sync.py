from pathlib import Path
import shutil

from utils.github_sync import upload_file


DATA_DIR = Path("data")
HISTORY_DIR = Path("history")
EXPORT_FILE = Path("exports/latest.json")


def sync_history():
    """
    Synchronize history locally and upload it to GitHub.
    """

    if not DATA_DIR.exists():
        return

    HISTORY_DIR.mkdir(parents=True, exist_ok=True)

    for csv_file in DATA_DIR.glob("*.csv"):

        # Read latest history from data/
        content = csv_file.read_text(encoding="utf-8")

        # Keep local history folder in sync
        history_file = HISTORY_DIR / csv_file.name
        shutil.copy2(csv_file, history_file)

        # Upload to GitHub. One bank's upload failure (rate limit,
        # transient network/5xx error) must not stop the remaining
        # banks in this cycle from being synced too.
        try:
            upload_file(
                f"history/{csv_file.name}",
                content,
                f"Update {csv_file.name}",
            )
        except Exception as e:
            print(f"WARNING: failed to sync {csv_file.name} to GitHub: {e}")


def sync_latest():
    """
    Upload latest.json to GitHub.
    """

    if not EXPORT_FILE.exists():
        return

    content = EXPORT_FILE.read_text(encoding="utf-8")

    try:
        upload_file(
            "exports/latest.json",
            content,
            "Update latest.json",
        )
    except Exception as e:
        # A transient failure here must not prevent main.py from going
        # on to sync_history() -- the per-bank CSVs are independently
        # valuable even if this particular upload didn't go through.
        print(f"WARNING: failed to sync latest.json to GitHub: {e}")