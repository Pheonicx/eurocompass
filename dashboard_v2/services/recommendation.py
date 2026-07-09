from dashboard_v2.services.transfer import calculate_transfer


def get_recommendation(summary, banks, amount=11904):
    """
    Generate a recommendation for Germany transfers.
    """

    best, worst, savings, _ = calculate_transfer(
        banks,
        amount,
    )

    spread = (
        summary["highest_sell"]["value"]
        - summary["lowest_sell"]["value"]
    )

    if spread < 0.25:

        action = "TRANSFER TODAY"

        color = "green"

        reason = (
            "The market is stable and the spread is very low."
        )

    elif spread < 0.60:

        action = "GOOD TIME TO TRANSFER"

        color = "blue"

        reason = (
            "Current rates are competitive across banks."
        )

    else:

        action = "COMPARE CAREFULLY"

        color = "orange"

        reason = (
            "Large differences exist between banks today."
        )

    return {
        "action": action,
        "color": color,
        "bank": best["bank"],
        "rate": best["rate"],
        "savings": savings,
        "reason": reason,
        "amount": amount,
    }