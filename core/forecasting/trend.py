"""
core/forecasting/trend.py

Deterministic historical statistics — moving averages, trend direction,
volatility, historical extremes (spec Ch.8.5, 8.6, 8.13: "Forecast
Preparation").

Per CLAUDE.md: "Financial calculations must remain deterministic.
Artificial Intelligence may explain calculations. AI must never replace
financial arithmetic." Everything here is plain statistics over
already-validated Observations — no AI/LLM involved anywhere in this
file. This is deliberately the foundation any future forecast sits on,
not a prediction itself: it describes what already happened. A future
AI layer could turn this into more natural phrasing, but the underlying
numbers are — and must remain — pure arithmetic.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from typing import Literal, Optional, Sequence

from core.models import Observation

TrendDirection = Literal["rising", "falling", "stable"]

# A change smaller than this is reported as "stable" rather than a real
# trend — avoids presenting ordinary noise as a meaningful signal.
STABLE_THRESHOLD_PCT = 0.5


@dataclass(frozen=True)
class TrendSummary:
    bank_id: str
    currency: str
    product_id: str
    sample_size: int
    average_sell: float
    lowest_sell: float
    highest_sell: float
    volatility: float  # population standard deviation of sell rates in the sample
    direction: TrendDirection
    change_pct: float  # % change from the first to the last observation in the sample


def summarize_trend(observations: Sequence[Observation]) -> Optional[TrendSummary]:
    """
    observations: prior observations for ONE bank/currency/product, in
    any order — this function sorts by collected_at itself, so callers
    don't need to get the ordering right (a prior version relied on the
    caller passing them oldest-first, which would silently invert the
    reported direction if ever violated; sorting here removes that
    hidden assumption entirely rather than just documenting it).

    Returns None with fewer than 2 observations: a single data point has
    no trend to report, and reporting one anyway would be a false signal
    (same "prefer false warnings over false confidence" reasoning used
    throughout validation).
    """
    if len(observations) < 2:
        return None

    ordered = sorted(observations, key=lambda o: o.collected_at)

    sells = [o.sell for o in ordered]
    average = statistics.mean(sells)
    volatility = statistics.pstdev(sells)

    oldest, newest = ordered[0], ordered[-1]
    change_pct = ((newest.sell - oldest.sell) / oldest.sell) * 100 if oldest.sell else 0.0

    if abs(change_pct) < STABLE_THRESHOLD_PCT:
        direction: TrendDirection = "stable"
    elif change_pct > 0:
        direction = "rising"
    else:
        direction = "falling"

    return TrendSummary(
        bank_id=oldest.bank_id,
        currency=oldest.currency,
        product_id=oldest.product_id,
        sample_size=len(ordered),
        average_sell=round(average, 4),
        lowest_sell=round(min(sells), 4),
        highest_sell=round(max(sells), 4),
        volatility=round(volatility, 4),
        direction=direction,
        change_pct=round(change_pct, 2),
    )


def describe_trend(trend: TrendSummary) -> str:
    """
    A deterministic, template-based plain-English description — NOT an
    AI-generated explanation. Kept as a reliable, dependency-free
    fallback regardless of whether any future AI explanation layer is
    ever added (spec 12.6: "Transparency before Automation" — the
    platform's core explanations must not depend on an external AI
    service being available or affordable).
    """
    if trend.direction == "stable":
        movement = f"stayed roughly flat (within {abs(trend.change_pct):.1f}%)"
    elif trend.direction == "rising":
        movement = f"risen {trend.change_pct:.1f}%"
    else:
        movement = f"fallen {abs(trend.change_pct):.1f}%"

    return (
        f"Over the last {trend.sample_size} observations, {trend.bank_id}'s "
        f"{trend.currency} {trend.product_id} sell rate has {movement}, "
        f"averaging {trend.average_sell:.4f} "
        f"(range {trend.lowest_sell:.4f}\u2013{trend.highest_sell:.4f})."
    )
