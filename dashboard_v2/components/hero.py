import streamlit as st


def hero(data):

    st.markdown(
        f"""
<div class="hero">

<div class="hero-title">

🧭 EUROCOMPASS

</div>

<div class="hero-subtitle">

Navigate Every Euro

</div>

<div class="hero-info">

🟢 LIVE &nbsp;&nbsp;&nbsp;

Last Updated: {data["generated_at"]}

</div>

</div>
""",
        unsafe_allow_html=True,
    )