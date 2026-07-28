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

    if not results:
        # No banks to compare (e.g. every collector failed this cycle).
        # Return an empty list rather than crashing on results[0] below,
        # so callers' existing "no market data" handling can run instead
        # of surfacing a raw IndexError.
        return results

    results.sort(key=lambda x: x["total_cost"])

    cheapest = results[0]["total_cost"]

    for result in results:

        result["extra_cost"] = result["total_cost"] - cheapest

    return results


def get_best_bank(results):
    if not results:
        return None
    return results[0]
