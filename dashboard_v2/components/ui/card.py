"""
Reusable Card component for EuroCompass.

This component wraps arbitrary HTML content inside
a consistently styled card.
"""


def card(content: str) -> str:
    return f"""
<div class="card">

{content}

</div>
"""