"""
core/validation/rules.py

Business validation and cross-field validation (spec Ch.7, sections 7.5
and 7.7). These are plain functions: given an Observation and the
Currency config it belongs to, decide whether it's plausible. They know
nothing about *how* the observation was collected — that separation is
what lets validation apply identically to every bank, present or future.

Some structural/business rules (buy and sell must be positive, sell must
not be lower than buy) are already enforced by Observation itself
(core/models.py __post_init__) — an Observation violating those can't
even be constructed. What lives here is what the domain model can't
check on its own: rules that depend on configuration (per-currency
plausible ranges) or on more than one field read together.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from core.models import Currency, Observation


def check_business_rules(observation: Observation, currency: Currency) -> Optional[str]:
    """
    Checks the observation's buy/sell/spread against the currency's
    configured plausible range (core/config/banks.json). Returns a
    rejection reason, or None if it passes.
    """
    if not (currency.min_rate <= observation.buy <= currency.max_rate):
        return (
            f"buy {observation.buy} is outside the plausible range "
            f"[{currency.min_rate}, {currency.max_rate}] for {currency.code}"
        )

    if not (currency.min_rate <= observation.sell <= currency.max_rate):
        return (
            f"sell {observation.sell} is outside the plausible range "
            f"[{currency.min_rate}, {currency.max_rate}] for {currency.code}"
        )

    if observation.spread > currency.max_spread:
        return (
            f"spread of {observation.spread:.4f} exceeds the plausible max "
            f"of {currency.max_spread} for {currency.code}"
        )

    return None


def check_rate_date_not_future(observation: Observation) -> Optional[str]:
    """
    Cross-field check (spec 7.7): the date a bank published a rate for
    should never be in the future relative to when we collected it — a
    reliable sign of a date-parsing bug (e.g. misreading day/month order).
    """
    if observation.rate_date is None:
        return None

    try:
        rate_date = date.fromisoformat(observation.rate_date)
    except ValueError:
        return f"rate_date '{observation.rate_date}' is not a valid date"

    if rate_date > observation.collected_at.date():
        return (
            f"rate_date {rate_date} is in the future relative to "
            f"collection time ({observation.collected_at.date()})"
        )

    return None
