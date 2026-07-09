import streamlit as st

from loader import load_market_data
from theme import load_theme

from components.header import header
from components.metrics import metrics
from components.planner import planner
from components.charts import charts
from components.quick_stats import quick_stats
from components.analytics import analytics
from components.gauge import market_gauge
from components.recommendation import recommendation
from components.transfer_comparison import transfer_comparison
from components.market_table import market_table
from components.history_section import history_section
from components.intelligence import intelligence

# =====================================================
# PAGE SETUP
# =====================================================

load_theme()

data = load_market_data()

if data is None:
    st.error("No market data found.")
    st.stop()

summary = data["summary"]
banks = data["banks"]
market_spread = (
    summary["highest_sell"]["value"]
    - summary["lowest_sell"]["value"]
)


# =====================================================
# HEADER
# =====================================================

header(
    data,
    summary,
)

st.write()


# =====================================================
# METRICS
# =====================================================

metrics(
    summary,
)

st.write()


# =====================================================
# EUROCOMPASS AI RECOMMENDATION
# =====================================================

recommendation(
    summary,
    banks,
)

st.write()


# =====================================================
# GERMANY TRANSFER PLANNER
# =====================================================

planner(
    banks,
)

st.write()


# =====================================================
# LIVE MARKET CHARTS
# =====================================================

charts(
    banks,
)

st.write()


# =====================================================
# MARKET ANALYTICS
# =====================================================

intelligence(
    selected_bank=summary["lowest_sell"]["bank"],
    market_spread=market_spread,
)

st.write()


# =====================================================
# TRANSFER COMPARISON
# =====================================================

transfer_comparison(
    banks,
)

st.write()


# =====================================================
# MARKET TABLE
# =====================================================

market_table(
    banks,
)

st.write()


# =====================================================
# HISTORY
# =====================================================

history_section(
    banks,
)