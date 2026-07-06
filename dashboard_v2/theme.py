from pathlib import Path
import streamlit as st


def load_theme():

    st.set_page_config(
        page_title="EuroCompass",
        page_icon="🧭",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    assets = Path(__file__).parent / "assets"

    css_files = [
        "tokens.css",
        "fonts.css",
        "animations.css",
        "styles.css",
    ]

    css = ""

    for file in css_files:
        with open(assets / file, encoding="utf-8") as f:
            css += f.read() + "\n"

    st.markdown(
        f"<style>{css}</style>",
        unsafe_allow_html=True,
    )