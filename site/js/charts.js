import { state } from './state.js';
import { activeRate, buildForecast } from './calculations.js';

let buyChart, sellChart, histChart, forecastChart;

const chartDefaults = {
  responsive: true, maintainAspectRatio: false, animation: { duration: 700, easing: 'easeOutQuart' },
  layout: { padding: { top: 26, right: 14, left: 4, bottom: 0 } },
  plugins: { legend: { display: false }, tooltip: { backgroundColor: '#14213D', padding: 10, titleFont: { family: 'Inter' }, bodyFont: { family: 'JetBrains Mono' } } },
  scales: { x: { grid: { display: false }, ticks: { font: { family: 'Inter', size: 11 }, color: '#5B6472' } }, y: { grid: { color: '#F3ECDD' }, ticks: { font: { family: 'JetBrains Mono', size: 11 }, color: '#8B8578', maxTicksLimit: 5 } } }
};

// Draws the exact rate value above each bar, so even a visually zoomed
// (non-zero-based) axis never leaves the viewer guessing at the number.
// Clamps the label's y-position so it can't collide with the chart's own
// top edge or axis labels when the tallest bar is close to the max.
const valueLabelPlugin = {
  id: 'valueLabel',
  afterDatasetsDraw(chart) {
    const { ctx, chartArea } = chart;
    const meta = chart.getDatasetMeta(0);
    ctx.save();
    ctx.font = '600 11px JetBrains Mono, monospace';
    ctx.fillStyle = '#14213D';
    meta.data.forEach((bar, i) => {
      const val = chart.data.datasets[0].data[i];
      const label = '৳' + val.toFixed(2);

      // Keep the label inside the chart's plotting area horizontally,
      // so bars near the left/right edge don't get their labels clipped.
      const textWidth = ctx.measureText(label).width;
      let x = bar.x;
      ctx.textAlign = 'center';
      if (x - textWidth / 2 < chartArea.left) { x = chartArea.left + textWidth / 2; ctx.textAlign = 'center'; }
      if (x + textWidth / 2 > chartArea.right) { x = chartArea.right - textWidth / 2; ctx.textAlign = 'center'; }

      const y = Math.max(bar.y - 8, chartArea.top + 12);
      ctx.fillText(label, x, y);
    });
    ctx.restore();
  }
};

// Zooms the y-axis into the actual data range instead of starting at 0,
// which is what was making every bank's bar look almost identical height
// even though the rates genuinely differ.
function zoomedAxis(values) {
  const min = Math.min(...values), max = Math.max(...values);
  const range = max - min;
  const pad = Math.max(range * 0.6, 0.4);
  return { min: +(min - pad).toFixed(2), max: +(max + pad).toFixed(2) };
}

export function renderBuySellCharts() {
  const buyVals = state.banks.map(b => b.buy);
  const sellVals = state.banks.map(b => b.sell);
  const buyAxis = zoomedAxis(buyVals);
  const sellAxis = zoomedAxis(sellVals);

  const buyOptions = JSON.parse(JSON.stringify(chartDefaults));
  buyOptions.scales.y.min = buyAxis.min;
  buyOptions.scales.y.max = buyAxis.max;
  buyOptions.plugins.legend.display = false;

  const sellOptions = JSON.parse(JSON.stringify(chartDefaults));
  sellOptions.scales.y.min = sellAxis.min;
  sellOptions.scales.y.max = sellAxis.max;

  if (buyChart) buyChart.destroy();
  if (sellChart) sellChart.destroy();

  buyChart = new Chart(document.getElementById('buyChart'), {
    type: 'bar',
    data: { labels: state.banks.map(b => b.key.slice(0, 2)), datasets: [{ data: buyVals, backgroundColor: state.banks.map(b => b.color), borderRadius: 5, maxBarThickness: 32 }] },
    options: buyOptions,
    plugins: [valueLabelPlugin],
  });
  sellChart = new Chart(document.getElementById('sellChart'), {
    type: 'bar',
    data: { labels: state.banks.map(b => b.key.slice(0, 2)), datasets: [{ data: sellVals, backgroundColor: state.banks.map(b => b.color), borderRadius: 5, maxBarThickness: 32 }] },
    options: sellOptions,
    plugins: [valueLabelPlugin],
  });
}

