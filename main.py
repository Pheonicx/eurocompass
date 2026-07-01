"""
Germany Finance Intelligence System (GFIS)

Version: 0.1.0
Author: Hussain Abdullah
Started: 01 July 2026
"""

from collectors import ebl
from utils.csv_handler import save_rate

rate = ebl.get_rate()

if rate:

    print(rate)

    save_rate(rate)

    print()

    print("Rate saved successfully!")

else:

    print("Failed to collect EBL rate.")