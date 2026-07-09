import streamlit as st

from dashboard_v2.history import load_history
from dashboard_v2.history_chart import create_history_chart


def history_section(banks):

    st.markdown("## 📈 Exchange Rate History")
    st.caption("Historical Buy & Sell rates")

    bank_names = [bank["bank"] for bank in banks]

    selected_bank = st.selectbox(
        "Select Bank",
        bank_names,
    )

    df = load_history(selected_bank)

    if df is None:
        st.info("No historical data available.")
        return

    fig = create_history_chart(
        df,
        selected_bank,
    )

    st.plotly_chart(
        fig,
        width="stretch",
    )

    latest = df.iloc[-1]

    c1, c2, c3 = st.columns(3)

    with c1:
        st.metric(
            "Latest Buy",
            f"৳ {latest['Buy']:.4f}",
        )

    with c2:
        st.metric(
            "Latest Sell",
            f"৳ {latest['Sell']:.4f}",
        )

    with c3:
        st.metric(
            "History Records",
            len(df),
        )