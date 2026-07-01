"""
Germany Finance Intelligence System (GFIS)

Version: 0.1.0
Author: Hussain Abdullah
Started: 01 July 2026
"""

from config.banks import BANKS
from utils.csv_handler import save_rate

for bank in BANKS:

    rate = bank.get_rate()

    if rate:

        print(rate)

        save_rate(rate)

        print(f"{rate['bank']} saved successfully!")

    else:

        print("Failed.")