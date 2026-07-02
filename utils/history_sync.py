from pathlib import Path

from utils.github_sync import upload_file


DATA_DIR = Path("data")


def sync_history():
    """
    Upload only modified CSV files to GitHub.
    """

    if not DATA_DIR.exists():
        return

    for csv_file in DATA_DIR.glob("*.csv"):

        content = csv_file.read_text(encoding="utf-8")

        upload_file(
            f"history/{csv_file.name}",
            content,
            f"Update {csv_file.name}",
        )