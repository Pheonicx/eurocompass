import streamlit as st


def market_overview(data, summary):

    best = summary["lowest_sell"]

    st.markdown(
        f"""
<div class="hero">

<div class="hero-wrapper">

<div class="hero-left">

<h1 class="hero-title">
🧭 EuroCompass
</h1>

<div class="hero-subtitle">

Navigate Every Euro

</div>

<p class="hero-description">

Real-time EUR exchange intelligence for students, professionals,
and families sending money to Germany.

</p>

<div class="hero-divider"></div>

<div class="status-row">

<div class="pill">🟢 LIVE</div>

<div class="pill">🕒 {data["generated_at"]}</div>

<div class="pill">🏦 {summary["banks_processed"]} Banks</div>

<div class="pill">⚡ GitHub Actions</div>

<div class="pill">☁ Cloudflare</div>

</div>

</div>

<div class="hero-right">

<div class="best-card">

<div class="best-title">

🏆 TODAY'S BEST RATE

</div>

<div class="best-bank">

{best["bank"]}

</div>

<div class="best-rate">

৳ {best["value"]:.4f}

</div>

<div class="best-save">

Lowest TT Selling Rate Today

</div>

</div>

</div>

</div>

</div>
""",
        unsafe_allow_html=True,
    )