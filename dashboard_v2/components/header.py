import streamlit as st


def header(data, summary):

    best = summary["lowest_sell"]
    worst = summary["highest_sell"]

    savings = (worst["value"] - best["value"]) * 11904
    spread = worst["value"] - best["value"]

    left, right = st.columns([3, 1], gap="large")

    with left:

        st.title("🧭 EuroCompass")

        st.caption("Germany Finance Intelligence")

        st.markdown("")

        st.caption("TODAY'S DECISION")

        st.markdown(
            f"""
# Transfer Today

### Save **৳ {savings:,.0f}**

Choose **{best["bank"]}** instead of the most expensive bank.
"""
        )

        st.caption(
            f"🟢 LIVE • {summary['banks_processed']} Banks • Updated {data['generated_at'][:16]}"
        )

    with right:

        st.metric(
            "🏆 Best Bank",
            best["bank"],
        )

        st.metric(
            "Lowest TT Selling Rate",
            f"৳ {best['value']:.4f}",
            delta=f"Spread ৳ {spread:.4f}",
        )

    st.divider()