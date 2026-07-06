import pandas as pd
import streamlit as st
import subprocess
import sys

from pathlib import Path
from loader import load_market_data
from metrics import calculate_metrics
from charts import create_bar_chart
from history import load_history
from history_chart import create_history_chart
from calculator import calculate_transfer_cost, get_best_bank
from config.banks import BANKS

st.set_page_config(
    page_title="EuroCompass",
    page_icon="🧭",
    layout="wide",
)



data = load_market_data()

if data is None:
    st.error("No market data found. Run main.py first.")
    st.stop()

banks = data["banks"]
summary = data["summary"]

df = pd.DataFrame(banks)

df["Spread"] = df["sell"] - df["buy"]

df = df.rename(
    columns={
        "bank": "Bank",
        "currency": "Currency",
        "buy": "Buy",
        "sell": "Sell",
    }
)

# Rank by lowest buy price
df = df.sort_values("Buy").reset_index(drop=True)

medals = ["🥇", "🥈", "🥉"]

rank = []

for i in range(len(df)):
    if i < 3:
        rank.append(medals[i])
    else:
        rank.append(str(i + 1))

df.insert(0, "Rank", rank)

# Format numbers
df["Buy"] = df["Buy"].map(lambda x: f"{x:.4f}")
df["Sell"] = df["Sell"].map(lambda x: f"{x:.4f}")
df["Spread"] = df["Spread"].map(lambda x: f"{x:.4f}")

stats = calculate_metrics(banks)

st.logo("https://img.icons8.com/fluency/96/compass.png")
st.title("🧭 EuroCompass")
st.caption("Compare EUR exchange rates across leading Bangladeshi banks.")
st.caption(f"Last Updated: {data['generated_at']}")
st.divider()

col1, col2 = st.columns([1, 5])

with col1:

    if st.button("🔄 Refresh Market"):

        project_root = Path(__file__).resolve().parent.parent
        main_file = project_root / "main.py"

        with st.spinner("Collecting latest exchange rates..."):

            subprocess.run(
                [sys.executable, str(main_file)],
                check=False,
            )

        st.success("Market data updated!")

        st.rerun()
st.divider()

st.header("🇩🇪 Germany Transfer Calculator")

euro_amount = st.number_input(
    "Transfer Amount (€)",
    min_value=100.0,
    value=11904.0,
    step=100.0,
)

transfer_results = calculate_transfer_cost(
    banks,
    euro_amount,
)

best_bank = get_best_bank(transfer_results)

most_expensive = max(
    transfer_results,
    key=lambda x: x["total_cost"],
)

savings = (
    most_expensive["total_cost"]
    - best_bank["total_cost"]
)

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "🏦 Recommended Bank",
        best_bank["bank"],
    )

with col2:
    st.metric(
        "TT Selling Rate",
        f'{best_bank["rate"]:.4f}',
    )

with col3:
    st.metric(
        "Estimated Cost",
        f'{best_bank["total_cost"]:,.2f} BDT',
    )

with col4:
    st.metric(
        "Savings",
        f'{savings:,.2f} BDT',
    )

st.success(
    f"Recommendation: Use **{best_bank['bank']}**. "
    f"You save approximately **{savings:,.2f} BDT** compared with the most expensive bank."
)

st.divider()

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Lowest Buy",
        f"{summary['lowest_buy']['value']:.4f}",
        summary["lowest_buy"]["bank"],
    )

with col2:
    st.metric(
        "Highest Buy",
        f"{summary['highest_buy']['value']:.4f}",
        summary["highest_buy"]["bank"],
    )

with col3:
    st.metric(
        "Lowest Sell",
        f"{summary['lowest_sell']['value']:.4f}",
        summary["lowest_sell"]["bank"],
    )

with col4:
    st.metric(
        "Highest Sell",
        f"{summary['highest_sell']['value']:.4f}",
        summary["highest_sell"]["bank"],
    )

st.divider()

st.subheader("🏦 Live Exchange Rates")
comparison_df = pd.DataFrame(transfer_results)

comparison_df = comparison_df.rename(
    columns={
        "bank": "Bank",
        "rate": "TT Selling",
        "total_cost": "Total Cost (BDT)",
        "extra_cost": "Extra Cost (BDT)",
    }
)

comparison_df["TT Selling"] = comparison_df["TT Selling"].map(
    lambda x: f"{x:.4f}"
)

comparison_df["Total Cost (BDT)"] = comparison_df["Total Cost (BDT)"].map(
    lambda x: f"{x:,.2f}"
)

comparison_df["Extra Cost (BDT)"] = comparison_df["Extra Cost (BDT)"].map(
    lambda x: f"{x:,.2f}"
)

st.subheader("💰 Germany Transfer Comparison")

st.dataframe(
    comparison_df,
    use_container_width=True,
    hide_index=True,
)

st.divider()

st.dataframe(
    df,
    use_container_width=True,
    hide_index=True,
)

st.divider()

left, right = st.columns(2)

with left:

    fig = create_bar_chart(
        banks,
        x="bank",
        y="buy",
        title="EUR Buy Rate",
        color="#2E86DE",
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
    )

with right:

    fig = create_bar_chart(
        banks,
        x="bank",
        y="sell",
        title="EUR Sell Rate",
        color="#E74C3C",
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
    )

st.divider()

st.success(
    f"Live market data collected from {summary['banks_processed']} banks."
)
st.divider()

st.header("📈 Historical Exchange Rate Analysis")

bank_names = [
    collector.__name__.split(".")[-1].upper()
    for collector in BANKS
]

selected_bank = st.selectbox(
    "Select Bank",
    sorted(bank_names),
)

history_df = load_history(selected_bank)

if history_df is not None:

    fig = create_history_chart(
        history_df,
        selected_bank,
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
    )

else:

    st.info("No historical data available yet.")