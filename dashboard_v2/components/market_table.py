import pandas as pd
import streamlit as st


def market_table(banks):

    df = pd.DataFrame(banks)

    df = df.sort_values("sell").reset_index(drop=True)

    best = df.iloc[0]["sell"]

    medals = ["🥇", "🥈", "🥉"]

    rows = []

    for i, row in df.iterrows():

        rows.append(
            {
                "Rank": medals[i] if i < 3 else str(i + 1),
                "Bank": row["bank"],
                "Buy": f"{row['buy']:.4f}",
                "Sell": f"{row['sell']:.4f}",
                "Difference": f"+{row['sell']-best:.4f}",
            }
        )

    st.dataframe(
        pd.DataFrame(rows),
        width="stretch",
        hide_index=True,
        height=420,
    )