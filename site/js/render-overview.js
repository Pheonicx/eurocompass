import { state } from './state.js';
import { activeRate, rankedBanks } from './calculations.js';

function staleBadge(b) {
  if (!b.rateDate) return '';
  if (!b.isStale) return '';
  return `<span class="stale-badge" title="This bank's rate is from ${b.rateDate}, not today">from ${b.rateDate}</span>`;
}

export function legendHtml() {
  return state.banks.map(b => `<span class="legend-item"><span class="legend-dot" style="background:${b.color};"></span>${b.name}</span>`).join('');
}

export function renderTicker() {
  document.getElementById('tickerTrack').innerHTML = (function () {
    const items = state.banks.map(b => `<span class="ticker-item"><span class="ticker-dot" style="background:${b.color};"></span><b>${b.name}</b>Sell ৳${b.sell.toFixed(2)} · Buy ৳${b.buy.toFixed(2)}</span>`).join('');
    return items + items;
  })();
}

export function renderRankTable() {
  const ranked = rankedBanks(state);
  const bestVal = activeRate(state, ranked[0]);
  document.getElementById('rankHead').innerHTML = `<tr>
    <th style="width:52px;padding-left:28px;">Rank</th><th>Bank</th>
    <th class="num ${state.mode === 'sell' ? 'hl' : ''}">Buy</th>
    <th class="num ${state.mode === 'buy' ? 'hl' : ''}">Sell</th>
    <th class="num" style="padding-right:28px;">Difference</th></tr>`;
  document.getElementById('rankBody').innerHTML = ranked.map((b, i) => {
    const val = activeRate(state, b);
    const diff = state.mode === 'buy' ? (val - bestVal).toFixed(2) : (bestVal - val).toFixed(2);
    const badgeClass = i === 0 ? 'gold' : i === 1 ? 'silver' : i === 2 ? 'bronze' : '';
    const diffCell = i === 0 ? '<span class="diff-best">Best rate</span>' : `<span class="diff-pos">+৳${diff}</span>`;
    return `<tr class="${i === 0 ? 'row-best' : ''}">
      <td style="padding-left:28px;"><span class="rank-badge ${badgeClass}">${i + 1}</span></td>
      <td><div class="bank-cell"><div class="bank-swatch" style="background:${b.color};"></div><span class="bank-name">${b.name}</span>${staleBadge(b)}</div></td>
      <td class="num ${state.mode === 'sell' ? 'hl' : ''}">৳${b.buy.toFixed(2)}</td>
      <td class="num ${state.mode === 'buy' ? 'hl' : ''}">৳${b.sell.toFixed(2)}</td>
      <td class="num" style="padding-right:28px;">${diffCell}</td>
    </tr>`;
  }).join('');
  const dateLabel = state.generatedAt ? new Date(state.generatedAt).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' }) : '—';
  document.getElementById('rankCaption').textContent = `${dateLabel} · ranked by ${state.mode === 'buy' ? 'lowest TT selling rate' : 'highest TT buying rate'}`;
}

function countUp(el, target, decimals, duration) {
  const start = performance.now();
  function step(now) {
    const p = Math.min((now - start) / duration, 1); const eased = 1 - Math.pow(1 - p, 3); const val = target * eased;
    el.textContent = decimals ? val.toFixed(decimals) : Math.round(val).toLocaleString();
    if (p < 1) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
}

export function renderHero() {
  const ranked = rankedBanks(state);
  const b0 = ranked[0], b1 = ranked[1];
  const rate0 = activeRate(state, b0), rate1 = activeRate(state, b1);
  const diff = Math.abs(rate1 - rate0).toFixed(2);

  document.getElementById('modeChip').textContent = state.mode === 'buy' ? 'Sending to Germany' : 'Converting to BDT';
  document.getElementById('bestDot').style.background = b0.color;
  document.getElementById('bestName').textContent = b0.name;
  document.getElementById('bestStale').innerHTML = staleBadge(b0);
  document.getElementById('rateUnitLabel').textContent = state.mode === 'buy' ? 'TT selling rate, per EUR' : 'TT buying rate, per EUR';
  document.getElementById('compareText').innerHTML = state.mode === 'buy'
    ? `৳<b>${diff}</b> better than the 2nd-best rate today — <b>${b1.name}</b> at ৳${rate1.toFixed(2)}.`
    : `৳<b>${diff}</b> more BDT per EUR than the 2nd-best rate — <b>${b1.name}</b> at ৳${rate1.toFixed(2)}.`;

  const hist = (state.mode === 'buy' ? state.sellHistByBank : state.buyHistByBank)[b0.key] || [];
  const last7 = hist.slice(-7);
  document.getElementById('sparkEmpty').style.display = last7.length < 2 ? 'block' : 'none';
  document.getElementById('sparkSvg').style.display = last7.length < 2 ? 'none' : 'block';
  if (last7.length >= 2) {
    const vals = last7.map(d => d.value);
    const min = Math.min(...vals), max = Math.max(...vals), range = (max - min) || 1;
    const w = 240, h = 44, pad = 4;
    const pts = vals.map((v, i) => { const x = (i / (vals.length - 1)) * w; const y = h - pad - ((v - min) / range) * (h - pad * 2); return `${x.toFixed(1)},${y.toFixed(1)}`; }).join(' ');
    document.getElementById('sparkSvg').innerHTML = `<polyline points="${pts}" fill="none" stroke="${b0.color}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>`;
    const delta = (vals[vals.length - 1] - vals[0]).toFixed(2);
    const favorable = state.mode === 'buy' ? delta <= 0 : delta >= 0;
    const el = document.getElementById('sparkDelta');
    el.textContent = (delta >= 0 ? '+' : '') + '৳' + delta;
    el.style.color = favorable ? '#3F7A57' : '#B23A63';
    document.getElementById('sparkLabel').textContent = `${b0.name.split(' ')[0]}'s own ${state.mode === 'buy' ? 'sell' : 'buy'} rate, past ${last7.length} days`;
    document.getElementById('chipRow').innerHTML = state.mode === 'buy'
      ? `<span class="chip">Lowest sell rate of ${state.banks.length}</span><span class="chip">${favorable ? 'Improving' : 'Rising'} trend, still cheapest</span>`
      : `<span class="chip">Highest buy rate of ${state.banks.length}</span><span class="chip">${favorable ? 'Improving' : 'Softening'} trend, still best</span>`;
  } else {
    document.getElementById('sparkDelta').textContent = '—';
    document.getElementById('chipRow').innerHTML = state.mode === 'buy'
      ? `<span class="chip">Lowest sell rate of ${state.banks.length}</span>`
      : `<span class="chip">Highest buy rate of ${state.banks.length}</span>`;
  }

  document.getElementById('heroRate').textContent = '0.00';
  countUp(document.getElementById('heroRate'), rate0, 2, 700);
}

export function renderChartTags() {
  document.getElementById('buyActiveTag').style.display = state.mode === 'sell' ? 'inline-block' : 'none';
  document.getElementById('sellActiveTag').style.display = state.mode === 'buy' ? 'inline-block' : 'none';
}
