import { state, currentRates, activeRate } from './state.js';
import { BANK_META } from './config.js';
import { fmtBDT } from './format.js';
import { computeForBank } from './calculations.js';

function fmtEUR(n) {
  return '€' + n.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 });
}

function renderFeeRows() {
  const el = document.getElementById('feeRows');
  el.innerHTML = state.calc.fees.map((f, i) => `
    <div class="fee-row" data-index="${i}">
      <input class="fee-label-input" type="text" value="${f.label}" placeholder="Fee name">
      <input class="fee-amount-input" type="number" value="${f.amount}" min="0">
      <select class="fee-currency-select">
        <option value="BDT" ${f.currency === 'BDT' ? 'selected' : ''}>BDT</option>
        <option value="EUR" ${f.currency === 'EUR' ? 'selected' : ''}>EUR</option>
        <option value="USD" ${f.currency === 'USD' ? 'selected' : ''}>USD</option>
      </select>
      <button class="fee-remove" data-index="${i}" title="Remove">×</button>
    </div>
  `).join('');

  el.querySelectorAll('.fee-label-input').forEach((input, i) => {
    input.addEventListener('input', e => { state.calc.fees[i].label = e.target.value; renderCalculator(); });
  });
  el.querySelectorAll('.fee-amount-input').forEach((input, i) => {
    input.addEventListener('input', e => { state.calc.fees[i].amount = parseFloat(e.target.value) || 0; renderCalculator(); });
  });
  el.querySelectorAll('.fee-currency-select').forEach((sel, i) => {
    sel.addEventListener('change', e => { state.calc.fees[i].currency = e.target.value; renderCalculator(); });
  });
  el.querySelectorAll('.fee-remove').forEach(btn => {
    btn.addEventListener('click', () => {
      state.calc.fees.splice(parseInt(btn.dataset.index), 1);
      renderCalculator();
    });
  });
}

export function renderCalculator() {
  const { amount, currency } = state.calc;
  const rates = (state.data?.rates_by_currency?.[currency]) || [];

  renderFeeRows();

  const resultTiles = document.getElementById('calcResultTiles');
  const bodyEl = document.getElementById('calcResults');
  const anyStudentRates = rates.some(r => r.student_rate);
  const toggle = document.getElementById('calcStudentToggle');
  if (toggle) {
    toggle.disabled = !anyStudentRates || state.mode !== 'send';
    document.getElementById('calcStudentWrap').classList.toggle('disabled', toggle.disabled);
  }

  if (!amount || amount <= 0 || rates.length === 0) {
    resultTiles.innerHTML = '';
    bodyEl.innerHTML = `<div class="hist-empty">Enter an amount to compare costs across banks.</div>`;
    return;
  }

  const costed = rates
    .map(r => ({ ...r, ...computeForBank(r, amount) }))
    .sort((a, b) => state.mode === 'send' ? a.totalBDT - b.totalBDT : b.totalBDT - a.totalBDT);

  const best = costed[0];
  const worst = costed[costed.length - 1];
  const bestMeta = BANK_META[best.bank_id] || { name: best.bank_name, color: '#6B7280' };
  const savings = Math.abs(worst.totalBDT - best.totalBDT);

  resultTiles.innerHTML = `
    <div class="result-tile">
      <div class="result-tile-label">Recommended bank</div>
      <div class="result-tile-value"><span class="tile-dot" style="background:${bestMeta.color}"></span>${bestMeta.name}</div>
      <div class="result-tile-sub">Rate ৳${best.rate.toFixed(2)}</div>
    </div>
    <div class="result-tile">
      <div class="result-tile-label">Total cost</div>
      <div class="result-tile-value">${fmtBDT(best.totalBDT)}</div>
      <div class="result-tile-sub">≈ ${fmtEUR(amount)} equivalent</div>
    </div>
    <div class="result-tile">
      <div class="result-tile-label">Fees + VAT</div>
      <div class="result-tile-value">${fmtBDT(best.feesTotal)}</div>
      <div class="result-tile-sub">of which VAT ${fmtBDT(best.feesVat)}</div>
    </div>
    <div class="result-tile">
      <div class="result-tile-label">You save</div>
      <div class="result-tile-value">${fmtBDT(savings)}</div>
      <div class="result-tile-sub">vs ${BANK_META[worst.bank_id]?.name || worst.bank_name}, all costs included</div>
    </div>
  `;

  bodyEl.innerHTML = `
    <div class="cost-note">
      Rates are live and real. Fees above are whatever you've entered — no bank currently publishes
      verified fee data, so treat the fee/VAT fields as your own estimate, same as the total here.
    </div>
    <table class="rank-table">
      <thead>
        <tr>
          <th>Bank</th>
          <th class="num">Rate</th>
          <th class="num">Total cost</th>
          <th class="num">${currency} equiv.</th>
          <th class="num">vs. cheapest</th>
        </tr>
      </thead>
      <tbody>
        ${costed.map((r, i) => {
          const meta = BANK_META[r.bank_id] || { name: r.bank_name, color: '#6B7280' };
          const diff = Math.abs(r.totalBDT - best.totalBDT);
          return `
            <tr class="${i === 0 ? 'row-best' : ''}">
              <td>
                <div class="bank-cell">
                  <div class="bank-swatch" style="background:${meta.color}"></div>
                  <span class="bank-name">${meta.name}</span>
                  ${r.usedStudentRate ? '<span class="student-tag">Student</span>' : ''}
                </div>
              </td>
              <td class="num">${r.rate.toFixed(4)}</td>
              <td class="num hl">${fmtBDT(r.totalBDT)}</td>
              <td class="num">${fmtEUR(amount)}</td>
              <td class="num">${i === 0 ? '<span class="diff-best">Cheapest</span>' : `<span class="diff-pos">+${fmtBDT(diff)}</span>`}</td>
            </tr>`;
        }).join('')}
      </tbody>
    </table>
    <div class="cost-note">For your entered amount plus all added costs, the gap between the cheapest and priciest bank is ${fmtBDT(savings)}.</div>
  `;
}

export function wireCalculator() {
  document.getElementById('calcAmount').addEventListener('input', e => {
    state.calc.amount = parseFloat(e.target.value) || 0;
    renderCalculator();
  });
  document.getElementById('calcCurrency').addEventListener('change', e => {
    state.calc.currency = e.target.value;
    renderCalculator();
  });
  document.getElementById('calcStudentToggle').addEventListener('change', e => {
    state.calc.useStudentRate = e.target.checked;
    renderCalculator();
  });
  document.getElementById('addFeeBtn').addEventListener('click', () => {
    state.calc.fees.push({ label: 'New fee', amount: 0, currency: 'BDT' });
    renderCalculator();
  });
  document.getElementById('vatPercent').addEventListener('input', e => {
    state.calc.vatPercent = parseFloat(e.target.value) || 0;
    renderCalculator();
  });
  document.getElementById('vatBasis').addEventListener('change', e => {
    state.calc.vatBasis = e.target.value;
    renderCalculator();
  });
}
