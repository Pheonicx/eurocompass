def calculate_transfer(banks, euro_amount):
    """
    Calculate Germany transfer costs.
    """

    results = []

    for bank in banks:

        rate = bank["sell"]

        total = rate * euro_amount

        results.append(
            {
                "bank": bank["bank"],
                "rate": rate,
                "total": total,
            }
        )

    results.sort(key=lambda x: x["total"])

    best = results[0]

    worst = results[-1]

    savings = worst["total"] - best["total"]

    return best, worst, savings, results