function fmtDateShort(iso) {
  const d = new Date(iso + 'T00:00:00');
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

// Formats a Date object as a YYYY-MM-DD key using its LOCAL calendar date,
// never toISOString() (which converts to UTC and silently shifts the date
// backward by a day for any timezone ahead of UTC, e.g. Bangladesh/UTC+6).
function localDateKey(d) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

export function renderHistChart() {
  const histSource = state.mode === 'buy' ? state.sellHistByBank : state.buyHistByBank;
  const dateSet = new Set();
  state.banks.forEach(b => (histSource[b.key] || []).forEach(d => dateSet.add(d.date)));
  const dates = [...dateSet].sort().slice(-14);

  document.getElementById('histEmpty').style.display = dates.length < 2 ? 'block' : 'none';
  document.getElementById('histCaption').textContent = dates.length
    ? `${state.mode === 'buy' ? 'TT selling' : 'TT buying'} rate, all banks compared — ${fmtDateShort(dates[0])} to ${fmtDateShort(dates[dates.length - 1])}`
    : 'Not enough historical data yet';

  const datasets = state.banks.map(b => {
    const byDate = {}; (histSource[b.key] || []).forEach(d => byDate[d.date] = d.value);
    return {
      label: b.name, data: dates.map(d => byDate[d] !== undefined ? byDate[d] : null), spanGaps: true,
      borderColor: b.color, backgroundColor: 'transparent', fill: false, tension: 0.35, pointRadius: 0, borderWidth: 2.25,
      pointHoverRadius: 5, pointHoverBackgroundColor: b.color, pointHoverBorderColor: '#fff', pointHoverBorderWidth: 2
    };
  });
  if (histChart) histChart.destroy();
  histChart = new Chart(document.getElementById('histChart'), { type: 'line', data: { labels: dates.map(fmtDateShort), datasets }, options: chartDefaults });
}

export function renderForecastChart() {
  const canvas = document.getElementById('forecastChart');
  const emptyEl = document.getElementById('forecastEmpty');
  const forecasts = state.banks.map(b => ({ bank: b, f: buildForecast(state, b.key) }));
  const anyValid = forecasts.some(x => x.f !== null);

  emptyEl.style.display = anyValid ? 'none' : 'block';
  canvas.style.display = anyValid ? 'block' : 'none';
  if (!anyValid) { if (forecastChart) { forecastChart.destroy(); forecastChart = null; } return; }

  // Build a shared date axis: history dates + forecast dates
  const sample = forecasts.find(x => x.f !== null).f;
  const historyDates = sample.history.map(d => d.date);
  const forecastDateLabels = sample.forecast.map(d => localDateKey(d.date));
  const allDateLabels = [...historyDates, ...forecastDateLabels];

  const datasets = [];
  forecasts.forEach(({ bank, f }) => {
    if (!f) return;
    const histByDate = {}; f.history.forEach(d => histByDate[d.date] = d.value);
    const historyData = historyDates.map(d => histByDate[d]);
    const forecastData = new Array(historyDates.length - 1).fill(null)
      .concat([f.history[f.history.length - 1].value])
      .concat(f.forecast.map(p => p.value));

    datasets.push({
      label: bank.name + ' (history)', data: historyData.concat(new Array(f.forecast.length).fill(null)),
      borderColor: bank.color, backgroundColor: 'transparent', fill: false, tension: 0.3, pointRadius: 0, borderWidth: 2.25,
    });
    datasets.push({
      label: bank.name + ' (forecast)', data: forecastData,
      borderColor: bank.color, backgroundColor: 'transparent', fill: false, tension: 0.3, pointRadius: 0, borderWidth: 2.25,
      borderDash: [5, 4],
    });
  });

  const labels = allDateLabels.map(d => {
    const dt = typeof d === 'string' ? new Date(d + 'T00:00:00') : d;
    return dt.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  });

  const options = JSON.parse(JSON.stringify(chartDefaults));
  options.plugins.legend.display = false;

  if (forecastChart) forecastChart.destroy();
  forecastChart = new Chart(canvas, { type: 'line', data: { labels, datasets }, options });
}
