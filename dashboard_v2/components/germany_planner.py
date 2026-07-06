import streamlit as st

from dashboard_v2.services.transfer import calculate_transfer


def germany_planner(banks):

    st.markdown(
        """
<div class="planner">

<div class="planner-title">

🇩🇪 Germany Transfer Planner

</div>

<div class="planner-sub">

Find the cheapest bank for your Germany transfer.

</div>
""",
        unsafe_allow_html=True,
    )

    amount = st.number_input(
        "Transfer Amount (€)",
        min_value=100.0,
        value=11904.0,
        step=100.0,
    )

    best, worst, savings, _ = calculate_transfer(
        banks,
        amount,
    )

    st.markdown(
        f"""
<div class="result-card">

<div class="result-label">

Recommended Bank

</div>

<div class="result-bank">

🏦 {best["bank"]}

</div>

<div class="result-value">

৳ {best["total"]:,.2f}

</div>

<div class="result-saving">

💰 You save approximately ৳ {savings:,.2f}

</div>

</div>

</div>
""",
        unsafe_allow_html=True,
    )