import pandas as pd
from pathlib import Path


DATA_DIR = Path("data")


def load_history(bank: str):
    """
    Load historical data for a bank.

    Returns a pandas DataFrame sorted by Date and Time.
    """

    csv_file = DATA_DIR / f"{bank}.csv"

    if not csv_file.exists():
        return None

    df = pd.read_csv(csv_file)

    if df.empty:
        return None

    df["Timestamp"] = pd.to_datetime(
        df["Date"] + " " + df["Time"]
    )

    df = df.sort_values("Timestamp")

    return df