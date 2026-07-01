import csv
from pathlib import Path


DATA_DIR = Path("data")


def get_previous_rate(bank):
    """
    Returns the previous saved rate for a bank.

    Returns:
        dict | None
    """

    csv_file = DATA_DIR / f"{bank}.csv"

    if not csv_file.exists():
        return None

    with open(csv_file, newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))

    # Need at least two records to compare
    if len(rows) < 2:
        return None

    previous = rows[-2]

    return {
        "buy": float(previous["Buy"]),
        "sell": float(previous["Sell"]),
    }


def calculate_change(current, previous):
    """
    Calculate buy/sell difference.

    Returns:
        dict
    """

    if previous is None:
        return {
            "buy_change": None,
            "sell_change": None,
        }

    return {
        "buy_change": current["buy"] - previous["buy"],
        "sell_change": current["sell"] - previous["sell"],
    }


def get_last_rate(bank):
    """
    Returns the most recent saved rate.

    Returns:
        dict | None
    """

    csv_file = DATA_DIR / f"{bank}.csv"

    if not csv_file.exists():
        return None

    with open(csv_file, newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))

    if not rows:
        return None

    latest = rows[-1]

    return {
        "buy": float(latest["Buy"]),
        "sell": float(latest["Sell"]),
    }
def get_rate_change(bank, current):
    """
    Returns the change between the current rate and the previous saved rate.
    """

    previous = get_previous_rate(bank)

    return calculate_change(current, previous)