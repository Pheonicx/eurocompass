from datetime import datetime

import streamlit as st


def header(data, summary):

    best = summary["lowest_sell"]
    worst = summary["highest_sell"]

    savings = (worst["value"] - best["value"]) * 11904
    spread = worst["value"] - best["value"]

    updated = datetime.fromisoformat(data["generated_at"])

    updated_text = updated.strftime("%d %b %Y • %H:%M UTC")

    left, right = st.columns([4, 1], gap="large")

    with left:

        st.title("🧭 EuroCompass")

        st.caption("Germany Finance Intelligence")

        st.markdown("### 💰 Save Money Today")

        st.markdown(
            f"""
## **Save ৳ {savings:,.0f}**

Transfer through **{best["bank"]}** today to get the lowest TT selling rate.
"""
        )

        info1, info2, info3 = st.columns(3)

        info1.metric(
            "🏆 Best Bank",
            best["bank"],
        )

        info2.metric(
            "💱 TT Selling",
            f"{best['value']:.4f}",
        )

        info3.metric(
            "📊 Market Spread",
            f"{spread:.4f}",
        )

        st.caption(
            f"🟢 LIVE • {summary['banks_processed']} Banks • Updated {updated_text}"
        )

    with right:

        st.metric(
            "💸 Estimated Saving",
            f"৳ {savings:,.0f}",
        )

    st.divider()