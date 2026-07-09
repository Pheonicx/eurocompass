import pandas as pd
import plotly.graph_objects as go


BEST_COLOR = "#14B8A6"
WORST_COLOR = "#FB7185"
NEUTRAL_COLOR = "#94A3B8"
GRID_COLOR = "rgba(148, 163, 184, 0.22)"
TEXT_COLOR = "#0F172A"
MUTED_TEXT = "#64748B"


def create_bar_chart(
    data,
    x,
    y,
    title,
    color,
):
    """
    Create a reusable Plotly bar chart.
    """

    df = pd.DataFrame(data).copy()

    if df.empty:
        return go.Figure()

    best_is_low = y == "sell"
    df = df.sort_values(y, ascending=best_is_low).reset_index(drop=True)

    best_value = df[y].min() if best_is_low else df[y].max()
    worst_value = df[y].max() if best_is_low else df[y].min()

    colors = []
    differences = []

    for value in df[y]:
        if value == best_value:
            colors.append(BEST_COLOR)
        elif value == worst_value:
            colors.append(WORST_COLOR)
        else:
            colors.append(NEUTRAL_COLOR)

        difference = value - best_value if best_is_low else best_value - value
        differences.append(difference)

    fig = go.Figure(
        data=[
            go.Bar(
                x=df[y],
                y=df[x],
                orientation="h",
                marker={
                    "color": colors,
                    "line": {
                        "color": "rgba(15, 23, 42, 0.06)",
                        "width": 1,
                    },
                },
                text=[f"{value:.4f}" for value in df[y]],
                textposition="outside",
                cliponaxis=False,
                textfont={
                    "size": 13,
                    "color": TEXT_COLOR,
                },
                customdata=list(zip(df[x], df[y], differences)),
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>"
                    "Rate: %{customdata[1]:.4f} BDT<br>"
                    "Difference from best: %{customdata[2]:.4f}"
                    "<extra></extra>"
                ),
            )
        ]
    )

    fig.update_layout(
        title=title,
        height=390,
        template="none",
        bargap=0.42,
        margin={
            "l": 92,
            "r": 54,
            "t": 68,
            "b": 38,
        },
        paper_bgcolor="white",
        plot_bgcolor="white",
        font={
            "family": "Inter, Segoe UI, sans-serif",
            "color": TEXT_COLOR,
        },
        title_font={
            "size": 19,
            "color": TEXT_COLOR,
        },
        showlegend=False,
        hoverlabel={
            "bgcolor": "white",
            "bordercolor": "rgba(15, 23, 42, 0.12)",
            "font_size": 13,
            "font_family": "Inter, Segoe UI, sans-serif",
        },
    )

    fig.update_xaxes(
        title_text="BDT per EUR",
        showgrid=True,
        gridcolor=GRID_COLOR,
        zeroline=False,
        tickfont={
            "size": 12,
            "color": MUTED_TEXT,
        },
    )

    fig.update_yaxes(
        title_text="",
        autorange="reversed",
        showgrid=False,
        tickfont={
            "size": 13,
            "color": TEXT_COLOR,
        },
    )

    return fig
