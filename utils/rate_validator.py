MIN_PLAUSIBLE_RATE = 100.0
MAX_PLAUSIBLE_RATE = 200.0
MAX_PLAUSIBLE_SPREAD = 10.0


def is_plausible_rate(rate, min_rate=MIN_PLAUSIBLE_RATE, max_rate=MAX_PLAUSIBLE_RATE, max_spread=MAX_PLAUSIBLE_SPREAD):
    """
    Sanity-check a collected rate before it's allowed to reach exports/history.

    Guards against a collector's fallback parser silently grabbing the wrong
    numbers from a source page/PDF (e.g. a page number or an unrelated
    figure) and publishing something like "360.00" as an EUR/BDT rate.

    Returns (True, None) if the rate looks plausible, or (False, reason)
    if it should be rejected for this collection cycle.
    """

    buy = rate.get("buy")
    sell = rate.get("sell")

    if buy is None or sell is None:
        return False, "missing buy or sell value"

    if not (min_rate <= buy <= max_rate):
        return False, f"buy {buy} is outside the plausible range [{min_rate}, {max_rate}]"

    if not (min_rate <= sell <= max_rate):
        return False, f"sell {sell} is outside the plausible range [{min_rate}, {max_rate}]"

    if sell < buy:
        return False, f"sell ({sell}) is lower than buy ({buy}), which shouldn't happen"

    if (sell - buy) > max_spread:
        return False, f"spread of {sell - buy:.2f} exceeds the plausible max of {max_spread}"

    return True, None
