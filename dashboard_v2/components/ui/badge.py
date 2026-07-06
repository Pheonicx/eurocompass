"""
Reusable badge.
"""


def badge(
    text: str,
    color: str = "blue",
):

    colors = {

        "blue": "#DBEAFE",

        "green": "#DCFCE7",

        "red": "#FEE2E2",

        "yellow": "#FEF3C7",

        "gray": "#F1F5F9",

    }

    text_colors = {

        "blue": "#2563EB",

        "green": "#16A34A",

        "red": "#DC2626",

        "yellow": "#D97706",

        "gray": "#475569",

    }

    return f"""
<span
style="
display:inline-block;
padding:8px 16px;
border-radius:999px;
background:{colors[color]};
color:{text_colors[color]};
font-weight:700;
font-size:14px;
margin-right:8px;
">
{text}
</span>
"""