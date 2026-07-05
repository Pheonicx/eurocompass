import csv
import os
from pathlib import Path
from datetime import datetime


def save_rate(rate):

    Path("data").mkdir(parents=True, exist_ok=True)
    filename = f"data/{rate['bank']}.csv"

    file_exists = os.path.isfile(filename)

    with open(filename, "a", newline="") as file:

        writer = csv.writer(file)

        if not file_exists:
            writer.writerow([
                "Date",
                "Time",
                "Currency",
                "Buy",
                "Sell"
            ])

        now = datetime.now()

        writer.writerow([
            now.strftime("%Y-%m-%d"),
            now.strftime("%H:%M:%S"),
            rate["currency"],
            rate["buy"],
            rate["sell"]
        ])