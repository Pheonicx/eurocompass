import { DEFAULT_FEES, DEFAULT_VAT_PERCENT } from './config.js';

// Single shared state object. Every render module reads from this;
// only main.js and dataLoader.js write to state.data / state.currency.

export const state = {
  currency: 'EUR',        // the currency toggle selected across the whole dashboard
  mode: 'send',           // 'send' (buying EUR/USD with BDT, TT selling) or 'convert' (selling EUR/USD for BDT, TT buying)
  data: null,             // the full parsed v2_exports/latest.json payload
  calc: {
    amount: 1000,
    currency: 'EUR',
    useStudentRate: false,
    fees: DEFAULT_FEES.map(f => ({ ...f })),
    vatPercent: DEFAULT_VAT_PERCENT,
    vatBasis: 'transfer',  // 'transfer' (% of the transfer amount) or 'fees' (% of the flat fees only)
  },
};

// Convenience accessors — every render module needs these same
// lookups, so they live in one place instead of being recomputed with
// slightly different logic in every file.

export function currentRates() {
  return (state.data?.rates_by_currency?.[state.currency]) || [];
}

export function currentTrends() {
  return (state.data?.trends_by_currency?.[state.currency]) || [];
}

export function currentHistory() {
  return (state.data?.history_by_currency?.[state.currency]) || [];
}

export function recommendationFor(currency, amount) {
  const recs = state.data?.recommendations || [];
  return recs.find(r => r.currency === currency && r.requested_amount === amount) || null;
}

// The rate a bank's row should be judged on, given the current mode:
// 'send' (buying foreign currency with BDT) uses the sell rate — what
// the bank charges you per unit. 'convert' (selling foreign currency
// for BDT) uses the buy rate — what the bank pays you per unit.
export function activeRate(r) {
  return state.mode === 'send' ? r.sell : r.buy;
}

export function rankedRates() {
  const rates = [...currentRates()];
  return rates.sort((a, b) =>
    state.mode === 'send' ? activeRate(a) - activeRate(b) : activeRate(b) - activeRate(a)
  );
}
