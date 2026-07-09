import streamlit as st


def insights(summary):

    best = summary["lowest_sell"]
    worst = summary["highest_sell"]

    spread = worst["value"] - best["value"]

    st.markdown("## 🧠 Smart Insights")

    c1, c2 = st.columns(2)

    with c1:

        with st.container(border=True):

            st.markdown("### 🏦 Best Choice Today")

            st.write(f"**{best['bank']}** currently offers the lowest TT selling rate.")

            st.metric(
                "Rate",
                f"৳ {best['value']:.4f}",
            )

            st.success("Recommended for today's transfer.")

    with c2:

        with st.container(border=True):

            st.markdown("### 📊 Market Overview")

            st.metric(
                "Today's Spread",
                f"৳ {spread:.4f}",
            )

            if spread < 0.20:
                status = "Low volatility"
            elif spread < 0.50:
                status = "Moderate volatility"
            else:
                status = "High volatility"

            st.write(f"**Market Status:** {status}")

            st.info(
                "Choosing the cheapest bank today can significantly reduce your transfer cost."
            )