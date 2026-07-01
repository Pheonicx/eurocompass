from bs4 import BeautifulSoup
from utils import http_client


def get_rate():
    url = "https://www.ebl.com.bd/forexrate"

    response = http_client.get(url)

    if response is None:
        return None

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