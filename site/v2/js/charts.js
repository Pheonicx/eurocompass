// Hand-rolled SVG charts. No external chart library dependency — the
// data shape here (a handful of series, a few dozen points each)
// doesn't need one, and it keeps the dashboard's only external
// dependency down to the Google Fonts stylesheet.

// Standard "nice numbers" axis algorithm: picks a clean step size
// (1, 2, 2.5, 5, or 10 x a power of 10) and snaps the given range
// outward to multiples of it, so gridlines land on round values like
// 142.00/143.00 instead of whatever raw min/max division produces.
function niceAxisBounds(rawMin, rawMax, targetTicks = 4) {
  const range = Math.max(rawMax - rawMin, 0.0001);
  const roughStep = range / targetTicks;
  const magnitude = Math.pow(10, Math.floor(Math.log10(roughStep)));
  const residual = roughStep / magnitude;

  let niceResidual;
  if (residual < 1.5) niceResidual = 1;
  else if (residual < 3) niceResidual = 2;
  else if (residual < 7) niceResidual = 5;
  else niceResidual = 10;

  const step = niceResidual * magnitude;
  const min = Math.floor(rawMin / step) * step;
  const max = Math.ceil(rawMax / step) * step;
  return { min, max, step };
}

function pathFor(points, width, height, min, max, padY = 6) {
  if (points.length === 0) return '';
  const range = Math.max(max - min, 0.0001);
  const stepX = points.length > 1 ? width / (points.length - 1) : 0;
  return points
    .map((p, i) => {
      const x = i * stepX;
      const y = padY + (height - padY * 2) * (1 - (p - min) / range);
      return `${i === 0 ? 'M' : 'L'}${x.toFixed(2)},${y.toFixed(2)}`;
    })
    .join(' ');
}

// Catmull-Rom to cubic-bezier conversion — a smooth curve through every
// point exactly (not an approximation), used for the history/forecast
// charts so multi-week trends read as a trend rather than a jagged
// zigzag. dashFrom, if given, splits the path into a solid prefix and
// a dashed suffix (for forecast charts: real history solid, projected
// continuation dashed).
function smoothPath(coords, dashFrom = null) {
  if (coords.length < 2) return { solid: '', dashed: '' };
  if (coords.length === 2) {
    const d = `M${coords[0].x},${coords[0].y} L${coords[1].x},${coords[1].y}`;
    return dashFrom === 0 ? { solid: '', dashed: d } : { solid: d, dashed: '' };
  }

  const segments = [];
  for (let i = 0; i < coords.length - 1; i++) {
    const p0 = coords[i - 1] || coords[i];
    const p1 = coords[i];
    const p2 = coords[i + 1];
    const p3 = coords[i + 2] || p2;
    const cp1x = p1.x + (p2.x - p0.x) / 6;
    const cp1y = p1.y + (p2.y - p0.y) / 6;
    const cp2x = p2.x - (p3.x - p1.x) / 6;
    const cp2y = p2.y - (p3.y - p1.y) / 6;
    segments.push({ from: i, cp1x, cp1y, cp2x, cp2y, to: p2 });
  }

  let solid = `M${coords[0].x},${coords[0].y} `;
  let dashed = '';
  segments.forEach(s => {
    const piece = `C${s.cp1x.toFixed(2)},${s.cp1y.toFixed(2)} ${s.cp2x.toFixed(2)},${s.cp2y.toFixed(2)} ${s.to.x.toFixed(2)},${s.to.y.toFixed(2)} `;
    if (dashFrom !== null && s.from >= dashFrom) {
      if (!dashed) dashed = `M${coords[s.from].x},${coords[s.from].y} `;
      dashed += piece;
    } else {
      solid += piece;
    }
  });
  return { solid, dashed };
}

// A single-series sparkline for the hero card: just the shape and a
// subtle fill, no axes or labels — the delta figure next to it (built
// by the caller from the same points) carries the actual number.
export function renderSparkline(points, color, valueField = 'sell') {
  const width = 320, height = 44;
  if (points.length < 2) {
    return `<div class="spark-empty">Not enough history yet for a trend line</div>`;
  }
  const values = points.map(p => p[valueField]);
  const min = Math.min(...values), max = Math.max(...values);
  const linePath = pathFor(values, width, height, min, max);
  const fillPath = `${linePath} L${width},${height} L0,${height} Z`;

  return `
    <svg class="spark-svg" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none">
      <path d="${fillPath}" fill="${color}" opacity="0.08" stroke="none"></path>
      <path d="${linePath}" fill="none" stroke="${color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"></path>
    </svg>`;
}

