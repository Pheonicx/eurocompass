import plotly.express as px


def create_history_chart(df, bank):
    """
    Create an interactive Buy/Sell history chart.
    """

    fig = px.line(
        df,
        x="Timestamp",
        y=["Buy", "Sell"],
        markers=True,
        title=f"{bank} - EUR Exchange Rate History",
    )

    fig.update_layout(
        height=450,
        legend_title="Rate",
        xaxis_title="Date",
        yaxis_title="BDT",
        template="plotly_white",
    )

    fig.update_traces(line=dict(width=3))

    return fig