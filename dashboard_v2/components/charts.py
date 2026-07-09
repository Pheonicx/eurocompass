import pandas as pd
import plotly.express as px
import streamlit as st


def charts(banks):

    st.markdown("## 📊 Today's Market Charts")

    df = pd.DataFrame(banks)

    left, right = st.columns(2)

    with left:

        buy_chart = px.bar(
            df.sort_values("buy"),
            x="bank",
            y="buy",
            color="buy",
            text="buy",
            title="EUR Buy Rates",
            color_continuous_scale="Blues",
        )

        buy_chart.update_traces(
            texttemplate="%.4f",
            textposition="outside",
        )

        buy_chart.update_layout(
            template="plotly_white",
            height=420,
            showlegend=False,
            xaxis_title="Bank",
            yaxis_title="BDT",
        )

        st.plotly_chart(
            buy_chart,
            width="stretch",
        )

    with right:

        sell_chart = px.bar(
            df.sort_values("sell"),
            x="bank",
            y="sell",
            color="sell",
            text="sell",
            title="TT Selling Rates",
            color_continuous_scale="Greens",
        )

        sell_chart.update_traces(
            texttemplate="%.4f",
            textposition="outside",
        )

        sell_chart.update_layout(
            template="plotly_white",
            height=420,
            showlegend=False,
            xaxis_title="Bank",
            yaxis_title="BDT",
        )

        st.plotly_chart(
            sell_chart,
            width="stretch",
        )