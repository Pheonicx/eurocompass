import { state, currentHistory } from './state.js';
import { BANK_META } from './config.js';
import { renderHistoryChart } from './charts.js';

export function renderHistory() {
  const history = currentHistory();
  const chartEl = document.getElementById('histChartWrap');
  const legendEl = document.getElementById('histLegend');
  const captionEl = document.getElementById('histCaption');
  const valueField = state.mode === 'send' ? 'sell' : 'buy';

  const seriesByBank = history.map(h => ({
    ...h,
    color: (BANK_META[h.bank_id] || {}).color || '#6B7280',
  }));

  const totalPoints = seriesByBank.reduce((sum, s) => sum + s.points.length, 0);
  captionEl.textContent = totalPoints > 0
    ? `TT ${state.mode === 'send' ? 'selling' : 'buying'} rate, all banks compared, ${state.currency}`
    : 'Not enough historical data yet';

  chartEl.innerHTML = renderHistoryChart(seriesByBank, valueField, chartEl.clientWidth || 760);

  legendEl.innerHTML = seriesByBank.map(s => `
    <div class="legend-item">
      <div class="legend-dot" style="background:${s.color}"></div>
      ${BANK_META[s.bank_id]?.name || s.bank_name}
    </div>
  `).join('');
}
