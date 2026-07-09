from pathlib import Path
import shutil


HISTORY_DIR = Path("history")
DATA_DIR = Path("data")


def restore_history():
    """
    Restore persistent history into the local data directory
    before new exchange rates are appended.

    Only copies files that don't already exist locally.
    """

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if not HISTORY_DIR.exists():
        return

    for history_file in HISTORY_DIR.glob("*.csv"):

        data_file = DATA_DIR / history_file.name

        if not data_file.exists():

            shutil.copy2(
                history_file,
                data_file,
            )