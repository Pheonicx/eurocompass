from utils.city_api import get_exchange_rates


def get_rate():
    """
    Collect EUR exchange rate from City Bank.
    """

    try:
        rates = get_exchange_rates()

        if not rates:
            return None

        for rate in rates:
            if rate.get("code") == "EUR":
                return {
                    "bank": "CITY",
                    "currency": "EUR",
                    "buy": float(rate["buying"]),
                    "sell": float(rate["selling"]),
                }

        return None

    except Exception as e:
        print(f"[CITY ERROR] {e}")
        return None