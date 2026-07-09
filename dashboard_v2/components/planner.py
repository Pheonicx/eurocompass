import streamlit as st

from dashboard_v2.services.transfer import calculate_transfer


def planner(banks):

    st.markdown("## 🇩🇪 Germany Transfer Calculator")
    st.caption("Calculate the cheapest way to send money to Germany.")

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

    left, right = st.columns([1.2, 1])

    with left:

        st.metric(
            "🏆 Recommended Bank",
            best["bank"],
        )

        st.metric(
            "Total Transfer Cost",
            f"৳ {best['total']:,.0f}",
        )

    with right:

        st.metric(
            "You Save",
            f"৳ {savings:,.0f}",
        )

        spread = worst["rate"] - best["rate"]

        st.metric(
            "Market Spread",
            f"৳ {spread:.4f}",
        )

    st.info(
        f"""
### Recommendation

✅ **Transfer today using {best['bank']}**

For a transfer of **€{amount:,.0f}**, choosing **{best['bank']}** instead of **{worst['bank']}** saves approximately **৳ {savings:,.0f}**.
"""
    )