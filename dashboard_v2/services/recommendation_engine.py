from dataclasses import dataclass

from dashboard_v2.services.analytics_engine import MarketAnalysis


@dataclass(slots=True)
class Recommendation:
    title: str
    confidence: int
    color: str
    summary: str
    reasons: list[str]


def generate_recommendation(
    analysis: MarketAnalysis,
) -> Recommendation:
    """
    Generate a recommendation from the analytics engine.

    This function contains NO statistical calculations.
    It only interprets the analytics output.
    """

    score = analysis.opportunity.score

    reasons = list(analysis.opportunity.reasons)

    # -----------------------------------------------------
    # Recommendation
    # -----------------------------------------------------

    if score >= 80:

        title = "Transfer Today"

        color = "green"

        summary = (
            "Current market conditions appear favorable "
            "for transferring EUR."
        )

    elif score >= 65:

        title = "Good Opportunity"

        color = "blue"

        summary = (
            "Market conditions are generally favorable, "
            "although monitoring upcoming movements may "
            "still be worthwhile."
        )

    elif score >= 50:

        title = "Neutral"

        color = "orange"

        summary = (
            "The market does not currently present a "
            "strong buying or waiting signal."
        )

    else:

        title = "Consider Waiting"

        color = "red"

        summary = (
            "Historical indicators suggest that better "
            "exchange opportunities may emerge."
        )

    # -----------------------------------------------------
    # Confidence
    # -----------------------------------------------------

    confidence = min(
        100,
        max(
            0,
            int(
                (
                    analysis.trend.r_squared * 40
                    + analysis.opportunity.score * 0.60
                )
            ),
        ),
    )

    return Recommendation(
        title=title,
        confidence=confidence,
        color=color,
        summary=summary,
        reasons=reasons,
    )