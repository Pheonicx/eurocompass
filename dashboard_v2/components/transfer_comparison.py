import pandas as pd
import plotly.express as px
import streamlit as st

from dashboard_v2.services.transfer import calculate_transfer


def transfer_comparison(banks):

    st.markdown("## 💸 Transfer Cost Comparison")
    st.caption("Compare the total cost of sending money to Germany across all available banks.")

    amount = st.number_input(
        "Comparison Amount (€)",
        min_value=100.0,
        value=11904.0,
        step=100.0,
        key="comparison_amount",
    )

    _, _, _, results = calculate_transfer(
        banks,
        amount,
    )

    df = pd.DataFrame(results).sort_values("total")

    fig = px.bar(
        df,
        x="bank",
        y="total",
        text="total",
        color="total",
        color_continuous_scale="Blues_r",
        title=f"Total Cost for €{amount:,.0f}",
    )

    fig.update_traces(
        texttemplate="৳ %{y:,.0f}",
        textposition="outside",
    )

    fig.update_layout(
        template="plotly_white",
        height=460,
        margin=dict(l=20, r=20, t=60, b=20),
        xaxis_title="",
        yaxis_title="BDT",
        coloraxis_showscale=False,
    )

    st.plotly_chart(
        fig,
        width="stretch",
    )

    cheapest = df.iloc[0]
    expensive = df.iloc[-1]

    savings = expensive["total"] - cheapest["total"]

    st.success(
        f"""
**Best Choice:** {cheapest['bank']}

Sending **€{amount:,.0f}** through **{cheapest['bank']}**
saves approximately **৳ {savings:,.0f}**
compared with **{expensive['bank']}**.
"""
    )