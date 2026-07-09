import plotly.graph_objects as go


BUY_COLOR = "#2563EB"
SELL_COLOR = "#EF4444"
GRID_COLOR = "rgba(148, 163, 184, 0.22)"
TEXT_COLOR = "#0F172A"
MUTED_TEXT = "#64748B"


def create_history_chart(df, bank):
    """
    Create an interactive Buy/Sell history chart.
    """

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df["Timestamp"],
            y=df["Buy"],
            mode="lines+markers",
            name="Buy",
            line={
                "color": BUY_COLOR,
                "width": 3,
            },
            marker={
                "size": 6,
                "color": BUY_COLOR,
                "line": {
                    "color": "white",
                    "width": 1.5,
                },
            },
            hovertemplate=(
                "<b>%{x|%d %b %Y}</b><br>"
                "Buy: %{y:.4f} BDT"
                "<extra></extra>"
            ),
        )
    )

    fig.add_trace(
        go.Scatter(
            x=df["Timestamp"],
            y=df["Sell"],
            mode="lines+markers",
            name="Sell",
            line={
                "color": SELL_COLOR,
                "width": 3,
            },
            marker={
                "size": 6,
                "color": SELL_COLOR,
                "line": {
                    "color": "white",
                    "width": 1.5,
                },
            },
            hovertemplate=(
                "<b>%{x|%d %b %Y}</b><br>"
                "Sell: %{y:.4f} BDT"
                "<extra></extra>"
            ),
        )
    )

    fig.update_layout(
        title=f"{bank} - Historical EUR Buy/Sell Movement",
        height=430,
        template="none",
        margin={
            "l": 18,
            "r": 18,
            "t": 70,
            "b": 36,
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
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "right",
            "x": 1,
            "title": "",
        },
        hovermode="x unified",
        hoverlabel={
            "bgcolor": "white",
            "bordercolor": "rgba(15, 23, 42, 0.12)",
            "font_size": 13,
            "font_family": "Inter, Segoe UI, sans-serif",
        },
    )

    fig.update_xaxes(
        title_text="",
        showgrid=False,
        tickfont={
            "size": 12,
            "color": MUTED_TEXT,
        },
    )

    fig.update_yaxes(
        title_text="BDT per EUR",
        showgrid=True,
        gridcolor=GRID_COLOR,
        zeroline=False,
        tickfont={
            "size": 12,
            "color": MUTED_TEXT,
        },
    )

    return fig
