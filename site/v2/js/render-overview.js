import { state, currentRates, activeRate } from './state.js';
import { BANK_META, CURRENCY_META } from './config.js';
import { computeMarketIntelligence } from './calculations.js';
import { renderBarChart } from './charts.js';

export function renderTrustStrip() {
  const rates = currentRates();
  const el = document.getElementById('trustStrip');
  if (!el) return;

  const totalConfigured = 5;
  const highCount = rates.filter(r => r.confidence === 'high').length;
  const staleCount = rates.filter(r => r.is_stale).length;

  document.getElementById('trustBanksStat').innerHTML =
    `<b>${rates.length}/${totalConfigured}</b> banks reporting`;
  document.getElementById('trustConfidenceStat').innerHTML =
    `<b>${highCount}/${rates.length || 0}</b> at high confidence`;
  document.getElementById('trustStaleStat').innerHTML = staleCount > 0
    ? `<b>${staleCount}</b> flagged stale`
    : `<b>0</b> flagged stale`;
}

export function renderTicker() {
  const rates = currentRates();
  const el = document.getElementById('tickerTrack');
  if (!el) return;
  const items = rates.map(r => {
    const meta = BANK_META[r.bank_id] || { name: r.bank_name, color: '#6B7280' };
    return `<span class="ticker-item"><span class="ticker-dot" style="background:${meta.color}"></span>${meta.name} Sell ৳${r.sell.toFixed(2)} · Buy ৳${r.buy.toFixed(2)}</span>`;
  }).join('');
  // Duplicated once so the scrolling marquee loops seamlessly.
  el.innerHTML = items + items;
}

export function renderInsightBanner() {
  const mi = computeMarketIntelligence();
  const el = document.getElementById('insightText');
  if (!el) return;

  if (!mi.hasHistory) {
    el.textContent = `Today's cross-bank spread is ৳${mi.todaySpread.toFixed(2)}. Historical comparison will appear once more days of data are collected.`;
    return;
  }

  if (mi.healthClass === 'tight') {
    el.innerHTML = `Today's spread of <b>৳${mi.todaySpread.toFixed(2)}</b> is narrower than the recent average of ৳${mi.avgSpread.toFixed(2)} — banks are closely matched, so the choice matters less than usual.`;
  } else if (mi.healthClass === 'favorable') {
    el.innerHTML = `Today's spread of <b>৳${mi.todaySpread.toFixed(2)}</b> is wider than the recent average of ৳${mi.avgSpread.toFixed(2)} — a good day to compare banks carefully, the difference is bigger than usual.`;
  } else {
    el.innerHTML = `Today's spread of <b>৳${mi.todaySpread.toFixed(2)}</b> is close to the recent average of ৳${mi.avgSpread.toFixed(2)}.`;
  }
}

export function renderModeBar() {
  document.querySelectorAll('.mode-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.mode === state.mode);
  });
}

export function renderBarCharts() {
  const rates = currentRates();
  const symbol = CURRENCY_META[state.currency]?.symbol || '';

  const buyBars = rates.map(r => ({
    label: r.bank_id,
    value: r.buy,
    color: (BANK_META[r.bank_id] || {}).color || '#6B7280',
  }));
  const sellBars = rates.map(r => ({
    label: r.bank_id,
    value: r.sell,
    color: (BANK_META[r.bank_id] || {}).color || '#6B7280',
  }));

  const buyEl = document.getElementById('buyBarChart');
  const sellEl = document.getElementById('sellBarChart');
  if (buyEl) buyEl.innerHTML = renderBarChart(buyBars, buyEl.clientWidth || 360);
  if (sellEl) sellEl.innerHTML = renderBarChart(sellBars, sellEl.clientWidth || 360);

  const activeTag = document.getElementById('barActiveTag');
  if (activeTag) activeTag.textContent = `Active for your mode: ${state.mode === 'send' ? 'Selling' : 'Buying'}`;

  const buyLegend = document.getElementById('buyBarLegend');
  const sellLegend = document.getElementById('sellBarLegend');
  const legendHtml = rates.map(r => {
    const meta = BANK_META[r.bank_id] || { name: r.bank_name, color: '#6B7280' };
    return `<span class="legend-item"><span class="legend-dot" style="background:${meta.color}"></span>${meta.name}</span>`;
  }).join('');
  if (buyLegend) buyLegend.innerHTML = legendHtml;
  if (sellLegend) sellLegend.innerHTML = legendHtml;
}

export function wireModeBar() {
  document.querySelectorAll('.mode-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      state.mode = btn.dataset.mode;
      window.renderAll();
    });
  });
}