function fmtDateShort(d) {
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

// A multi-bank historical line chart with a real Y axis, X axis date
// labels, hover tooltips, and smoothed curves.
export function renderHistoryChart(seriesByBank, valueField = 'sell', containerWidth = 760) {
  const width = containerWidth, height = 280;
  const padL = 52, padR = 16, padT = 16, padB = 32;
  const plotW = width - padL - padR, plotH = height - padT - padB;

  const allPoints = seriesByBank.flatMap(s => s.points);
  if (allPoints.length === 0) {
    return `<div class="hist-empty">Not enough historical data yet — check back after a few collection cycles.</div>`;
  }

  const allVals = allPoints.map(p => p[valueField]);
  const rawMin = Math.min(...allVals), rawMax = Math.max(...allVals);
  const pad = Math.max((rawMax - rawMin) * 0.15, 0.3);
  const { min, max, step } = niceAxisBounds(rawMin - pad, rawMax + pad);

  const dateSet = new Set();
  seriesByBank.forEach(s => s.points.forEach(p => dateSet.add(p.collected_at.slice(0, 10))));
  const dates = [...dateSet].sort();

  const tickCount = Math.round((max - min) / step);
  const yGridLines = Array.from({ length: tickCount + 1 }, (_, i) => {
    const val = min + step * i;
    const y = padT + plotH * (1 - i / tickCount);
    return `<line x1="${padL}" y1="${y}" x2="${width - padR}" y2="${y}" stroke="var(--border, #EAE3D6)" stroke-width="1"></line>
            <text x="${padL - 8}" y="${y + 4}" text-anchor="end" font-family="JetBrains Mono, monospace" font-size="10.5" fill="var(--text-muted, #8B8578)">${val.toFixed(2)}</text>`;
  }).join('');

  const xLabelStep = Math.max(Math.ceil(dates.length / 6), 1);
  const xLabels = dates.map((d, i) => {
    if (i % xLabelStep !== 0 && i !== dates.length - 1) return '';
    const x = padL + (dates.length > 1 ? (plotW * i) / (dates.length - 1) : plotW / 2);
    return `<text x="${x}" y="${height - 10}" text-anchor="middle" font-family="Inter, sans-serif" font-size="11" fill="var(--text-secondary, #5B6472)">${fmtDateShort(new Date(d))}</text>`;
  }).join('');

  const seriesSvg = seriesByBank.map(s => {
    const byDate = {};
    s.points.forEach(p => { byDate[p.collected_at.slice(0, 10)] = p[valueField]; });

    const coords = dates
      .map((d, i) => {
        if (byDate[d] === undefined) return null;
        const x = padL + (dates.length > 1 ? (plotW * i) / (dates.length - 1) : plotW / 2);
        const y = padT + plotH * (1 - (byDate[d] - min) / (max - min));
        return { x, y, value: byDate[d], date: d };
      })
      .filter(Boolean);

    if (coords.length === 0) return '';

    const { solid } = smoothPath(coords);
    const dots = coords
      .map(
        c => `<circle cx="${c.x.toFixed(2)}" cy="${c.y.toFixed(2)}" r="7" fill="transparent" stroke="none">
                <title>${s.bank_name}: ${c.value.toFixed(4)} BDT on ${fmtDateShort(new Date(c.date))}</title>
              </circle>`
      )
      .join('');

    return `<path d="${solid}" fill="none" stroke="${s.color}" stroke-width="2.25" stroke-linecap="round" stroke-linejoin="round"></path>${dots}`;
  }).join('');

  return `
    <svg viewBox="0 0 ${width} ${height}" style="width:100%;height:auto;display:block;">
      ${yGridLines}
      ${xLabels}
      ${seriesSvg}
    </svg>`;
}

// A forecast chart: real history as a solid smoothed line, the
// straight-line projection as a dashed continuation — visually honest
// about which part is observed and which part is a labeled guess.
export function renderForecastChart(seriesByBank, forecastByBank, containerWidth = 760) {
  const width = containerWidth, height = 260;
  const padL = 52, padR = 16, padT = 16, padB = 32;
  const plotW = width - padL - padR, plotH = height - padT - padB;

  const allHistVals = seriesByBank.flatMap(s => s.points.map(p => p.value));
  const allForecastVals = Object.values(forecastByBank).flatMap(f => f ? f.forecast.map(p => p.value) : []);
  const allVals = [...allHistVals, ...allForecastVals];
  if (allVals.length === 0) {
    return `<div class="forecast-empty">Not enough historical data yet to forecast a trend.</div>`;
  }

  const rawMin = Math.min(...allVals), rawMax = Math.max(...allVals);
  const pad = Math.max((rawMax - rawMin) * 0.15, 0.3);
  const { min, max, step } = niceAxisBounds(rawMin - pad, rawMax + pad);

  const allDates = [
    ...seriesByBank.flatMap(s => s.points.map(p => p.date)),
    ...Object.values(forecastByBank).flatMap(f => f ? f.forecast.map(p => p.date) : []),
  ].sort((a, b) => a - b);
  const uniqueDates = [...new Set(allDates.map(d => d.toISOString().slice(0, 10)))].sort();

  const xForDate = d => {
    const key = d.toISOString().slice(0, 10);
    const idx = uniqueDates.indexOf(key);
    return padL + (uniqueDates.length > 1 ? (plotW * idx) / (uniqueDates.length - 1) : plotW / 2);
  };
  const yForVal = v => padT + plotH * (1 - (v - min) / (max - min));

  const tickCount = Math.round((max - min) / step);
  const yGridLines = Array.from({ length: tickCount + 1 }, (_, i) => {
    const val = min + step * i;
    const y = padT + plotH * (1 - i / tickCount);
    return `<line x1="${padL}" y1="${y}" x2="${width - padR}" y2="${y}" stroke="var(--border, #EAE3D6)" stroke-width="1"></line>
            <text x="${padL - 8}" y="${y + 4}" text-anchor="end" font-family="JetBrains Mono, monospace" font-size="10.5" fill="var(--text-muted, #8B8578)">${val.toFixed(2)}</text>`;
  }).join('');

  const xLabelStep = Math.max(Math.ceil(uniqueDates.length / 8), 1);
  const xLabels = uniqueDates.map((d, i) => {
    if (i % xLabelStep !== 0 && i !== uniqueDates.length - 1) return '';
    const x = padL + (uniqueDates.length > 1 ? (plotW * i) / (uniqueDates.length - 1) : plotW / 2);
    return `<text x="${x}" y="${height - 10}" text-anchor="middle" font-family="Inter, sans-serif" font-size="10.5" fill="var(--text-secondary, #5B6472)">${fmtDateShort(new Date(d))}</text>`;
  }).join('');

  const seriesSvg = seriesByBank.map(s => {
    const histCoords = s.points.map(p => ({ x: xForDate(p.date), y: yForVal(p.value) }));
    const f = forecastByBank[s.bank_id];
    const forecastCoords = f ? f.forecast.map(p => ({ x: xForDate(p.date), y: yForVal(p.value) })) : [];
    const allCoords = [...histCoords, ...forecastCoords];
    const { solid, dashed } = smoothPath(allCoords, f ? histCoords.length - 1 : null);

    return `
      <path d="${solid}" fill="none" stroke="${s.color}" stroke-width="2.25" stroke-linecap="round" stroke-linejoin="round"></path>
      ${dashed ? `<path d="${dashed}" fill="none" stroke="${s.color}" stroke-width="2.25" stroke-linecap="round" stroke-dasharray="5,5" opacity="0.65"></path>` : ''}
    `;
  }).join('');

  return `
    <svg viewBox="0 0 ${width} ${height}" style="width:100%;height:auto;display:block;">
      ${yGridLines}
      ${xLabels}
      ${seriesSvg}
    </svg>`;
}

// A "today's snapshot" bar chart: one bar per bank, value labeled
// directly on top — clearer than a table for "who's cheapest right
// now" at a glance, complementary to the ranking table's precision.
export function renderBarChart(bars, containerWidth = 360) {
  const width = containerWidth, height = 230;
  const padL = 8, padR = 8, padT = 34, padB = 26;
  const plotW = width - padL - padR, plotH = height - padT - padB;

  if (bars.length === 0) return `<div class="hist-empty">No data available.</div>`;

  const vals = bars.map(b => b.value);
  const rawMin = Math.min(...vals), rawMax = Math.max(...vals);
  const range = Math.max(rawMax - rawMin, 0.01);
  const min = rawMin - range * 0.5;
  const max = rawMax + range * 0.15;

  const barW = Math.min(56, (plotW / bars.length) * 0.55);
  const gap = plotW / bars.length;

  const barsSvg = bars.map((b, i) => {
    const cx = padL + gap * i + gap / 2;
    const barH = plotH * ((b.value - min) / (max - min));
    const y = padT + plotH - barH;
    return `
      <text x="${cx}" y="${y - 10}" text-anchor="middle" font-family="JetBrains Mono, monospace" font-size="12.5" font-weight="600" fill="var(--ink, #14213D)">৳${b.value.toFixed(2)}</text>
      <rect x="${(cx - barW / 2).toFixed(1)}" y="${y.toFixed(1)}" width="${barW}" height="${barH.toFixed(1)}" rx="6" fill="${b.color}"></rect>
      <text x="${cx}" y="${height - 8}" text-anchor="middle" font-family="Inter, sans-serif" font-size="11.5" fill="var(--text-secondary, #5B6472)">${b.label}</text>
    `;
  }).join('');

  return `<svg viewBox="0 0 ${width} ${height}" style="width:100%;height:auto;display:block;">${barsSvg}</svg>`;
}
