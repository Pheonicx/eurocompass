import { state } from './state.js';
import { loadAll } from './dataLoader.js';
import { renderHero } from './render-hero.js';
import { renderRankings } from './render-rankings.js';
import { renderRecommendations } from './render-recommendations.js';
import { renderCalculator, wireCalculator } from './render-calculator.js';
import { renderTrends } from './render-trends.js';
import { renderHistory } from './render-history.js';
import { renderStudentRates } from './render-student.js';
import { renderForecast } from './render-forecast.js';
import { renderTicker, renderInsightBanner, renderModeBar, renderBarCharts, renderTrustStrip, wireModeBar } from './render-overview.js';

function fmtTimestamp(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  return 'Rates as of ' + d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' }) +
    ' · ' + d.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
}

function renderAll() {
  document.getElementById('updatedStamp').textContent = fmtTimestamp(state.data?.generated_at);
  renderTrustStrip();
  renderTicker();
  renderInsightBanner();
  renderModeBar();
  renderHero();
  renderRankings();
  renderTrends();
  renderBarCharts();
  renderRecommendations();
  renderCalculator();
  renderStudentRates();
  renderForecast();
  renderHistory();
}
window.renderAll = renderAll; // mode-bar clicks live in render-overview.js and need to trigger a full re-render

function wireCurrencyToggle() {
  document.querySelectorAll('.currency-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      state.currency = btn.dataset.currency;
      document.querySelectorAll('.currency-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      renderAll();
    });
  });
}

async function init() {
  try {
    await loadAll(state);
    wireCurrencyToggle();
    wireModeBar();
    wireCalculator();
    renderAll();
    document.getElementById('loadingScreen').style.display = 'none';
    document.getElementById('app').style.display = 'block';
  } catch (err) {
    console.error(err);
    document.getElementById('loadingScreen').style.display = 'none';
    document.getElementById('errorScreen').style.display = 'flex';
    document.getElementById('errorDetail').textContent = err.message || 'The data source did not respond.';
  }

  document.getElementById('refreshBtn').addEventListener('click', () => location.reload());
}

init();
