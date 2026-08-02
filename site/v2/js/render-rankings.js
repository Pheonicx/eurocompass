import { state, rankedRates, activeRate } from './state.js';
import { BANK_META, CONFIDENCE_META } from './config.js';
import { confDots } from './format.js';

const RANK_BADGES = ['gold', 'silver', 'bronze'];

export function renderRankings() {
  const rates = rankedRates();
  const el = document.getElementById('rankTableBody');
  const caption = document.getElementById('rankCaption');
  const sellHead = document.getElementById('rankSellHead');

  if (sellHead) {
    sellHead.textContent = state.mode === 'send' ? 'Sell' : 'Buy';
  }

  if (rates.length === 0) {
    el.innerHTML = `<tr><td colspan="7" class="hist-empty">No data available for ${state.currency}.</td></tr>`;
    caption.textContent = '';
    return;
  }

  caption.textContent = `${rates.length} bank${rates.length === 1 ? '' : 's'} · ranked by ${state.mode === 'send' ? 'TT selling rate, lowest first' : 'TT buying rate, highest first'}`;

  const bestRate = activeRate(rates[0]);

  el.innerHTML = rates.map((r, i) => {
    const meta = BANK_META[r.bank_id] || { name: r.bank_name, color: '#6B7280' };
    const badge = i < 3 ? `<span class="rank-badge ${RANK_BADGES[i]}">${i + 1}</span>` : `<span class="rank-badge">${i + 1}</span>`;
    const diff = Math.abs(activeRate(r) - bestRate);
    const diffCell = i === 0
      ? '<span class="diff-best">Best rate</span>'
      : `<span class="diff-pos">+${diff.toFixed(4)}</span>`;

    return `
      <tr class="${i === 0 ? 'row-best' : ''}">
        <td>${badge}</td>
        <td>
          <div class="bank-cell">
            <div class="bank-swatch" style="background:${meta.color}"></div>
            <span class="bank-name">${meta.name}</span>
            ${r.is_stale ? '<span class="stale-badge">Stale</span>' : ''}
          </div>
        </td>
        <td class="num">${r.buy.toFixed(4)}</td>
        <td class="num hl">${r.sell.toFixed(4)}</td>
        <td class="num">${r.student_rate && state.mode === 'send' ? r.student_rate.toFixed(4) : '—'}</td>
        <td class="num">${diffCell}</td>
        <td class="num">${confDots(r.confidence)}<span style="color:${(CONFIDENCE_META[r.confidence] || {}).color || 'inherit'};font-weight:600">${r.confidence}</span></td>
      </tr>`;
  }).join('');
}
