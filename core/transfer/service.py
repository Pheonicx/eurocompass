"""
core/transfer/service.py

The single entry point for "given these banks' current rates, what
should this user do?" — combines calculator.py and recommender.py so
every future interface (dashboard, Telegram bot, API) calls one function
instead of each reimplementing the same loop (CLAUDE.md: "One Source of
Truth" — "Business logic should exist only once").
"""

from __future__ import annotations

from core.models import Fee, Observation
from core.transfer.calculator import calculate_transfer_cost
from core.transfer.recommender import Recommendation, generate_recommendation


def recommend_for_amount(
    observations: list[Observation],
    requested_amount: float,
    fees_by_bank: dict[str, tuple[Fee, ...]] | None = None,
    bank_names: dict[str, str] | None = None,
) -> Recommendation:
    """
    observations: one Observation per candidate bank, all for the SAME
        currency and product (e.g. every bank's current EUR/TT rate).
        Mixing currencies/products in one call isn't meaningful — a
        recommendation answers "which bank for THIS currency/product",
        so callers should filter to one currency/product before calling.
    requested_amount: how much of that currency the user wants to buy.
    fees_by_bank: optional known fees per bank_id. A bank absent from
        this dict is treated as "fees not yet verified" (calculator.py
        handles the honesty around that), not as "zero fees."
    """
    if not observations:
        raise ValueError("recommend_for_amount requires at least one observation")

    currencies = {o.currency for o in observations}
    products = {o.product_id for o in observations}
    if len(currencies) > 1 or len(products) > 1:
        raise ValueError(
            f"All observations must share one currency and product; got "
            f"currencies={currencies}, products={products}"
        )

    bank_ids = [o.bank_id for o in observations]
    if len(bank_ids) != len(set(bank_ids)):
        # Without this check, a caller accidentally including the same
        # bank twice would silently corrupt the recommendation: the
        # breakdowns list below would rank both copies, but
        # observations_by_bank (a dict keyed by bank_id) would silently
        # keep only the last one's confidence/staleness data — the two
        # could disagree without any error ever being raised.
        duplicates = {b for b in bank_ids if bank_ids.count(b) > 1}
        raise ValueError(
            f"observations contains the same bank more than once: {duplicates}. "
            f"Pass at most one observation per bank."
        )

    fees_by_bank = fees_by_bank or {}

    breakdowns = [
        calculate_transfer_cost(
            observation=obs,
            requested_amount=requested_amount,
            fees=fees_by_bank.get(obs.bank_id, ()),
        )
        for obs in observations
    ]

    observations_by_bank = {o.bank_id: o for o in observations}

    return generate_recommendation(breakdowns, observations_by_bank, bank_names=bank_names)
