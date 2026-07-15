// Single shared state object. Every render module reads from this;
// only main.js and dataLoader.js write to it.

import { DEFAULT_FEES, DEFAULT_VAT_PERCENT } from './config.js';

export const state = {
  mode: 'buy',            // 'buy' = sending to Germany (TT sell) | 'sell' = converting EUR to BDT (TT buy)
  amountCurrency: 'EUR',  // currency of the number typed into the calculator's amount box
  useStudentRate: false,  // when true, the calculator uses a bank's student-file rate instead of its normal rate, for banks that publish one
  fees: DEFAULT_FEES.map(f => ({ ...f })),
  vat: {
    percent: DEFAULT_VAT_PERCENT,
    basis: 'transfer',    // 'transfer' = % of transfer amount | 'fees' = % of the other added costs
  },
  banks: [],               // [{key, name, color, buy, sell}]
  sellHistByBank: {},      // {key: [{date, value}]}
  buyHistByBank: {},
  generatedAt: null,
  summary: null,
};
