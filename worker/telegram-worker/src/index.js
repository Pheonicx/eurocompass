const DATA_URL =
  "https://raw.githubusercontent.com/Pheonicx/eurocompass/main/exports/latest.json";

async function loadData() {
  const response = await fetch(DATA_URL);

  if (!response.ok) {
    throw new Error("Unable to load market data.");
  }

  return await response.json();
}

export default {
  async fetch(request) {
    const url = new URL(request.url);

    if (url.pathname === "/") {
      return new Response(
`🧭 EuroCompass Cloud

Endpoints

/health
/rates
/summary
/best
/banks`,
      {
        headers: {
          "content-type": "text/plain;charset=UTF-8",
        },
      });
    }

    if (url.pathname === "/health") {
      return Response.json({
        project: "EuroCompass",
        status: "online",
        version: "2.0.0",
        service: "Cloudflare Worker",
        time: new Date().toISOString(),
      });
    }

    const data = await loadData();

    if (url.pathname === "/rates") {
      return Response.json(data);
    }

    if (url.pathname === "/summary") {
      return Response.json(data.summary);
    }

    if (url.pathname === "/banks") {
      return Response.json(data.banks);
    }

    if (url.pathname === "/best") {
      return Response.json({
        generated_at: data.generated_at,
        bank: data.summary.lowest_sell.bank,
        tt_selling: data.summary.lowest_sell.value,
      });
    }

    if (url.pathname === "/telegram") {

  	if (request.method !== "POST") {
    	return new Response("Telegram Webhook", { status: 200 });
  		}

  		const update = await request.json();

  		console.log(JSON.stringify(update, null, 2));

  		return new Response("OK");
	}

    return new Response("404 Not Found", {
      status: 404,
    });
  },
};