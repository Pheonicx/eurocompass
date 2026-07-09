import streamlit as st


def analytics(summary):

    spread = (
        summary["highest_sell"]["value"]
        - summary["lowest_sell"]["value"]
    )

    avg_buy = summary["average_buy"]
    avg_sell = summary["average_sell"]

    if spread < 0.30:
        status = "🟢 Stable"

    elif spread < 0.70:
        status = "🟡 Moderate"

    else:
        status = "🔴 Volatile"

    st.markdown("## 📊 Market Analytics")

    c1, c2, c3 = st.columns(3)

    with c1:

        st.metric(
            "Average Buy",
            f"{avg_buy:.4f}"
        )

    with c2:

        st.metric(
            "Average Sell",
            f"{avg_sell:.4f}"
        )

    with c3:

        st.metric(
            "Market Spread",
            f"{spread:.4f}"
        )

    st.info(
        f"""
### {status}

**Best Bank:** {summary["lowest_sell"]["bank"]}

**Highest Selling Rate:** {summary["highest_sell"]["bank"]}

Current spread is **{spread:.4f} BDT**.
"""
    )