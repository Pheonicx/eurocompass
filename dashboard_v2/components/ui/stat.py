"""
Reusable statistic card for EuroCompass.

Use this component anywhere a KPI or summary value
needs to be displayed.
"""

from .card import card


def stat(
    *,
    icon: str,
    title: str,
    value: str,
    subtitle: str,
    accent: str = "#2563EB",
):
    content = f"""
<div style="
display:flex;
justify-content:space-between;
align-items:flex-start;
margin-bottom:18px;
">

<div style="
width:56px;
height:56px;
border-radius:16px;
background:{accent}15;
display:flex;
align-items:center;
justify-content:center;
font-size:28px;
">
{icon}
</div>

</div>

<div style="
font-size:15px;
font-weight:600;
color:#64748B;
margin-bottom:10px;
">
{title}
</div>

<div style="
font-size:34px;
font-weight:800;
color:#0F172A;
line-height:1.1;
">
{value}
</div>

<div style="
margin-top:12px;
font-size:15px;
font-weight:600;
color:{accent};
">
{subtitle}
</div>
"""

    return card(content)