import { state } from './state.js';
import { BANK_META, CONFIDENCE_META } from './config.js';
import { fmtBDT, fmtAmount, confDots } from './format.js';

export function renderRecommendations() {
  const recs = state.data?.recommendations || [];
  const el = document.getElementById('recommendationsGrid');

  if (recs.length === 0) {
    el.innerHTML = `<div class="hist-empty">No recommendations available right now.</div>`;
    return;
  }

  el.innerHTML = recs.map(rec => {
    const meta = BANK_META[rec.recommended_bank_id] || { name: rec.recommended_bank_name, color: '#6B7280' };
    const conf = CONFIDENCE_META[rec.confidence] || { label: rec.confidence, color: '#8B8578' };
    const isCurrentCurrency = rec.currency === state.currency;

    const altRows = rec.alternatives.slice(0, 3).map(a => `
      <div class="rec-alt-row">
        <span>${BANK_META[a.bank_id]?.name || a.bank_name}</span>
        <span class="rec-alt-diff">+${fmtBDT(a.extra_cost_vs_recommended_bdt)}</span>
      </div>
    `).join('');

    return `
      <div class="card rec-card ${isCurrentCurrency ? 'rec-card-active' : ''}">
        <div class="rec-seal">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none"><path d="M9 12l2 2 4-4M12 3l2.4 1.4L17 4l.6 2.6L20 8l-1.4 2.4L20 13l-2.4 1L17 17l-2.6-.6L12 18l-2.4-1.4L7 17l-.6-2.6L4 13l1.4-2.4L4 8l2.4-1L7 4l2.6.6L12 3Z" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round" stroke-linecap="round"/></svg>
          Validated recommendation
        </div>
        <div class="rec-card-head">
          <span class="rec-amount">${fmtAmount(rec.currency, rec.requested_amount)}</span>
          <span class="rec-confidence" style="color:${conf.color}">${confDots(rec.confidence)}${conf.label}</span>
        </div>
        <div class="rec-bank-row">
          <div class="best-dot" style="background:${meta.color}"></div>
          <span class="rec-bank-name">${meta.name}</span>
        </div>
        <div class="rec-total">${fmtBDT(rec.total_cost_bdt)}</div>
        <div class="rec-savings">Saves ${fmtBDT(rec.estimated_savings_vs_most_expensive_bdt)} vs the most expensive option</div>
        <p class="rec-explanation">${rec.explanation}</p>
        <div class="rec-alts">
          <div class="rec-alts-label">Other options considered</div>
          ${altRows}
        </div>
      </div>
    `;
  }).join('');
}
