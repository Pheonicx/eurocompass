import { describe, it, expect, vi, afterEach } from "vitest";
import worker from "./index.js";

function stubFetchToFail() {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => new Response("not found", { status: 404 }))
  );
}

function stubFetchEmptyBanks() {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () =>
      new Response(
        JSON.stringify({
          generated_at: "2026-07-28T09:00:00+00:00",
          summary: null,
          banks: [],
        }),
        { status: 200 }
      )
    )
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("v1 HTTP routes handle a data-load failure gracefully", () => {
  it("/rates does not crash with a bare 500 when GitHub raw fetch fails", async () => {
    stubFetchToFail();
    const res = await worker.fetch(new Request("http://worker.test/rates"), {});
    expect(res.status).toBe(503);
    const body = await res.json();
    expect(body.error).toBeDefined();
  });

  it("/summary does not crash with a bare 500 when GitHub raw fetch fails", async () => {
    stubFetchToFail();
    const res = await worker.fetch(new Request("http://worker.test/summary"), {});
    expect(res.status).toBe(503);
  });

  it("/best does not crash with a bare 500 when GitHub raw fetch fails", async () => {
    stubFetchToFail();
    const res = await worker.fetch(new Request("http://worker.test/best"), {});
    expect(res.status).toBe(503);
  });
});

describe("Telegram handlers handle a data-load failure gracefully", () => {
  function telegramUpdate(text) {
    return new Request("http://worker.test/telegram", {
      method: "POST",
      body: JSON.stringify({
        message: { chat: { id: 123 }, text },
      }),
    });
  }

  it("/rates command sends a friendly message instead of failing silently", async () => {
    // First call: incoming Telegram webhook fetch never happens (this IS
    // the fetch call), but loadData() inside the handler uses global
    // fetch too -- stub it to fail, then check sendTelegramMessage (the
    // worker's own outbound fetch) was still invoked with an error text.
    const calls = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url, opts) => {
        if (String(url).includes("api.telegram.org")) {
          calls.push(JSON.parse(opts.body));
          return new Response(JSON.stringify({ ok: true }), { status: 200 });
        }
        return new Response("not found", { status: 404 });
      })
    );

    const res = await worker.fetch(telegramUpdate("/rates"), { TELEGRAM_BOT_TOKEN: "fake" });
    expect(res.status).toBe(200);
    // Must have actually sent *some* message to the user, not silently
    // thrown before ever calling sendTelegramMessage.
    expect(calls.length).toBeGreaterThan(0);
    expect(calls[0].text.toLowerCase()).toContain("unavailable");
  });

  it("/status command sends a friendly message instead of failing silently", async () => {
    const calls = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url, opts) => {
        if (String(url).includes("api.telegram.org")) {
          calls.push(JSON.parse(opts.body));
          return new Response(JSON.stringify({ ok: true }), { status: 200 });
        }
        return new Response("not found", { status: 404 });
      })
    );

    const res = await worker.fetch(telegramUpdate("/status"), { TELEGRAM_BOT_TOKEN: "fake" });
    expect(res.status).toBe(200);
    expect(calls.length).toBeGreaterThan(0);
    expect(calls[0].text.toLowerCase()).toContain("unavailable");
  });

  it("/recommend command sends a friendly message instead of failing silently", async () => {
    const calls = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url, opts) => {
        if (String(url).includes("api.telegram.org")) {
          calls.push(JSON.parse(opts.body));
          return new Response(JSON.stringify({ ok: true }), { status: 200 });
        }
        return new Response("not found", { status: 404 });
      })
    );

    const res = await worker.fetch(telegramUpdate("/recommend 1000"), { TELEGRAM_BOT_TOKEN: "fake" });
    expect(res.status).toBe(200);
    expect(calls.length).toBeGreaterThan(0);
    expect(calls[0].text.toLowerCase()).toContain("unavailable");
  });

  it("/rates command doesn't crash on an empty banks list (all collectors failed)", async () => {
    const calls = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url, opts) => {
        if (String(url).includes("api.telegram.org")) {
          calls.push(JSON.parse(opts.body));
          return new Response(JSON.stringify({ ok: true }), { status: 200 });
        }
        return new Response(
          JSON.stringify({ generated_at: "2026-07-28T09:00:00+00:00", banks: [] }),
          { status: 200 }
        );
      })
    );

    const res = await worker.fetch(telegramUpdate("/rates"), { TELEGRAM_BOT_TOKEN: "fake" });
    expect(res.status).toBe(200);
    expect(calls.length).toBeGreaterThan(0);
  });
});
