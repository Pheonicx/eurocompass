import { state } from './state.js';
import { rankedBanks, computeForBank, toEURAmount, activeRate } from './calculations.js';

export function renderFeeRows() {
  document.getElementById('feeRows').innerHTML = state.fees.map((f, i) => `
    <div class="fee-row">
      <input type="text" value="${f.label}" data-i="${i}" data-field="label">
      <input type="number" value="${f.amount}" data-i="${i}" data-field="amount">
      <select data-i="${i}" data-field="currency">
        <option value="BDT" ${f.currency === 'BDT' ? 'selected' : ''}>BDT</option>
        <option value="EUR" ${f.currency === 'EUR' ? 'selected' : ''}>EUR</option>
        <option value="USD" ${f.currency === 'USD' ? 'selected' : ''}>USD</option>
      </select>
      <button class="fee-remove" data-i="${i}">×</button>
    </div>`).join('');

  document.querySelectorAll('#feeRows input, #feeRows select').forEach(el => {
    el.addEventListener('input', e => {
      state.fees[+e.target.dataset.i][e.target.dataset.field] = e.target.value;
      window.dispatchEvent(new CustomEvent('ec:recalc'));
    });
  });
  document.querySelectorAll('.fee-remove').forEach(btn => {
    btn.addEventListener('click', e => {
      state.fees.splice(+e.target.dataset.i, 1);
      renderFeeRows();
      window.dispatchEvent(new CustomEvent('ec:recalc'));
    });
  });
}

function getAmountEUR(bestBank) {
  const raw = document.getElementById('calcAmount').value.replace(/,/g, '');
  const amount = parseFloat(raw) || 0;
  const rate = activeRate(state, bestBank);
  return { amount, amountEUR: toEURAmount(amount, state.amountCurrency, rate) };
}

export function renderCalcAndCostTable() {
  const ranked = rankedBanks(state);
  const bestBankForConversion = ranked[0];
  const { amount, amountEUR } = getAmountEUR(bestBankForConversion);

  const results = ranked.map(b => ({ ...b, ...computeForBank(state, b, amountEUR) }));
  const bestR = results[0], worstR = results[results.length - 1];
  const diffBDT = state.mode === 'buy' ? (worstR.totalBDT - bestR.totalBDT) : (bestR.totalBDT - worstR.totalBDT);

  document.getElementById('calcAmountLabel').textContent = state.mode === 'buy' ? 'Amount to send' : 'Amount to convert';
  document.getElementById('calcTitle').textContent = state.mode === 'buy' ? 'Transfer calculator' : 'Conversion calculator';
  document.getElementById('calcCaption').textContent = state.mode === 'buy'
    ? 'Estimated cost, including fees and VAT, based on current TT selling rates'
    : 'Estimated BDT received, after fees and VAT, based on current TT buying rates';

  if (state.amountCurrency !== 'EUR') {
    document.getElementById('calcAmountHint').textContent = `≈ €${Math.round(amountEUR).toLocaleString()} at ${bestBankForConversion.name}'s rate (৳${activeRate(state, bestBankForConversion).toFixed(2)})`;
  } else {
    document.getElementById('calcAmountHint').textContent = 'Typical semester tuition + living cost transfer';
  }

  document.getElementById('calcResults').innerHTML = `
    <div class="result-tile accent">
      <div class="result-tile-label">Recommended bank</div>
      <div class="result-tile-value accent-text"><span class="tile-dot" style="background:${bestR.color};"></span>${bestR.name}</div>
      <div class="result-tile-sub">Rate ৳${bestR.rate.toFixed(2)}</div>
    </div>
    <div class="result-tile">
      <div class="result-tile-label">${state.mode === 'buy' ? 'Total cost' : 'Net you receive'}</div>
      <div class="result-tile-value">৳${Math.round(bestR.totalBDT).toLocaleString()}</div>
      <div class="result-tile-sub">≈ €${Math.round(bestR.totalEUR).toLocaleString()} equivalent</div>
    </div>
    <div class="result-tile">
      <div class="result-tile-label">Fees + VAT</div>
      <div class="result-tile-value">৳${Math.round(bestR.feesBDT).toLocaleString()}</div>
      <div class="result-tile-sub">of which VAT ৳${Math.round(bestR.feesVat).toLocaleString()}</div>
    </div>
    <div class="result-tile">
      <div class="result-tile-label">${state.mode === 'buy' ? 'You save' : 'You gain'}</div>
      <div class="result-tile-value" style="color:var(--success);">৳${Math.round(diffBDT).toLocaleString()}</div>
      <div class="result-tile-sub">vs. ${worstR.name}, all costs included</div>
    </div>`;

  document.getElementById('costSectionTitle').textContent = state.mode === 'buy' ? 'Cost by bank' : 'BDT received, by bank';
  document.getElementById('costSectionCaption').textContent = state.mode === 'buy'
    ? 'Your entered amount plus all added costs, at every bank'
    : 'Your entered amount minus all added costs, at every bank';
  document.getElementById('costHead').innerHTML = `<tr>
    <th style="width:52px;">Rank</th><th>Bank</th><th class="num">Rate</th>
    <th class="num">${state.mode === 'buy' ? 'Total cost' : 'Net received'}</th><th class="num">EUR equiv.</th><th class="num">${state.mode === 'buy' ? 'vs. cheapest' : 'vs. best'}</th></tr>`;
  document.getElementById('costBody').innerHTML = results.map((b, i) => {
    const d = state.mode === 'buy' ? Math.round(b.totalBDT - bestR.totalBDT) : Math.round(bestR.totalBDT - b.totalBDT);
    const diffCell = i === 0 ? `<span class="diff-best">${state.mode === 'buy' ? 'Cheapest' : 'Best'}</span>` : `<span class="diff-pos">${state.mode === 'buy' ? '+' : '-'}৳${Math.abs(d).toLocaleString()}</span>`;
    return `<tr class="${i === 0 ? 'row-best' : ''}">
      <td><span class="rank-badge ${i === 0 ? 'gold' : i === 1 ? 'silver' : i === 2 ? 'bronze' : ''}">${i + 1}</span></td>
      <td><div class="bank-cell"><div class="bank-swatch" style="background:${b.color};"></div><span class="bank-name">${b.name}</span></div></td>
      <td class="num">৳${b.rate.toFixed(2)}</td>
      <td class="num">৳${Math.round(b.totalBDT).toLocaleString()}</td>
      <td class="num">€${Math.round(b.totalEUR).toLocaleString()}</td>
      <td class="num">${diffCell}</td>
    </tr>`;
  }).join('');
  const spreadNote = Math.round(Math.abs(results[results.length - 1].totalBDT - bestR.totalBDT));
  document.getElementById('costNote').textContent = state.mode === 'buy'
    ? `For your entered amount plus all added costs, the gap between the cheapest and priciest bank is ৳${spreadNote.toLocaleString()}.`
    : `For your entered amount minus all added costs, the gap between the best and weakest bank is ৳${spreadNote.toLocaleString()}.`;
}
