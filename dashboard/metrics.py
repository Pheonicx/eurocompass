from statistics import mean


def calculate_metrics(banks):
    """
    Calculate market statistics from the latest bank data.
    """

    lowest_buy = min(banks, key=lambda x: x["buy"])
    highest_buy = max(banks, key=lambda x: x["buy"])

    lowest_sell = min(banks, key=lambda x: x["sell"])
    highest_sell = max(banks, key=lambda x: x["sell"])

    average_buy = mean(bank["buy"] for bank in banks)
    average_sell = mean(bank["sell"] for bank in banks)

    return {
        "lowest_buy": lowest_buy,
        "highest_buy": highest_buy,
        "lowest_sell": lowest_sell,
        "highest_sell": highest_sell,
        "average_buy": average_buy,
        "average_sell": average_sell,
    }