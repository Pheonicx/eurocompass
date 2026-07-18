import { describe, it, expect } from "vitest";
import {
  formatV2Rates,
  formatV2Recommendation,
  findRecommendation,
  listRecommendationOptions,
} from "./formatter.js";

describe("formatV2Rates", () => {
  it("handles no data gracefully", () => {
    expect(formatV2Rates([], "EUR")).toContain("No EUR rate data");
    expect(formatV2Rates(null, "USD")).toContain("No USD rate data");
  });

  it("sorts banks by sell rate, cheapest first", () => {
    const rates = [
      { bank_id: "A", bank_name: "Bank A", buy: 139, sell: 143, confidence: "medium", is_stale: false },
      { bank_id: "B", bank_name: "Bank B", buy: 139, sell: 140, confidence: "high", is_stale: false },
    ];
    const text = formatV2Rates(rates, "EUR");
    const posA = text.indexOf("Bank A");
    const posB = text.indexOf("Bank B");
    expect(posB).toBeLessThan(posA); // cheapest (Bank B) listed first
  });

  it("flags stale rates", () => {
    const rates = [
      { bank_id: "A", bank_name: "Bank A", buy: 139, sell: 143, confidence: "medium", is_stale: true },
    ];
    expect(formatV2Rates(rates, "EUR")).toContain("(stale)");
  });
});

describe("formatV2Recommendation", () => {
  const rec = {
    currency: "EUR",
    product_id: "TT",
    requested_amount: 1000,
    recommended_bank_name: "BRAC Bank PLC",
    total_cost_bdt: 142432.6,
    confidence: "medium",
    explanation: "BRAC Bank PLC is recommended because it is cheapest today.",
  };

  it("includes the recommended bank and total cost", () => {
    const text = formatV2Recommendation(rec);
    expect(text).toContain("BRAC Bank PLC");
    expect(text).toContain("142,432.60 BDT");
  });

  it("includes the full explanation text verbatim", () => {
    const text = formatV2Recommendation(rec);
    expect(text).toContain(rec.explanation);
  });
});

describe("findRecommendation", () => {
  const recommendations = [
    { currency: "EUR", requested_amount: 1000 },
    { currency: "EUR", requested_amount: 12208 },
    { currency: "USD", requested_amount: 1000 },
  ];

  it("finds an exact currency+amount match", () => {
    const found = findRecommendation(recommendations, "EUR", 12208);
    expect(found).not.toBeNull();
    expect(found.requested_amount).toBe(12208);
  });

  it("returns null when nothing matches", () => {
    expect(findRecommendation(recommendations, "GBP", 500)).toBeNull();
  });

  it("handles a null/undefined list without throwing", () => {
    expect(findRecommendation(null, "EUR", 1000)).toBeNull();
  });

  it("compares amount numerically, not as a string", () => {
    // Telegram text input arrives as a string ("1000"), recommendations
    // store it as a number -- this must still match.
    const found = findRecommendation(recommendations, "EUR", "1000");
    expect(found).not.toBeNull();
  });
});

describe("listRecommendationOptions", () => {
  it("lists each available amount with its currency", () => {
    const text = listRecommendationOptions([
      { currency: "EUR", requested_amount: 1000 },
      { currency: "USD", requested_amount: 500 },
    ]);
    expect(text).toContain("1,000 EUR");
    expect(text).toContain("500 USD");
  });

  it("handles an empty list gracefully", () => {
    expect(listRecommendationOptions([])).toContain("No example recommendations");
  });
});
