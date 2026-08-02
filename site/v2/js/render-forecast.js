import { state, rankedRates } from './state.js';
import { BANK_META } from './config.js';
import { buildForecast } from './calculations.js';
import { renderForecastChart } from './charts.js';

export function renderForecast() {
  const ranked = rankedRates();
  const chartEl = document.getElementById('forecastChartWrap');
  const legendEl = document.getElementById('forecastLegend');
  const summaryEl = document.getElementById('forecastSummary');
  if (!chartEl) return;

  const seriesByBank = ranked.map(r => {
    const f = buildForecast(r.bank_id);
    return {
      bank_id: r.bank_id,
      bank_name: r.bank_name,
      color: (BANK_META[r.bank_id] || {}).color || '#6B7280',
      points: f ? f.history : [],
    };
  }).filter(s => s.points.length > 0);

  const forecastByBank = {};
  ranked.forEach(r => { forecastByBank[r.bank_id] = buildForecast(r.bank_id); });

  chartEl.innerHTML = renderForecastChart(seriesByBank, forecastByBank, chartEl.clientWidth || 760);

  legendEl.innerHTML = seriesByBank.map(s => `
    <div class="legend-item">
      <div class="legend-dot" style="background:${s.color}"></div>
      ${BANK_META[s.bank_id]?.name || s.bank_name}
    </div>
  `).join('');

  const best = ranked[0];
  const f = best ? buildForecast(best.bank_id) : null;

  if (!f) {
    summaryEl.innerHTML = `Not enough historical data yet to project a trend${best ? ` for ${BANK_META[best.bank_id]?.name || best.bank_name}` : ''}. Forecasts need at least a few days of collected rates.`;
    return;
  }

  const lastVal = f.history[f.history.length - 1].value;
  const endVal = f.forecast[f.forecast.length - 1].value;
  const endDate = f.forecast[f.forecast.length - 1].date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  const change = (endVal - lastVal).toFixed(2);
  const dirWord = f.direction === 'rising' ? 'rising' : f.direction === 'falling' ? 'falling' : 'roughly flat';

  summaryEl.innerHTML = `
    <p>Based on the last ${f.history.length} readings of ${BANK_META[best.bank_id]?.name || best.bank_name}'s
    ${state.mode === 'send' ? 'selling' : 'buying'} rate, the trend is <b>${dirWord}</b>. If it continues in a
    straight line, the rate could be around <b>৳${endVal.toFixed(2)}</b> by ${endDate} — a change of
    ${change >= 0 ? '+' : ''}${change} from the latest reading.</p>
    <p class="forecast-disclaimer">This is a simple straight-line projection of recent history, not a
    prediction or guarantee. Real exchange rates move for many reasons this model can't see — treat it as
    a rough "if nothing changes" reference point, not financial advice.</p>
  `;
}
