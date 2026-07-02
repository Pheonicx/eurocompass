import json
from pathlib import Path


# Project root directory
BASE_DIR = Path(__file__).resolve().parent.parent

DATA_FILE = BASE_DIR / "exports" / "latest.json"


def load_market_data():
    """
    Load the latest exported market snapshot.
    """

    if not DATA_FILE.exists():
        return None

    with open(DATA_FILE, "r", encoding="utf-8") as file:
        return json.load(file)