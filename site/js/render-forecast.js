import { state } from './state.js';
import { buildForecast, rankedBanks } from './calculations.js';
import { renderForecastChart } from './charts.js';

export function renderForecast() {
  renderForecastChart();

  const ranked = rankedBanks(state);
  const best = ranked[0];
  const f = buildForecast(state, best.key);
  const summaryEl = document.getElementById('forecastSummary');
  const legendEl = document.getElementById('forecastLegend');

  legendEl.innerHTML = state.banks.map(b =>
    `<span class="legend-item"><span class="legend-dot" style="background:${b.color};"></span>${b.name}</span>`
  ).join('');

  if (!f) {
    summaryEl.innerHTML = `Not enough historical data yet to project a trend for ${best.name}. Forecasts need at least a few days of collected rates.`;
    return;
  }

  const lastVal = f.history[f.history.length - 1].value;
  const endVal = f.forecast[f.forecast.length - 1].value;
  const endDate = f.forecast[f.forecast.length - 1].date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  const change = (endVal - lastVal).toFixed(2);
  const dirWord = f.direction === 'rising' ? 'rising' : f.direction === 'falling' ? 'falling' : 'roughly flat';

  summaryEl.innerHTML = `
    <p>Based on the last ${f.history.length} days of ${best.name}'s ${state.mode === 'buy' ? 'selling' : 'buying'} rate,
    the trend is <b>${dirWord}</b>. If it continues in a straight line, the rate could be around
    <b>৳${endVal.toFixed(2)}</b> by ${endDate} — a change of ${change >= 0 ? '+' : ''}${change} from today.</p>
    <p class="forecast-disclaimer">This is a simple straight-line projection of recent history, not a prediction
    or guarantee. Real exchange rates move for many reasons this model can't see — treat it as a rough
    "if nothing changes" reference point, not financial advice.</p>
  `;
}
