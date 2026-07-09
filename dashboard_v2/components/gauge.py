import plotly.graph_objects as go
import streamlit as st


def market_gauge(summary):

    spread = (
        summary["highest_sell"]["value"]
        - summary["lowest_sell"]["value"]
    )

    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",

            value=spread,

            title={
                "text":"Market Spread (BDT)"
            },

            gauge={

                "axis":{
                    "range":[0,2]
                },

                "bar":{
                    "color":"royalblue"
                },

                "steps":[

                    {
                        "range":[0,.5],
                        "color":"lightgreen"
                    },

                    {
                        "range":[.5,1],
                        "color":"khaki"
                    },

                    {
                        "range":[1,2],
                        "color":"salmon"
                    }

                ]

            }

        )
    )

    fig.update_layout(height=350)

    st.plotly_chart(
        fig,
        width="stretch"
    )