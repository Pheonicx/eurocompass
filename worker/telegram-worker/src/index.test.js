import { describe, it, expect, vi, afterEach } from "vitest";
import worker from "./index.js";

const SAMPLE_V2_DATA = {
  generated_at: "2026-07-16T12:00:00+00:00",
  rates_by_currency: {
    EUR: [
      { bank_id: "BRAC", bank_name: "BRAC Bank PLC", buy: 139.6, sell: 142.4, confidence: "medium", is_stale: true },
    ],
  },
  recommendations: [
    {
      currency: "EUR",
      product_id: "TT",
      requested_amount: 1000,
      recommended_bank_id: "BRAC",
      recommended_bank_name: "BRAC Bank PLC",
      total_cost_bdt: 142400,
      confidence: "medium",
      explanation: "BRAC Bank PLC is recommended.",
      alternatives: [],
    },
  ],
};

function stubFetchForV2Data() {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url) => {
      if (String(url).includes("v2_exports")) {
        return new Response(JSON.stringify(SAMPLE_V2_DATA), { status: 200 });
      }
      return new Response("not found", { status: 404 });
    })
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("v2 HTTP endpoints", () => {
  it("/v2/health responds without needing v2 data", async () => {
    const res = await worker.fetch(new Request("http://worker.test/v2/health"), {});
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.layer).toBe("v2");
  });

  it("/v2/rates returns EUR rates by default", async () => {
    stubFetchForV2Data();
    const res = await worker.fetch(new Request("http://worker.test/v2/rates"), {});
    const body = await res.json();
    expect(body.currency).toBe("EUR");
    expect(body.rates).toHaveLength(1);
    expect(body.rates[0].bank_id).toBe("BRAC");
  });

  it("/v2/rates respects a ?currency= query param", async () => {
    stubFetchForV2Data();
    const res = await worker.fetch(new Request("http://worker.test/v2/rates?currency=USD"), {});
    const body = await res.json();
    expect(body.currency).toBe("USD");
    expect(body.rates).toEqual([]); // no USD data in the sample
  });

  it("/v2/recommendations returns the full recommendations array", async () => {
    stubFetchForV2Data();
    const res = await worker.fetch(new Request("http://worker.test/v2/recommendations"), {});
    const body = await res.json();
    expect(body.recommendations).toHaveLength(1);
    expect(body.recommendations[0].recommended_bank_id).toBe("BRAC");
  });

  it("existing v1 routes are untouched by these additions", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(
          JSON.stringify({
            summary: { banks_processed: 1, lowest_sell: { bank: "BRAC", value: 142.4 } },
            banks: [{ bank: "BRAC", sell: 142.4 }],
          }),
          { status: 200 }
        )
      )
    );
    const res = await worker.fetch(new Request("http://worker.test/best"), {});
    const body = await res.json();
    expect(body.bank).toBe("BRAC");
  });
});
