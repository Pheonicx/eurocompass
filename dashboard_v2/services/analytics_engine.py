from __future__ import annotations

from dataclasses import dataclass
from typing import List

import numpy as np
import pandas as pd
from scipy.stats import linregress


# ==========================================================
# Configuration
# ==========================================================

DEFAULT_WINDOW = 30

LOW_VOLATILITY = 0.15
MEDIUM_VOLATILITY = 0.35

LOW_PERCENTILE = 30
HIGH_PERCENTILE = 70


# ==========================================================
# Data Models
# ==========================================================

@dataclass(slots=True)
class MarketStatistics:
    current: float
    previous: float
    minimum: float
    maximum: float
    mean: float
    median: float
    std_dev: float
    value_range: float
    change: float
    change_percent: float
    observations: int

@dataclass(slots=True)
class TrendAnalysis:
    direction: str
    slope: float
    intercept: float
    r_value: float
    r_squared: float
    strength: str

@dataclass(slots=True)
class VolatilityAnalysis:
    std_dev: float
    average_change: float
    level: str

@dataclass(slots=True)
class PositionAnalysis:
    percentile: float
    z_score: float
    distance_from_mean: float

@dataclass(slots=True)
class OpportunityAnalysis:
    score: int
    classification: str
    reasons: List[str]

@dataclass(slots=True)
class MarketHealthAnalysis:
    score: int
    level: str
    reasons: List[str]

@dataclass(slots=True)
class MarketAnalysis:
    statistics: MarketStatistics
    trend: TrendAnalysis
    volatility: VolatilityAnalysis
    position: PositionAnalysis
    opportunity: OpportunityAnalysis
    health: MarketHealthAnalysis


# ==========================================================
# Helpers
# ==========================================================

def _prepare_dataframe(
    history_df: pd.DataFrame,
    window: int = DEFAULT_WINDOW,
) -> pd.DataFrame:
    """
    Prepare and validate historical data.
    """

    if history_df.empty:
        raise ValueError("History dataframe is empty.")

    df = history_df.copy()

    df = df.sort_values("Timestamp")

    if len(df) > window:
        df = df.tail(window)

    df["Sell"] = pd.to_numeric(df["Sell"])

    return df.reset_index(drop=True)

# ==========================================================
# Statistics
# ==========================================================

def _calculate_statistics(df: pd.DataFrame) -> MarketStatistics:
    """
    Calculate descriptive statistics for selling rates.
    """

    sell = df["Sell"].to_numpy(dtype=float)

    current = float(sell[-1])

    previous = (
        float(sell[-2])
        if len(sell) >= 2
        else current
    )

    change = current - previous

    change_percent = (
        (change / previous) * 100
        if previous != 0
        else 0
    )

    return MarketStatistics(
        current=current,
        previous=previous,
        minimum=float(np.min(sell)),
        maximum=float(np.max(sell)),
        mean=float(np.mean(sell)),
        median=float(np.median(sell)),
        std_dev=float(np.std(sell, ddof=1))
        if len(sell) > 1
        else 0.0,
        value_range=float(np.max(sell) - np.min(sell)),
        change=change,
        change_percent=change_percent,
        observations=len(sell),
    )


# ==========================================================
# Trend
# ==========================================================

def _calculate_trend(df: pd.DataFrame) -> TrendAnalysis:
    """
    Linear regression trend using historical selling rates.
    """

    y = df["Sell"].to_numpy(dtype=float)
    x = np.arange(len(y))

    result = linregress(x, y)

    slope = float(result.slope)

    if abs(slope) < 0.005:
        direction = "Stable"
    elif slope > 0:
        direction = "Rising"
    else:
        direction = "Falling"

    strength_value = abs(result.rvalue)

    if strength_value >= 0.80:
        strength = "Strong"
    elif strength_value >= 0.50:
        strength = "Moderate"
    else:
        strength = "Weak"

    return TrendAnalysis(
        direction=direction,
        slope=slope,
        intercept=float(result.intercept),
        r_value=float(result.rvalue),
        r_squared=float(result.rvalue ** 2),
        strength=strength,
    )


# ==========================================================
# Volatility
# ==========================================================

def _calculate_volatility(df: pd.DataFrame) -> VolatilityAnalysis:
    """
    Calculate market volatility from consecutive changes.
    """

    sell = df["Sell"].to_numpy(dtype=float)

    changes = np.diff(sell)

    if len(changes) == 0:
        return VolatilityAnalysis(
            std_dev=0.0,
            average_change=0.0,
            level="Stable",
        )

    std = float(np.std(changes, ddof=1)) if len(changes) > 1 else 0.0

    avg = float(np.mean(np.abs(changes)))

    if std < LOW_VOLATILITY:
        level = "Low"

    elif std < MEDIUM_VOLATILITY:
        level = "Moderate"

    else:
        level = "High"

    return VolatilityAnalysis(
        std_dev=std,
        average_change=avg,
        level=level,
    )

# ==========================================================
# Position Analysis
# ==========================================================

def _calculate_position(
    df: pd.DataFrame,
    statistics: MarketStatistics,
) -> PositionAnalysis:
    """
    Determine where the current rate sits
    relative to historical observations.
    """

    sell = df["Sell"].to_numpy(dtype=float)

    current = statistics.current

    percentile = (
        np.sum(sell <= current)
        / len(sell)
        * 100
    )

    if statistics.std_dev == 0:
        z_score = 0.0
    else:
        z_score = (
            current - statistics.mean
        ) / statistics.std_dev

    distance = current - statistics.mean

    return PositionAnalysis(
        percentile=float(percentile),
        z_score=float(z_score),
        distance_from_mean=float(distance),
    )


