import { state } from './state.js';
import { computeMarketIntelligence, rankedBanks } from './calculations.js';

export function renderMarketIntelligence() {
  const mi = computeMarketIntelligence(state);
  const ranked = rankedBanks(state);
  const best = ranked[0];

  document.getElementById('gaugeNum').textContent = mi.opportunityScore;
  document.getElementById('gaugeArc').style.strokeDashoffset = 188.5 - (188.5 * (mi.opportunityScore / 100));

  const badge = document.getElementById('healthBadge');
  badge.className = 'health-badge ' + mi.healthClass;
  document.getElementById('healthLabel').textContent = mi.health;
  document.getElementById('healthNote').textContent = mi.hasHistory
    ? (mi.healthClass === 'favorable'
      ? `Today's spread of ৳${mi.todaySpread.toFixed(2)} is wider than the recent average of ৳${mi.avgSpread.toFixed(2)} — a good window to compare.`
      : mi.healthClass === 'tight'
        ? `Today's spread of ৳${mi.todaySpread.toFixed(2)} is narrower than usual (avg ৳${mi.avgSpread.toFixed(2)}) — banks are closely matched right now.`
        : `Today's spread of ৳${mi.todaySpread.toFixed(2)} is close to the recent average of ৳${mi.avgSpread.toFixed(2)}.`)
    : `Today's spread across banks is ৳${mi.todaySpread.toFixed(2)}. Historical comparison will appear once more days of data are collected.`;

  document.getElementById('confidenceNum').textContent = mi.confidence + '%';
  document.getElementById('confFill').style.width = mi.confidence + '%';

  document.getElementById('reasonsList').innerHTML = `
    <li>${best.name} offers the ${state.mode === 'buy' ? 'lowest TT selling' : 'highest TT buying'} rate across all ${state.banks.length} tracked banks.</li>
    <li>Today's cross-bank spread is ৳${mi.todaySpread.toFixed(2)}${mi.hasHistory ? `, vs a recent average of ৳${mi.avgSpread.toFixed(2)}` : ''}.</li>
    <li>${mi.confidence}% of tracked banks reported data in the latest collection run.</li>
  `;

  return mi;
}
