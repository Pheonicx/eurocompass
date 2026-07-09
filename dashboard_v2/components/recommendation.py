import streamlit as st

from dashboard_v2.services.recommendation import get_recommendation


def recommendation(summary, banks):

    rec = get_recommendation(summary, banks)

    st.markdown("## 🤖 EuroCompass Recommendation")

    if rec["color"] == "green":
        st.success(
            f"""
### ✅ {rec['action']}

**Recommended Bank:** {rec['bank']}

TT Selling Rate:
**৳ {rec['rate']:.4f}**

Estimated Saving:
**৳ {rec['savings']:,.0f}**

{rec['reason']}
"""
        )

    elif rec["color"] == "blue":

        st.info(
            f"""
### ℹ️ {rec['action']}

**Recommended Bank:** {rec['bank']}

TT Selling Rate:
**৳ {rec['rate']:.4f}**

Estimated Saving:
**৳ {rec['savings']:,.0f}**

{rec['reason']}
"""
        )

    else:

        st.warning(
            f"""
### ⚠️ {rec['action']}

**Recommended Bank:** {rec['bank']}

TT Selling Rate:
**৳ {rec['rate']:.4f}**

Estimated Saving:
**৳ {rec['savings']:,.0f}**

{rec['reason']}
"""
        )