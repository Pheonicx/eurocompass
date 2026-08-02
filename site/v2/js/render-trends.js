import { state, rankedRates } from './state.js';
import { BANK_META } from './config.js';
import { computeMarketIntelligence } from './calculations.js';

export function renderTrends() {
  const mi = computeMarketIntelligence();
  const ranked = rankedRates();
  const best = ranked[0];

  const gaugeNum = document.getElementById('gaugeNum');
  const gaugeArc = document.getElementById('gaugeArc');
  if (gaugeNum && gaugeArc) {
    gaugeNum.textContent = mi.opportunityScore;
    gaugeArc.style.strokeDashoffset = 188.5 - (188.5 * (mi.opportunityScore / 100));
  }

  const badge = document.getElementById('healthBadge');
  if (badge) {
    badge.className = 'health-badge ' + mi.healthClass;
    document.getElementById('healthLabel').textContent = mi.health;
    document.getElementById('healthNote').textContent = mi.hasHistory
      ? (mi.healthClass === 'favorable'
        ? `Today's spread of ৳${mi.todaySpread.toFixed(2)} is wider than the recent average of ৳${mi.avgSpread.toFixed(2)} — a good window to compare.`
        : mi.healthClass === 'tight'
          ? `Today's spread of ৳${mi.todaySpread.toFixed(2)} is narrower than usual (avg ৳${mi.avgSpread.toFixed(2)}) — banks are closely matched right now.`
          : `Today's spread of ৳${mi.todaySpread.toFixed(2)} is close to the recent average of ৳${mi.avgSpread.toFixed(2)}.`)
      : `Today's spread across banks is ৳${mi.todaySpread.toFixed(2)}. Historical comparison will appear once more days of data are collected.`;
  }

  const confidenceNum = document.getElementById('confidenceNum');
  if (confidenceNum) {
    confidenceNum.textContent = mi.confidence + '%';
    document.getElementById('confFill').style.width = mi.confidence + '%';
  }

  const reasonsList = document.getElementById('reasonsList');
  if (reasonsList && best) {
    reasonsList.innerHTML = `
      <li>${BANK_META[best.bank_id]?.name || best.bank_name} offers the ${state.mode === 'send' ? 'lowest TT selling' : 'highest TT buying'} rate across all ${mi.rates.length} tracked banks.</li>
      <li>Today's cross-bank spread is ৳${mi.todaySpread.toFixed(2)}${mi.hasHistory ? `, vs a recent average of ৳${mi.avgSpread.toFixed(2)}` : ''}.</li>
      <li>${mi.confidence}% of tracked banks reported data in the latest collection run.</li>
    `;
  }

  return mi;
}
