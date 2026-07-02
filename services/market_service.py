import json
from pathlib import Path

from dashboard.calculator import calculate_transfer_cost, get_best_bank


EXPORT_FILE = Path("exports/latest.json")


def load_market():
    """
    Load the latest exported market data.
    """

    if not EXPORT_FILE.exists():
        return None

    with open(EXPORT_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def get_rates():
    """
    Return all bank rates.
    """

    data = load_market()

    if data is None:
        return None

    return sorted(
        data["banks"],
        key=lambda x: x["sell"],
    )


def recommend_bank(euro_amount):
    """
    Return the cheapest bank for a transfer.
    """

    rates = get_rates()

    if rates is None:
        return None

    comparison = calculate_transfer_cost(
    rates,
    euro_amount,
    )

    return get_best_bank(comparison)