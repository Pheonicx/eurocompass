def calculate_transfer_cost(banks, euro_amount):
    """
    Calculate Germany transfer costs using TT Selling rate.
    """

    results = []

    for bank in banks:

        rate = bank["sell"]

        total_cost = rate * euro_amount

        results.append(
            {
                "bank": bank["bank"],
                "rate": rate,
                "total_cost": total_cost,
            }
        )

    results.sort(key=lambda x: x["total_cost"])

    cheapest = results[0]["total_cost"]

    for result in results:

        result["extra_cost"] = result["total_cost"] - cheapest

    return results


def get_best_bank(results):
    return results[0]