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
        assets / "tokens.css",
        assets / "fonts.css",
        assets / "animations.css",
        assets / "styles.css",

        assets / "theme" / "header.css",
        assets / "theme" / "metrics.css",
        assets / "theme" / "planner.css",
        assets / "theme" / "table.css",
        assets / "theme" / "charts.css",
    ]

    css = ""

    for file in css_files:

        if file.exists():

            css += file.read_text(
                encoding="utf-8"
            )

            css += "\n"

    st.markdown(
        f"<style>{css}</style>",
        unsafe_allow_html=True,
    )