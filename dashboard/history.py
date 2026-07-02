import io
import os

import pandas as pd
import requests
import streamlit as st


def get_secret(key: str, default: str):
    """
    Safely read a Streamlit secret.
    Falls back to environment variables or a default value
    when running locally without secrets.toml.
    """
    try:
        return st.secrets[key]
    except Exception:
        return os.getenv(key, default)


def load_history(bank: str):
    """
    Load historical exchange rate data from GitHub.
    """

    owner = get_secret("GITHUB_USERNAME", "Pheonicx")
    repo = get_secret("GITHUB_REPO", "eurocompass")
    branch = get_secret("GITHUB_BRANCH", "main")

    url = (
        f"https://raw.githubusercontent.com/"
        f"{owner}/{repo}/{branch}/history/{bank}.csv"
    )

    try:
        response = requests.get(url, timeout=20)
        response.raise_for_status()

        df = pd.read_csv(io.StringIO(response.text))

        if df.empty:
            return None

        df["Timestamp"] = pd.to_datetime(
            df["Date"] + " " + df["Time"]
        )

        return df.sort_values("Timestamp")

    except Exception as e:
        st.warning(f"Unable to load history: {e}")
        return None