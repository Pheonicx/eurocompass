import { state, currentRates, currentHistory, activeRate } from './state.js';
import { REF_USD_BDT, FORECAST_HISTORY_DAYS, FORECAST_AHEAD_DAYS, FORECAST_MIN_POINTS } from './config.js';

// The rate a calculator row should actually use: the bank's student
// rate, if the toggle is on, that bank publishes one, AND we're in
// 'send' mode (student file rates are an education-remittance concept
// — they don't apply to converting money the other direction).
export function effectiveRate(r) {
  if (state.calc.useStudentRate && state.mode === 'send' && r.student_rate) {
    return r.student_rate;
  }
  return activeRate(r);
}

function flatFeesBDT(rate) {
  return state.calc.fees.reduce((sum, f) => {
    const amt = parseFloat(f.amount) || 0;
    if (f.currency === 'BDT') return sum + amt;
    if (f.currency === 'EUR' && state.calc.currency === 'EUR') return sum + amt * rate;
    if (f.currency === 'USD' && state.calc.currency === 'USD') return sum + amt * rate;
    return sum + amt * REF_USD_BDT;
  }, 0);
}

function vatBDT(baseBDT, flatFeesTotalBDT) {
  const pct = (parseFloat(state.calc.vatPercent) || 0) / 100;
  const basis = state.calc.vatBasis === 'transfer' ? baseBDT : flatFeesTotalBDT;
  return basis * pct;
}

// Full cost breakdown for one bank, given the current calculator
// amount/fees/VAT settings — this is deliberately client-side (v2's
// server-computed recommendations only cover 3 fixed scenario
// amounts): any amount, live.
export function computeForBank(r, amount) {
  const rate = effectiveRate(r);
  const baseBDT = amount * rate;
  const flat = flatFeesBDT(rate);
  const vat = vatBDT(baseBDT, flat);
  const feesTotal = flat + vat;
  const totalBDT = state.mode === 'send' ? baseBDT + feesTotal : baseBDT - feesTotal;
  return { rate, baseBDT, feesFlat: flat, feesVat: vat, feesTotal, totalBDT, usedStudentRate: rate !== activeRate(r) };
}

// Real market intelligence: deterministic statistics derived from
// actual stored history, exactly like v1's — an "opportunity score" is
// a transparent formula over real numbers (shown alongside it), not an
// invented or AI-generated figure.
export function computeMarketIntelligence() {
  const rates = currentRates();
  const activeVals = rates.map(r => activeRate(r));
  const todaySpread = activeVals.length ? Math.max(...activeVals) - Math.min(...activeVals) : 0;

  const history = currentHistory();
  const dateSet = new Set();
  history.forEach(h => h.points.forEach(p => dateSet.add(p.collected_at.slice(0, 10))));
  const dates = [...dateSet].sort().slice(-7);

  const spreadsByDate = dates.map(date => {
    const vals = history
      .map(h => {
        const point = h.points.find(p => p.collected_at.slice(0, 10) === date);
        return point ? (state.mode === 'send' ? point.sell : point.buy) : null;
      })
      .filter(v => v !== null);
    if (vals.length < 2) return null;
    return Math.max(...vals) - Math.min(...vals);
  }).filter(v => v !== null);

  const hasHistory = spreadsByDate.length > 0;
  const avgSpread = hasHistory
    ? spreadsByDate.reduce((a, b) => a + b, 0) / spreadsByDate.length
    : todaySpread;

  const ratio = avgSpread > 0 ? (todaySpread - avgSpread) / avgSpread : 0;
  const opportunityScore = Math.max(5, Math.min(95, Math.round(50 + ratio * 50)));

  let health, healthClass;
  if (todaySpread > avgSpread * 1.15) { health = 'Favorable'; healthClass = 'favorable'; }
  else if (todaySpread < avgSpread * 0.85) { health = 'Tight'; healthClass = 'tight'; }
  else { health = 'Normal'; healthClass = 'normal'; }

  // Real confidence: how many banks are actually reporting data right
  // now for this currency, out of the 5 configured — the same "did
  // collection actually work" question v1 asked, kept because it's a
  // genuinely different, useful signal from the per-observation
  // HIGH/MEDIUM/LOW confidence shown elsewhere on rate rows.
  const totalBanksConfigured = 5;
  const confidence = Math.round((rates.length / totalBanksConfigured) * 100);

  return { todaySpread, avgSpread, opportunityScore, health, healthClass, confidence, hasHistory, rates };
}

function linearRegression(points) {
  const n = points.length;
  const sumX = points.reduce((s, p) => s + p.x, 0);
  const sumY = points.reduce((s, p) => s + p.y, 0);
  const sumXY = points.reduce((s, p) => s + p.x * p.y, 0);
  const sumXX = points.reduce((s, p) => s + p.x * p.x, 0);
  const denom = n * sumXX - sumX * sumX;
  if (denom === 0) return { slope: 0, intercept: sumY / n };
  const slope = (n * sumXY - sumX * sumY) / denom;
  const intercept = (sumY - slope * sumX) / n;
  return { slope, intercept };
}

// A simple, honestly-labeled straight-line projection of a bank's
// recent rate history — not a prediction, not AI-generated, just
// transparent arithmetic over real stored numbers with the trend
// direction and disclaimer shown right alongside it. Returns null if
// there isn't enough history to say anything responsible.
export function buildForecast(bankId) {
  const bankHistory = currentHistory().find(h => h.bank_id === bankId);
  if (!bankHistory) return null;

  const series = bankHistory.points.slice(-FORECAST_HISTORY_DAYS);
  if (series.length < FORECAST_MIN_POINTS) return null;

  const valueOf = p => (state.mode === 'send' ? p.sell : p.buy);
  const points = series.map((p, i) => ({ x: i, y: valueOf(p) }));
  const { slope, intercept } = linearRegression(points);

  const lastDate = new Date(series[series.length - 1].collected_at);
  const forecastPoints = [];
  for (let i = 1; i <= FORECAST_AHEAD_DAYS; i++) {
    const x = points.length - 1 + i;
    const y = slope * x + intercept;
    const d = new Date(lastDate);
    d.setDate(d.getDate() + i);
    forecastPoints.push({ date: d, value: y });
  }

  return {
    history: series.map(p => ({ date: new Date(p.collected_at), value: valueOf(p) })),
    forecast: forecastPoints,
    direction: slope > 0.005 ? 'rising' : slope < -0.005 ? 'falling' : 'flat',
  };
}
