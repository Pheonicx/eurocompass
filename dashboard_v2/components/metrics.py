import streamlit as st

from components.ui.stat import stat


def metrics(summary):

    cols = st.columns(4)

    with cols[0]:
        st.markdown(
            stat(
                icon="💶",
                title="Lowest Buy",
                value=f"{summary['lowest_buy']['value']:.4f}",
                subtitle=summary["lowest_buy"]["bank"],
                accent="#10B981",
            ),
            unsafe_allow_html=True,
        )

    with cols[1]:
        st.markdown(
            stat(
                icon="💸",
                title="Highest Buy",
                value=f"{summary['highest_buy']['value']:.4f}",
                subtitle=summary["highest_buy"]["bank"],
                accent="#F59E0B",
            ),
            unsafe_allow_html=True,
        )

    with cols[2]:
        st.markdown(
            stat(
                icon="🏦",
                title="Lowest Sell",
                value=f"{summary['lowest_sell']['value']:.4f}",
                subtitle=summary["lowest_sell"]["bank"],
                accent="#2563EB",
            ),
            unsafe_allow_html=True,
        )

    with cols[3]:
        st.markdown(
            stat(
                icon="📈",
                title="Highest Sell",
                value=f"{summary['highest_sell']['value']:.4f}",
                subtitle=summary["highest_sell"]["bank"],
                accent="#EF4444",
            ),
            unsafe_allow_html=True,
        )