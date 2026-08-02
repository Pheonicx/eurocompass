// Shared constants used across the v2 dashboard.

// Points at v2-dev while this branch is in development. Update to
// "main" once v2-dev merges and the hourly workflow starts writing
// v2_exports/latest.json for real.
export const REPO_RAW = "https://raw.githubusercontent.com/Pheonicx/eurocompass/v2-dev";
export const EXPORT_PATH = "v2_exports/latest.json";

// Approximate reference rate used only to convert USD-denominated
// calculator fees when the transfer itself is in EUR (or vice versa).
// Not a live tracked rate.
export const REF_USD_BDT = 121.50;

export const DEFAULT_FEES = [
  { label: "Bank transfer fee", amount: 500, currency: "BDT" },
  { label: "Student file opening fee", amount: 3000, currency: "BDT" },
];
export const DEFAULT_VAT_PERCENT = 15;

// How many days of history to use for the trend forecast, and how many
// days ahead to project.
export const FORECAST_HISTORY_DAYS = 14;
export const FORECAST_AHEAD_DAYS = 7;
export const FORECAST_MIN_POINTS = 4;

export const BANK_META = {
  SONALI: { name: "Sonali Bank", color: "#0D9488" },
  BRAC:   { name: "BRAC Bank",   color: "#6366F1" },
  CITY:   { name: "City Bank",   color: "#C2622D" },
  EBL:    { name: "EBL",         color: "#B23A63" },
  PRIME:  { name: "Prime Bank",  color: "#6B7280" },
};

export const CURRENCY_META = {
  EUR: { symbol: "€", label: "Euro" },
  USD: { symbol: "$", label: "US Dollar" },
};

export const CONFIDENCE_META = {
  high:   { label: "High confidence",   color: "#3F7A57" },
  medium: { label: "Medium confidence", color: "#B8862F" },
  low:    { label: "Low confidence",    color: "#B23A63" },
};

// The three scenarios core.export.DEFAULT_SCENARIOS actually computes
// server-side. Kept here (not derived from the data) so the UI can
// label them consistently even before data loads.
export const SCENARIOS = [
  { currency: "EUR", amount: 1000 },
  { currency: "EUR", amount: 12208 },
  { currency: "USD", amount: 1000 },
];
