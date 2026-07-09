import streamlit as st

from dashboard_v2.services.dashboard_service import (
    build_dashboard_analysis,
)


def intelligence(selected_bank: str, market_spread: float):
    """
    Display the market intelligence panel.
    """

    result = build_dashboard_analysis(
        bank=selected_bank,
        market_spread=market_spread,
    )

    if result is None:
        st.warning("Unable to analyze market.")
        return

    analysis = result["analysis"]
    recommendation = result["recommendation"]

    st.subheader("🧠 Market Intelligence")
    st.caption("Statistical analysis of historical exchange-rate behaviour")

    left, right = st.columns([2, 1], gap="large")

    # ----------------------------------------------------
    # Left
    # ----------------------------------------------------

    with left:

        st.success(f"**{recommendation.title}**")

        st.write(recommendation.summary)

        st.markdown("##### Why?")

        for reason in recommendation.reasons:
            st.markdown(f"✅ {reason}")

    # ----------------------------------------------------
    # Right
    # ----------------------------------------------------

    with right:

        st.metric(
            "Confidence",
            f"{recommendation.confidence}%",
        )

        st.metric(
            "Opportunity Score",
            f"{analysis.opportunity.score}/100",
            analysis.opportunity.classification,
        )

        st.metric(
            "Market Health",
            f"{analysis.health.score}/100",
            analysis.health.level,
        )

    st.divider()