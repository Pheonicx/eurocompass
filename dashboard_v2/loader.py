import sys
import json
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from collectors import brac
from collectors import city
from collectors import ebl
from collectors import prime
from collectors import sonali


DATA_FILE = Path("exports/latest.json")


def collect_live_data():
    """
    Collect live exchange rates from all supported banks.
    """

    banks = []

    for collector in [ebl, city, brac, prime, sonali]:

        try:

            result = collector.get_rate()

            if result:
                banks.append(result)

        except Exception as error:

            st.error(
                f"Collector '{collector.__name__}' failed:\n{type(error).__name__}: {error}"
            )

    return banks


def load_market_data():
    """
    Load latest market snapshot.
    If it doesn't exist, collect live data.
    """

    if DATA_FILE.exists():

        with open(DATA_FILE, "r", encoding="utf-8") as file:
            return json.load(file)

    banks = collect_live_data()

    if not banks:
     return None

    summary = {
    "banks_processed": len(banks),

    "lowest_buy": {
        "bank": min(banks, key=lambda x: x["buy"])["bank"],
        "value": min(banks, key=lambda x: x["buy"])["buy"],
    },

    "highest_buy": {
        "bank": max(banks, key=lambda x: x["buy"])["bank"],
        "value": max(banks, key=lambda x: x["buy"])["buy"],
    },

    "lowest_sell": {
        "bank": min(banks, key=lambda x: x["sell"])["bank"],
        "value": min(banks, key=lambda x: x["sell"])["sell"],
    },

    "highest_sell": {
        "bank": max(banks, key=lambda x: x["sell"])["bank"],
        "value": max(banks, key=lambda x: x["sell"])["sell"],
    },

    "average_buy": sum(b["buy"] for b in banks) / len(banks),
    "average_sell": sum(b["sell"] for b in banks) / len(banks),
}

    return {
     "banks": banks,
     "generated_at": "Live",
     "summary": summary,
    }