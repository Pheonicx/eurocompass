import streamlit as st


def metric_card(title, value, bank, icon):

    with st.container(border=True):

        st.caption(f"{icon} {title}")

        st.markdown(
            f"""
## ৳ {value:.4f}
"""
        )

        st.caption(f"Bank: {bank}")


def metrics(summary):

    c1, c2, c3, c4 = st.columns(4, gap="large")

    with c1:
        metric_card(
            "Lowest Sell",
            summary["lowest_sell"]["value"],
            summary["lowest_sell"]["bank"],
            "🏦",
        )

    with c2:
        metric_card(
            "Highest Sell",
            summary["highest_sell"]["value"],
            summary["highest_sell"]["bank"],
            "📈",
        )

    with c3:
        metric_card(
            "Lowest Buy",
            summary["lowest_buy"]["value"],
            summary["lowest_buy"]["bank"],
            "💶",
        )

    with c4:
        metric_card(
            "Highest Buy",
            summary["highest_buy"]["value"],
            summary["highest_buy"]["bank"],
            "💰",
        )