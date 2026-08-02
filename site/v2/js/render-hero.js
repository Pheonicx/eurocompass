import { state, currentHistory, activeRate, rankedRates } from './state.js';
import { BANK_META, CURRENCY_META } from './config.js';
import { renderSparkline } from './charts.js';

export function renderHero() {
  const rates = rankedRates();
  const el = document.getElementById('heroBestCard');
  if (rates.length === 0) {
    el.innerHTML = `<div class="hist-empty">No live rate data for ${state.currency} right now.</div>`;
    return;
  }

  const best = rates[0];
  const second = rates[1];
  const meta = BANK_META[best.bank_id] || { name: best.bank_name, color: '#6B7280' };
  const symbol = CURRENCY_META[state.currency]?.symbol || '';
  const rateField = state.mode === 'send' ? 'sell' : 'buy';
  const modeLabel = state.mode === 'send' ? 'TT Selling' : 'TT Buying';

  const history = currentHistory().find(h => h.bank_id === best.bank_id);
  const points = history ? history.points : [];
  let deltaHtml = '';
  if (points.length >= 2) {
    const delta = points[points.length - 1][rateField] - points[0][rateField];
    const cls = delta > 0 ? 'diff-pos' : delta < 0 ? 'diff-best' : '';
    const sign = delta > 0 ? '+' : '';
    deltaHtml = `<span class="spark-delta ${cls}">${sign}${delta.toFixed(4)} over ${points.length} readings</span>`;
  }

  el.innerHTML = `
    <div class="best-eyebrow">
      Best rate right now
      <span class="mode-chip">${symbol} ${state.currency} · ${modeLabel}</span>
    </div>
    <div class="best-name-row">
      <div class="best-dot" style="background:${meta.color}"></div>
      <div class="best-name">${meta.name}</div>
      ${best.is_stale ? '<span class="stale-badge">Stale data</span>' : ''}
    </div>
    <div class="best-rate">${activeRate(best).toFixed(4)}</div>
    <div class="best-rate-unit">BDT per 1 ${state.currency}</div>
    ${second ? `
      <div class="best-compare">
        <div class="best-compare-text">
          <b>${Math.abs(activeRate(second) - activeRate(best)).toFixed(4)} BDT</b> ${state.mode === 'send' ? 'cheaper' : 'better'} per unit than the next best option,
          ${BANK_META[second.bank_id]?.name || second.bank_name}.
        </div>
      </div>` : ''}
    <div class="spark-block">
      <div class="spark-label-row">
        <span class="spark-label">Recent trend</span>
        ${deltaHtml}
      </div>
      ${renderSparkline(points, meta.color, rateField)}
    </div>
    <div class="chip-row">
      <span class="chip">${best.confidence} confidence</span>
      ${best.student_rate && state.mode === 'send' ? `<span class="chip">Student rate: ${best.student_rate.toFixed(4)}</span>` : ''}
    </div>
  `;
}
