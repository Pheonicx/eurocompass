import plotly.express as px


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

    fig = px.bar(
        data,
        x=x,
        y=y,
        text=y,
        color_discrete_sequence=[color],
    )

    fig.update_traces(
    texttemplate="%{y:.4f}",
    textposition="outside",
)
    

    fig.update_layout(
        title=title,
        xaxis_title="",
        yaxis_title="",
        height=450,
        template="plotly_white",
    )

    return fig