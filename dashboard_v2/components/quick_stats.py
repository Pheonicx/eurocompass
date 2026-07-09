import streamlit as st


def quick_stats(summary):

    c1, c2, c3 = st.columns(3)

    with c1:
        st.metric(
            "Banks Monitored",
            summary["banks_processed"],
        )

    with c2:
        spread = (
            summary["highest_sell"]["value"]
            - summary["lowest_sell"]["value"]
        )

        st.metric(
            "Today's Spread",
            f"{spread:.4f}",
        )

    with c3:
        st.metric(
            "Market Status",
            "LIVE",
        )