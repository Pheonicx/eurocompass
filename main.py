"""
Germany Finance Intelligence System (GFIS)

Version: 0.1.0
Author: Hussain Abdullah
Started: 01 July 2026
"""

import requests
from bs4 import BeautifulSoup

url = "https://www.ebl.com.bd/forexrate"

response = requests.get(url)

print("Website Status:", response.status_code)

soup = BeautifulSoup(response.text, "html.parser")
# Find all table rows
rows = soup.find_all("tr")

for row in rows:
    cells = row.find_all("td")

    if len(cells) >= 3:
        currency = cells[0].text.strip()

        if currency == "EUR":
            buying = cells[1].text.strip()
            selling = cells[2].text.strip()

            print()
            print("===== EUR FOUND =====")
            print("Buying :", buying)
            print("Selling:", selling)
            break