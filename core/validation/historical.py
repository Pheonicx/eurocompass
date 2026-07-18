"""
core/validation/historical.py

Historical validation (spec Ch.7.6): compares a new observation against
recent, already-accepted observations for the same bank/currency/product.
A rate can be individually plausible (pass core.validation.rules) and
still be wrong — e.g. a parser silently grabbing a neighbouring column
that's still "in range" but not the actual rate. A sudden large jump from
recent history is a strong, independent signal something went wrong.
"""

from __future__ import annotations

from typing import Optional, Sequence

from core.models import Observation

# 5% is deliberately generous. EUR/BDT and USD/BDT have historically moved
# well under 1% day-to-day (see core/config/banks.json threshold notes) —
# this threshold exists to catch parsing errors, not to react to normal
# market movement, so it's set loosely enough to avoid rejecting a real,
# unusual-but-genuine market move.
DEFAULT_MAX_CHANGE_PCT = 5.0


def check_against_recent_history(
    observation: Observation,
    recent: Sequence[Observation],
    max_change_pct: float = DEFAULT_MAX_CHANGE_PCT,
) -> Optional[str]:
    """
    `recent` should be prior ACCEPTED observations for the same bank,
    currency, and product — most recent first. Only the single most
    recent one is used.

    With no prior history (e.g. this is the very first observation ever
    collected for this bank/currency), there's nothing to compare
    against, so this always passes — a new bank or currency should never
    be permanently blocked from getting its first data point.
    """
    if not recent:
        return None

    last = recent[0]

    if last.buy <= 0:
        return None  # defensive only; Observation forbids this from ever being stored

    change_pct = abs(observation.buy - last.buy) / last.buy * 100

    if change_pct > max_change_pct:
        return (
            f"buy rate changed {change_pct:.1f}% since the last accepted "
            f"observation ({last.buy} -> {observation.buy}), exceeding the "
            f"{max_change_pct}% plausibility threshold"
        )

    return None
