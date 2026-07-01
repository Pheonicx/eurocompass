import requests
from bs4 import BeautifulSoup


def get_rate():
    url = "https://www.ebl.com.bd/forexrate"

    response = requests.get(url)

    soup = BeautifulSoup(response.text, "html.parser")

    rows = soup.find_all("tr")

    for row in rows:
        cells = row.find_all("td")

        if len(cells) >= 3:
            currency = cells[0].text.strip()

            if currency == "EUR":
                buying = cells[1].text.strip()
                selling = cells[2].text.strip()

                return {
                    "bank": "EBL",
                    "currency": "EUR",
                    "buy": float(buying),
                    "sell": float(selling),
                }

    return None