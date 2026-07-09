import base64
import io
import os

import pandas as pd
import requests
import streamlit as st


def get_secret(key: str, default: str = ""):
    """
    Safely read a Streamlit secret.
    Falls back to environment variables or a default value
    when running locally without secrets.toml.
    """
    try:
        return st.secrets[key]
    except Exception:
        return os.getenv(key, default)


@st.cache_data(ttl=3600)
def load_history(bank: str):
    """
    Load historical exchange rate data from GitHub
    using the authenticated GitHub Contents API.
    """

    owner = get_secret("GITHUB_USERNAME", "Pheonicx")
    repo = get_secret("GITHUB_REPO", "eurocompass")
    token = get_secret("GITHUB_TOKEN", "")

    url = (
        f"https://api.github.com/repos/"
        f"{owner}/{repo}/contents/history/{bank}.csv"
    )

    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "EuroCompass",
    }

    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        response = requests.get(
            url,
            headers=headers,
            timeout=20,
        )

        response.raise_for_status()

        payload = response.json()

        content = base64.b64decode(
            payload["content"]
        ).decode("utf-8")

        df = pd.read_csv(io.StringIO(content))

        if df.empty:
            return None

        df["Timestamp"] = pd.to_datetime(
            df["Date"] + " " + df["Time"]
        )

        return df.sort_values("Timestamp")

    except Exception as e:
        st.warning(f"Unable to load history: {e}")
        return None