import io

import pandas as pd
import requests
import streamlit as st


def load_history(bank: str):
    """
    Load historical data from GitHub.
    """

    owner = st.secrets["GITHUB_USERNAME"]
    repo = st.secrets["GITHUB_REPO"]

    url = (
        f"https://raw.githubusercontent.com/"
        f"{owner}/{repo}/main/history/{bank}.csv"
    )

    response = requests.get(url, timeout=20)

    if response.status_code != 200:
        return None

    df = pd.read_csv(io.StringIO(response.text))

    if df.empty:
        return None

    df["Timestamp"] = pd.to_datetime(
        df["Date"] + " " + df["Time"]
    )

    df = df.sort_values("Timestamp")

    return df