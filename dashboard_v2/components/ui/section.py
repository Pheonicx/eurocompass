"""
Reusable section heading.
"""


import streamlit as st


def section(
    icon: str,
    title: str,
    subtitle: str = "",
):

    st.markdown(
        f"""
<div style="margin-top:45px;margin-bottom:20px;">

<h2 style="
margin:0;
font-size:30px;
font-weight:800;
color:#0F172A;
">

{icon} {title}

</h2>

<p style="
margin-top:8px;
color:#64748B;
font-size:16px;
">

{subtitle}

</p>

</div>
""",
        unsafe_allow_html=True,
    )