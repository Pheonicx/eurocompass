def metric_card(
    icon,
    title,
    value,
    bank,
    description,
):

    return f"""
<div class="metric-card">

<div class="metric-icon">
{icon}
</div>

<div class="metric-title">
{title}
</div>

<div class="metric-value">
{value}
</div>

<div class="metric-bank">
🏦 {bank}
</div>

<div class="metric-description">
{description}
</div>

</div>
"""