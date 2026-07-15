import { REF_USD_BDT, FORECAST_HISTORY_DAYS, FORECAST_AHEAD_DAYS, FORECAST_MIN_POINTS } from './config.js';

export function activeRate(state, b) {
  return state.mode === 'buy' ? b.sell : b.buy;
}

// The rate the calculator should actually use for a bank: its student
// file rate, if the toggle is on and that bank publishes one, otherwise
// its normal rate. Student rates only make sense for sending money
// (buy mode) — an education remittance context — so the toggle has no
// effect in sell mode even if left on.
export function effectiveRate(state, b) {
  if (state.useStudentRate && state.mode === 'buy' && b.student) {
    if (b.student.rate !== undefined) return b.student.rate;
    if (b.student.sell !== undefined) return b.student.sell;
  }
  if (state.useStudentRate && state.mode === 'sell' && b.student && b.student.buy !== undefined) {
    return b.student.buy;
  }
  return activeRate(state, b);
}

export function usingStudentRate(state, b) {
  return effectiveRate(state, b) !== activeRate(state, b);
}

export function rankedBanks(state) {
  return [...state.banks].sort((a, b) =>
    state.mode === 'buy' ? a.sell - b.sell : b.buy - a.buy
  );
}

// Same idea as rankedBanks, but ranks by whatever rate the calculator
// is actually going to use (student or normal) — so the "recommended
// bank" reflects reality when the student toggle changes who's cheapest.
export function rankedBanksForCalculator(state) {
  return [...state.banks].sort((a, b) =>
    state.mode === 'buy'
      ? effectiveRate(state, a) - effectiveRate(state, b)
      : effectiveRate(state, b) - effectiveRate(state, a)
  );
}

// Converts an amount typed in EUR, BDT, or USD into an EUR-equivalent
// amount, using the given bank's own rate for the EUR<->BDT leg.
export function toEURAmount(amount, currency, rate) {
  if (currency === 'EUR') return amount;
  if (currency === 'BDT') return amount / rate;
  // USD -> BDT (reference rate) -> EUR (this bank's rate)
  return (amount * REF_USD_BDT) / rate;
}

function flatFeesBDT(state, rate) {
  return state.fees.reduce((sum, f) => {
    const amt = parseFloat(f.amount) || 0;
    if (f.currency === 'BDT') return sum + amt;
    if (f.currency === 'EUR') return sum + amt * rate;
    return sum + amt * REF_USD_BDT;
  }, 0);
}

function vatBDT(state, rate, baseBDT, flatFeesTotalBDT) {
  const pct = (parseFloat(state.vat.percent) || 0) / 100;
  const basisAmount = state.vat.basis === 'transfer' ? baseBDT : flatFeesTotalBDT;
  return basisAmount * pct;
}

export function feeTotalBDT(state, rate, baseBDT) {
  const flat = flatFeesBDT(state, rate);
  const vat = vatBDT(state, rate, baseBDT, flat);
  return { flat, vat, total: flat + vat };
}

export function computeForBank(state, b, amountEUR) {
  const rate = effectiveRate(state, b);
  const baseBDT = amountEUR * rate;
  const fees = feeTotalBDT(state, rate, baseBDT);
  const totalBDT = state.mode === 'buy' ? baseBDT + fees.total : baseBDT - fees.total;
  const totalEUR = totalBDT / rate;
  return { rate, baseBDT, feesBDT: fees.total, feesFlat: fees.flat, feesVat: fees.vat, totalBDT, totalEUR, usedStudentRate: usingStudentRate(state, b) };
}

export function computeMarketIntelligence(state) {
  const activeVals = state.banks.map(b => activeRate(state, b));
  const todaySpread = Math.max(...activeVals) - Math.min(...activeVals);

  const histSource = state.mode === 'buy' ? state.sellHistByBank : state.buyHistByBank;
  const dateSet = new Set();
  state.banks.forEach(b => (histSource[b.key] || []).forEach(d => dateSet.add(d.date)));
  const dates = [...dateSet].sort().slice(-7);
  const spreadsByDate = dates.map(date => {
    const vals = state.banks.map(b => {
      const rec = (histSource[b.key] || []).find(d => d.date === date);
      return rec ? rec.value : null;
    }).filter(v => v !== null);
    if (vals.length < 2) return null;
    return Math.max(...vals) - Math.min(...vals);
  }).filter(v => v !== null);
  const avgSpread = spreadsByDate.length ? spreadsByDate.reduce((a, b) => a + b, 0) / spreadsByDate.length : todaySpread;

  const ratio = avgSpread > 0 ? (todaySpread - avgSpread) / avgSpread : 0;
  const opportunityScore = Math.max(5, Math.min(95, Math.round(50 + ratio * 50)));

  let health, healthClass;
  if (todaySpread > avgSpread * 1.15) { health = 'Favorable'; healthClass = 'favorable'; }
  else if (todaySpread < avgSpread * 0.85) { health = 'Tight'; healthClass = 'tight'; }
  else { health = 'Normal'; healthClass = 'normal'; }

  const banksProcessed = state.summary ? state.summary.banks_processed : state.banks.length;
  const confidence = Math.round((banksProcessed / 5) * 100);

  return { todaySpread, avgSpread, opportunityScore, health, healthClass, confidence, hasHistory: spreadsByDate.length > 0 };
}

// --- Forecast: simple linear regression over recent history ---

function linearRegression(points) {
  // points: [{x, y}]. Returns {slope, intercept}.
  const n = points.length;
  const sumX = points.reduce((s, p) => s + p.x, 0);
  const sumY = points.reduce((s, p) => s + p.y, 0);
  const sumXY = points.reduce((s, p) => s + p.x * p.y, 0);
  const sumXX = points.reduce((s, p) => s + p.x * p.x, 0);
  const denom = (n * sumXX - sumX * sumX);
  if (denom === 0) return { slope: 0, intercept: sumY / n };
  const slope = (n * sumXY - sumX * sumY) / denom;
  const intercept = (sumY - slope * sumX) / n;
  return { slope, intercept };
}

// Returns null if there isn't enough history to forecast responsibly.
export function buildForecast(state, bankKey) {
  const histSource = state.mode === 'buy' ? state.sellHistByBank : state.buyHistByBank;
  const series = (histSource[bankKey] || []).slice(-FORECAST_HISTORY_DAYS);
  if (series.length < FORECAST_MIN_POINTS) return null;

  const points = series.map((d, i) => ({ x: i, y: d.value }));
  const { slope, intercept } = linearRegression(points);

  const lastDate = new Date(series[series.length - 1].date + 'T00:00:00');
  const forecastPoints = [];
  for (let i = 1; i <= FORECAST_AHEAD_DAYS; i++) {
    const x = points.length - 1 + i;
    const y = slope * x + intercept;
    const d = new Date(lastDate);
    d.setDate(d.getDate() + i);
    forecastPoints.push({ date: d, value: y });
  }

  return {
    history: series,
    forecast: forecastPoints,
    slopePerDay: slope,
    direction: slope > 0.005 ? 'rising' : slope < -0.005 ? 'falling' : 'flat',
  };
}
