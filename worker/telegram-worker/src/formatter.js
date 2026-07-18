// worker/telegram-worker/src/formatter.js
//
// Pure formatting functions for EuroCompass v2 data
// (v2_exports/latest.json, produced by core/export.py in the Python
// backend). Kept separate from index.js's routing/Telegram-sending code
// so they can be unit tested directly with plain Vitest, without needing
// the full Cloudflare Workers test runtime.
//
// Nothing here duplicates v2's actual recommendation MATH -- that's
// computed once in Python (core/transfer/) and exported as plain JSON.
// These functions only format numbers and explanation text that were
// already computed there (CLAUDE.md: "One Source of Truth" -- business
// logic exists once).

export function formatV2Rates(rates, currencyCode) {
  if (!rates || rates.length === 0) {
    return `No ${currencyCode} rate data available yet from the v2 pipeline.`;
  }

  const sorted = [...rates].sort((a, b) => a.sell - b.sell);
  const medals = ["🥇", "🥈", "🥉"];

  const lines = [`🧭 EuroCompass v2 — ${currencyCode} rates`, ""];

  sorted.forEach((bank, index) => {
    const rank = medals[index] ?? `${index + 1}.`;
    const staleTag = bank.is_stale ? " (stale)" : "";
    lines.push(`${rank} ${bank.bank_name}`);
    lines.push(`   Buy ${bank.buy.toFixed(4)} · Sell ${bank.sell.toFixed(4)}${staleTag}`);
    lines.push(`   Confidence: ${bank.confidence}`);
    lines.push("");
  });

  return lines.join("\n").trim();
}

export function formatV2Recommendation(rec) {
  const totalFormatted = rec.total_cost_bdt.toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });

  const header =
    `🧭 EuroCompass v2\n\n` +
    `💶 ${rec.requested_amount.toLocaleString()} ${rec.currency} · ${rec.product_id}\n\n` +
    `🏆 Recommended: ${rec.recommended_bank_name}\n` +
    `💵 Total cost: ${totalFormatted} BDT\n` +
    `📊 Confidence: ${rec.confidence}\n\n`;

  return (header + rec.explanation).trim();
}

export function findRecommendation(recommendations, currency, amount) {
  if (!recommendations) return null;
  return (
    recommendations.find(
      (r) => r.currency === currency && Number(r.requested_amount) === Number(amount)
    ) ?? null
  );
}

export function listRecommendationOptions(recommendations) {
  if (!recommendations || recommendations.length === 0) {
    return "No example recommendations are available yet.";
  }
  return recommendations
    .map(
      (r) =>
        `• ${r.requested_amount.toLocaleString()} ${r.currency} → /v2recommend ${r.currency} ${r.requested_amount}`
    )
    .join("\n");
}
