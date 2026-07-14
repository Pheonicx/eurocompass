// Shared constants used across the dashboard.

export const REPO_RAW = "https://raw.githubusercontent.com/Pheonicx/eurocompass/main";

// Approximate reference rate used only to convert USD-denominated amounts
// and fees. Not a live tracked rate — your collectors only track EUR.
export const REF_USD_BDT = 121.50;

export const BANK_META = {
  SONALI: { name: "Sonali Bank", color: "#0D9488" },
  BRAC:   { name: "BRAC Bank",   color: "#6366F1" },
  CITY:   { name: "City Bank",   color: "#C2622D" },
  EBL:    { name: "EBL",         color: "#B23A63" },
  PRIME:  { name: "Prime Bank",  color: "#6B7280" },
};

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
