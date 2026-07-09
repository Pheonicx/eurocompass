import pandas as pd
import streamlit as st


def ranking(banks):

    st.subheader("🏆 Today's Bank Ranking")

    df = pd.DataFrame(banks)

    df = df.sort_values("sell")

    df.insert(
        0,
        "Rank",
        range(
            1,
            len(df) + 1,
        ),
    )

    medals = {
        1: "🥇",
        2: "🥈",
        3: "🥉",
    }

    for _, row in df.iterrows():

        rank = row["Rank"]

        emoji = medals.get(rank, "•")

        st.markdown(
            f"""
**{emoji} #{rank} {row["bank"]}**

TT Selling Rate: **৳ {row["sell"]:.4f}**

---
"""
        )