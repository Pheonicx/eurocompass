import { currentRates } from './state.js';
import { BANK_META } from './config.js';

export function renderStudentRates() {
  const rates = currentRates().filter(r => r.student_rate);
  const el = document.getElementById('studentTableBody');
  if (!el) return;

  if (rates.length === 0) {
    el.innerHTML = `<tr><td colspan="3" class="hist-empty">No banks are currently publishing a distinct student file rate for this currency.</td></tr>`;
    return;
  }

  const sorted = [...rates].sort((a, b) => a.student_rate - b.student_rate);

  el.innerHTML = sorted.map((r, i) => {
    const meta = BANK_META[r.bank_id] || { name: r.bank_name, color: '#6B7280' };
    const savingsPerUnit = r.sell - r.student_rate;
    return `
      <tr class="${i === 0 ? 'row-best' : ''}">
        <td>
          <div class="bank-cell">
            <div class="bank-swatch" style="background:${meta.color}"></div>
            <span class="bank-name">${meta.name}</span>
          </div>
        </td>
        <td class="num hl">${r.student_rate.toFixed(4)}</td>
        <td class="num">${savingsPerUnit > 0 ? `<span class="diff-best">${savingsPerUnit.toFixed(4)} cheaper per unit</span>` : '—'}</td>
      </tr>`;
  }).join('');
}
