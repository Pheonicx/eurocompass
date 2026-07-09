from dashboard_v2.history import load_history
from dashboard_v2.services.analytics_engine import analyze_history
from dashboard_v2.services.recommendation_engine import (
    generate_recommendation,
)


def build_dashboard_analysis(
    bank: str,
    market_spread: float,
):
    """
    Build the complete analytics package for a bank.

    Returns
    -------
    {
        "history": DataFrame,
        "analysis": MarketAnalysis,
        "recommendation": Recommendation,
    }
    """

    history = load_history(bank)

    if history is None:
        return None

    analysis = analyze_history(
        history_df=history,
        market_spread=market_spread,
    )

    recommendation = generate_recommendation(
        analysis,
    )

    return {
        "history": history,
        "analysis": analysis,
        "recommendation": recommendation,
    }