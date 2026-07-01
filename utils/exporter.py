import csv
import json
from datetime import datetime
from pathlib import Path


EXPORT_DIR = Path("exports")
EXPORT_DIR.mkdir(exist_ok=True)


def export_json(results):
    """
    Export the latest market snapshot to JSON.
    """

    output = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "currency": "EUR",
        "banks": results,
    }

    output_file = EXPORT_DIR / "latest.json"

    with open(output_file, "w", encoding="utf-8") as file:
        json.dump(output, file, indent=4)


def export_csv(results):
    """
    Export the latest market snapshot to CSV.
    """

    output_file = EXPORT_DIR / "latest.csv"

    with open(output_file, "w", newline="", encoding="utf-8") as file:

        writer = csv.writer(file)

        writer.writerow(
            [
                "Bank",
                "Currency",
                "Buy",
                "Sell",
            ]
        )

        for rate in results:

            writer.writerow(
                [
                    rate["bank"],
                    rate["currency"],
                    rate["buy"],
                    rate["sell"],
                ]
            )