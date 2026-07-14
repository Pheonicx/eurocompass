import { REPO_RAW, BANK_META } from './config.js';

async function fetchJSON(url) {
  const res = await fetch(url + (url.includes('?') ? '&' : '?') + '_=' + Date.now());
  if (!res.ok) throw new Error('Failed to fetch ' + url + ' (' + res.status + ')');
  return res.json();
}

async function fetchText(url) {
  const res = await fetch(url + (url.includes('?') ? '&' : '?') + '_=' + Date.now());
  if (!res.ok) throw new Error('Failed to fetch ' + url + ' (' + res.status + ')');
  return res.text();
}

function parseHistoryCSV(text) {
  const lines = text.trim().split(/\r?\n/);
  if (lines.length < 2) return [];
  const rows = lines.slice(1).map(line => {
    const parts = line.split(',');
    return { date: parts[0], time: parts[1], buy: parseFloat(parts[3]), sell: parseFloat(parts[4]) };
  }).filter(r => r.date && !isNaN(r.sell) && !isNaN(r.buy));
  // one entry per date: keep the last reading of each day
  const byDate = {};
  rows.forEach(r => { byDate[r.date] = r; });
  return Object.keys(byDate).sort().map(d => byDate[d]);
}

// Populates the shared state object with live data. Throws on failure so
// the caller can show the error screen.
export async function loadAll(state) {
  const latest = await fetchJSON(`${REPO_RAW}/exports/latest.json`);
  state.generatedAt = latest.generated_at;
  state.summary = latest.summary;
  state.banks = latest.banks.map(b => {
    const meta = BANK_META[b.bank] || { name: b.bank, color: "#6B7280" };
    return {
      key: b.bank, name: meta.name, color: meta.color, buy: b.buy, sell: b.sell,
      rateDate: b.rate_date || null,
      isStale: !!b.is_stale,
      student: b.student || null,
    };
  });

  const histResults = await Promise.allSettled(
    state.banks.map(b => fetchText(`${REPO_RAW}/history/${b.key}.csv`))
  );
  state.banks.forEach((b, i) => {
    const r = histResults[i];
    const daily = r.status === 'fulfilled' ? parseHistoryCSV(r.value) : [];
    state.sellHistByBank[b.key] = daily.map(d => ({ date: d.date, value: d.sell }));
    state.buyHistByBank[b.key] = daily.map(d => ({ date: d.date, value: d.buy }));
  });
}
