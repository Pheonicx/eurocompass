export function fmtBDT(n) {
  return '৳' + n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export function fmtAmount(currency, amount) {
  return amount.toLocaleString('en-US', { maximumFractionDigits: 0 }) + ' ' + currency;
}

// Three-dot confidence indicator (●●● / ●●○ / ●○○), used consistently
// everywhere a confidence level appears — reinforces that this is real
// per-observation confidence, not just a colored word, wherever it
// shows up on the page.
export function confDots(level) {
  return `<span class="conf-dots ${level}"><span></span><span></span><span></span></span>`;
}