# ==========================================================
# Opportunity Score
# ==========================================================

def _calculate_opportunity(
    statistics: MarketStatistics,
    trend: TrendAnalysis,
    volatility: VolatilityAnalysis,
    position: PositionAnalysis,
    market_spread: float,
) -> OpportunityAnalysis:
    """
    Calculate an explainable opportunity score using
    continuous weighted scoring.

    Weights
    -------
    Historical Position : 40
    Trend               : 25
    Volatility          : 20
    Market Spread       : 15

    Total               : 100
    """

    reasons = []

    # ======================================================
    # Historical Position (0–40)
    # Lower percentile = cheaper relative to history
    # ======================================================

    position_score = (100 - position.percentile) * 0.40

    if position.percentile <= 25:
        reasons.append(
            "Current rate is in the lower part of its historical range."
        )
    elif position.percentile >= 75:
        reasons.append(
            "Current rate is relatively high compared with history."
        )

    # ======================================================
    # Trend (0–25)
    # Falling trend is good for buyers.
    # Stable is neutral.
    # Rising is less attractive.
    # ======================================================

    slope = trend.slope

    # Normalize slope to [-1,1]
    normalized_slope = np.tanh(slope * 100)

    trend_score = ((1 - normalized_slope) / 2) * 25

    if trend.direction == "Falling":
        reasons.append(
            "Historical trend is moving downward."
        )

    elif trend.direction == "Stable":
        reasons.append(
            "Historical trend is stable."
        )

    else:
        reasons.append(
            "Historical trend is rising."
        )

    # ======================================================
    # Volatility (0–20)
    # Lower volatility = higher confidence
    # ======================================================

    volatility_score = max(
        0,
        20 - volatility.std_dev * 40,
    )

    if volatility.level == "Low":
        reasons.append(
            "Market volatility is low."
        )

    elif volatility.level == "High":
        reasons.append(
            "Recent market movement has been volatile."
        )

    # ======================================================
    # Market Spread (0–15)
    # Larger spread means choosing the right bank
    # produces greater savings.
    # ======================================================

    spread_score = min(
        market_spread / 2,
        1,
    ) * 15

    if market_spread >= 1:
        reasons.append(
            "Large spread between banks increases savings potential."
        )

    # ======================================================

    total_score = (
        position_score
        + trend_score
        + volatility_score
        + spread_score
    )

    total_score = max(
        0,
        min(
            100,
            round(total_score),
        ),
    )

    if total_score >= 80:
        classification = "Excellent"

    elif total_score >= 65:
        classification = "Good"

    elif total_score >= 50:
        classification = "Fair"

    else:
        classification = "Poor"

    return OpportunityAnalysis(
        score=total_score,
        classification=classification,
        reasons=reasons,
    )

def _calculate_market_health(
    trend: TrendAnalysis,
    volatility: VolatilityAnalysis,
    market_spread: float,
) -> MarketHealthAnalysis:
    """
    Overall market quality.

    Higher score means a healthier,
    more predictable market.
    """

    score = 0

    reasons = []

    # -----------------------------
    # Trend Stability
    # -----------------------------

    if trend.direction == "Stable":
        score += 35
        reasons.append(
            "Stable exchange-rate trend."
        )

    elif trend.strength == "Weak":
        score += 25
        reasons.append(
            "Only weak directional movement."
        )

    else:
        score += 15

    # -----------------------------
    # Volatility
    # -----------------------------

    if volatility.level == "Low":
        score += 40
        reasons.append(
            "Low market volatility."
        )

    elif volatility.level == "Moderate":
        score += 25

    else:
        score += 10

    # -----------------------------
    # Competition
    # -----------------------------

    if market_spread >= 1:
        score += 25
        reasons.append(
            "Strong competition between banks."
        )

    elif market_spread >= 0.50:
        score += 15

    else:
        score += 8

    score = min(score, 100)

    if score >= 85:
        level = "Excellent"

    elif score >= 70:
        level = "Healthy"

    elif score >= 50:
        level = "Moderate"

    else:
        level = "Weak"

    return MarketHealthAnalysis(
        score=score,
        level=level,
        reasons=reasons,
    )

# ==========================================================
# Public API
# ==========================================================

def analyze_history(
    history_df: pd.DataFrame,
    market_spread: float,
    window: int = DEFAULT_WINDOW,
) -> MarketAnalysis:
    """
    Perform complete market analysis.

    Parameters
    ----------
    history_df
        Historical exchange-rate dataframe.

    market_spread
        Difference between the highest and
        lowest selling rates today.

    window
        Rolling analysis window.
    """

    df = _prepare_dataframe(
        history_df,
        window,
    )

    statistics = _calculate_statistics(df)

    trend = _calculate_trend(df)

    volatility = _calculate_volatility(df)

    position = _calculate_position(
        df,
        statistics,
    )

    opportunity = _calculate_opportunity(
        statistics,
        trend,
        volatility,
        position,
        market_spread,
    )

    health = _calculate_market_health(
        trend,
        volatility,
        market_spread,
    )

    return MarketAnalysis(
    statistics=statistics,
    trend=trend,
    volatility=volatility,
    position=position,
    opportunity=opportunity,
    health=health,
    )