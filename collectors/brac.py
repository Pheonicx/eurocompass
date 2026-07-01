import re
import requests

URL = "https://www.bracbank.com/en/treasury/foreign-exchange"


def get_rate():
    """
    Collect EUR exchange rate from BRAC Bank.

    Returns:
        dict | None
    """

    try:
        response = requests.get(URL, timeout=20)
        response.raise_for_status()

        html = response.text

        # Find the EUR object inside the embedded Next.js data
        pattern = (
            r'\\"currency\\":\\"EUR\\",'
            r'\\"buy\\":([0-9.]+),'
            r'\\"sell\\":([0-9.]+)'
        )

        match = re.search(pattern, html)

        if not match:
            print("BRAC: EUR data not found.")
            return None

        buy = float(match.group(1))
        sell = float(match.group(2))

        return {
            "bank": "BRAC",
            "currency": "EUR",
            "buy": buy,
            "sell": sell,
        }

    except Exception as e:
        print(f"BRAC ERROR: {e}")
        return None