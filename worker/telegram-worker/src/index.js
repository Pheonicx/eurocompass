const DATA_URL =
  "https://raw.githubusercontent.com/Pheonicx/eurocompass/main/exports/latest.json";

async function loadData() {
  const response = await fetch(DATA_URL);

  if (!response.ok) {
    throw new Error("Unable to load market data.");
  }

  return await response.json();
}

function calculateTransferCost(banks, euroAmount) {

  const results = banks.map(bank => ({
    bank: bank.bank,
    rate: bank.sell,
    total_cost: bank.sell * euroAmount,
  }));

  results.sort((a, b) => a.total_cost - b.total_cost);

  const cheapest = results[0].total_cost;

  results.forEach(result => {
    result.extra_cost = result.total_cost - cheapest;
  });

  return results;

}

async function sendTelegramMessage(env, chatId, text) {
  const url =
    `https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/sendMessage`;

  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      chat_id: chatId,
      text: text,
    }),
  });

  if (!response.ok) {
    console.log(await response.text());
  }
}

export default {
  async fetch(request, env) {
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

const message = update.message;

if (!message) {
  return new Response("OK");
}

const chatId = message.chat.id;
const text = message.text ?? "";

if (text === "/start") {

  await sendTelegramMessage(
    env,
    chatId,
`🧭 EuroCompass

Cloud-powered EUR Exchange Intelligence

Available Commands

/rates
/recommend <EUR amount>
/help`
  );

}

else if (text === "/rates") {

  const data = await loadData();

  const banks = data.banks
    .sort((a, b) => a.sell - b.sell);

  let reply = "🏦 Today's EUR TT Selling Rates\n\n";

  const medals = ["🥇","🥈","🥉"];

  banks.forEach((bank, index) => {

    const rank = medals[index] ?? `${index + 1}.`;

    reply += `${rank} ${bank.bank}\n`;
    reply += `${bank.sell.toFixed(4)}\n\n`;

  });

  await sendTelegramMessage(
    env,
    chatId,
    reply.trim()
  );

}

else if (text.startsWith("/recommend")) {

  const parts = text.split(" ");

  if (parts.length !== 2) {

    await sendTelegramMessage(
      env,
      chatId,
      "Usage:\n/recommend <EUR amount>"
    );

    return new Response("OK");
  }

  const euroAmount = Number(parts[1]);

  if (isNaN(euroAmount) || euroAmount <= 0) {

    await sendTelegramMessage(
      env,
      chatId,
      "Please enter a valid EUR amount."
    );

    return new Response("OK");
  }

  const data = await loadData();

  const results = calculateTransferCost(
    data.banks,
    euroAmount
  );

  const best = results[0];

  const savings =
    results[results.length - 1].total_cost -
    best.total_cost;

  await sendTelegramMessage(
    env,
    chatId,
`💶 Germany Transfer

Amount
€${euroAmount}

🏆 Recommended Bank

${best.bank}

TT Selling
${best.rate.toFixed(4)}

Estimated Cost
${best.total_cost.toFixed(2)} BDT

Savings vs Most Expensive Bank
${savings.toFixed(2)} BDT`
  );

}

return new Response("OK");
	}

    return new Response("404 Not Found", {
      status: 404,
    });
  },
};