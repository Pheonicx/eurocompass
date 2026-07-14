import { state } from './state.js';
import { loadAll } from './dataLoader.js';
import { computeMarketIntelligence, rankedBanks } from './calculations.js';
import { renderTicker, renderRankTable, renderHero, renderChartTags, legendHtml } from './render-overview.js';
import { renderMarketIntelligence } from './render-market-intelligence.js';
import { renderBuySellCharts, renderHistChart } from './charts.js';
import { renderFeeRows, renderCalcAndCostTable } from './render-calculator.js';
import { renderForecast } from './render-forecast.js';

function fmtTimestamp(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  return 'Rates as of ' + d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' }) + ' · ' + d.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
}

function renderAll() {
  document.getElementById('updatedStamp').textContent = fmtTimestamp(state.generatedAt);
  renderTicker();
  document.getElementById('buyLegend').innerHTML = legendHtml();
  document.getElementById('sellLegend').innerHTML = legendHtml();
  document.getElementById('histLegend').innerHTML = legendHtml();

  renderRankTable();
  renderHero();
  renderChartTags();
  renderMarketIntelligence();
  renderCalcAndCostTable();
  renderBuySellCharts();
  renderHistChart();
  renderForecast();

  const mi = computeMarketIntelligence(state);
  const ranked = rankedBanks(state);
  document.getElementById('insightText').innerHTML = mi.hasHistory
    ? `Today's spread of <b>৳${mi.todaySpread.toFixed(2)}</b> is ${mi.todaySpread > mi.avgSpread ? 'wider' : 'narrower'} than the recent average of ৳${mi.avgSpread.toFixed(2)} — ${mi.healthClass === 'favorable' ? 'comparing before you transfer is worth more than usual right now.' : 'banks are closely matched, so the choice matters less than usual.'}`
    : `<b>${ranked[0].name}</b> currently has the best rate for ${state.mode === 'buy' ? 'sending money to Germany' : 'converting EUR to BDT'}. Historical comparison will appear as more data is collected.`;
}

function wireEvents() {
  document.getElementById('modeBuyBtn').addEventListener('click', () => {
    state.mode = 'buy';
    document.getElementById('modeBuyBtn').classList.add('active');
    document.getElementById('modeSellBtn').classList.remove('active');
    renderAll();
  });
  document.getElementById('modeSellBtn').addEventListener('click', () => {
    state.mode = 'sell';
    document.getElementById('modeSellBtn').classList.add('active');
    document.getElementById('modeBuyBtn').classList.remove('active');
    renderAll();
  });

  document.getElementById('calcAmount').addEventListener('input', renderCalcAndCostTable);
  document.getElementById('calcAmountCurrency').addEventListener('change', e => {
    state.amountCurrency = e.target.value;
    renderCalcAndCostTable();
  });

  document.getElementById('vatPercent').addEventListener('input', e => {
    state.vat.percent = e.target.value;
    renderCalcAndCostTable();
  });
  document.getElementById('vatBasis').addEventListener('change', e => {
    state.vat.basis = e.target.value;
    renderCalcAndCostTable();
  });

  document.getElementById('addFeeBtn').addEventListener('click', () => {
    state.fees.push({ label: "New cost", amount: 0, currency: "BDT" });
    renderFeeRows();
    renderCalcAndCostTable();
  });

  window.addEventListener('ec:recalc', renderCalcAndCostTable);

  document.getElementById('refreshBtn').addEventListener('click', () => location.reload());
}

async function init() {
  try {
    await loadAll(state);
    renderFeeRows();
    wireEvents();
    renderAll();
    document.getElementById('loadingScreen').style.display = 'none';
    document.getElementById('app').style.display = 'block';
  } catch (err) {
    console.error(err);
    document.getElementById('loadingScreen').style.display = 'none';
    document.getElementById('errorScreen').style.display = 'flex';
    document.getElementById('errorDetail').textContent = err.message || 'The data source did not respond.';
  }
}

init();
