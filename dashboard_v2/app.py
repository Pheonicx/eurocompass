import streamlit as st

from loader import load_market_data
from theme import load_theme

from components.market_overview import market_overview
from components.metrics import metrics
from components.germany_planner import germany_planner

load_theme()

data = load_market_data()

if data is None:

    st.error("No market data found.")

    st.stop()

market_overview(
    data,
    data["summary"],
)
metrics(
    data["summary"]
)

germany_planner(
    data["banks"]
)