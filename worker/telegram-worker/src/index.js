const DATA_URL =
  "https://raw.githubusercontent.com/Pheonicx/eurocompass/main/exports/latest.json";
// Users waiting to enter EUR amount
const pendingRecommendations = new Map();

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

      reply_markup: {

        keyboard: [

        [
          { text: "📊 Rates" },
          { text: "💶 Recommend" }
        ],

        [
          { text: "🟢 Status" },
          { text: "🌐 Dashboard" }
        ],

        [
          { text: "❓ Help" }
        ]

      ],

        resize_keyboard: true,
        is_persistent: true

      }

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

if (
  text === "/start" ||
  text === "/menu"
) {

  await sendTelegramMessage(
    env,
    chatId,
`🧭 EuroCompass

Cloud-powered EUR Exchange Intelligence

Available Commands

📊 /rates
Live TT selling rates

💶 /recommend <EUR>
Find the cheapest bank

🟢 /status
System status

❓ /help
Show this help`
  );

}

else if (
  text === "/help" ||
  text === "❓ Help"
) {

  await sendTelegramMessage(
    env,
    chatId,
`🧭 EuroCompass

Available Commands

📊 /rates
Live TT selling rates

💶 /recommend <EUR>
Example:
 /recommend 11904

🟢 /status
System status

❓ /help
Show this help`
  );

}

else if (text === "🌐 Dashboard") {

  await sendTelegramMessage(
  env,
  chatId,
`🌐 EuroCompass Dashboard

Access the live dashboard here:

https://eurocompass.eurocompass.workers.dev/#

📊 Live rates
📈 Analytics
💶 Transfer calculator`
);

}

else if (
  text === "/rates" ||
  text === "📊 Rates"
) {

  const data = await loadData();

  const banks = [...data.banks].sort(
    (a, b) => a.sell - b.sell
  );

  const best = banks[0];
  const worst = banks[banks.length - 1];

  const spread = worst.sell - best.sell;
  const saving = spread * 12153;

  let reply =
`🧭 EuroCompass

🏆 Best Today

${best.bank}
${best.sell.toFixed(4)} BDT/EUR

💰 Market Spread
${spread.toFixed(4)} BDT

💸 Estimated Saving
≈ ${saving.toFixed(0)} BDT

━━━━━━━━━━━━━━

🏦 Today's TT Selling Rates

`;

  const medals = ["🥇","🥈","🥉"];

  banks.forEach((bank, index) => {

    const rank =
      medals[index] ??
      `${index + 1}.`;

    reply += `${rank} ${bank.bank.padEnd(8)} ${bank.sell.toFixed(4)}\n`;

  });

  const updated = new Date(data.generated_at);

  const formatted = updated.toLocaleString("en-GB", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });

  reply += `

  🕒 Updated
  ${formatted}`;

  await sendTelegramMessage(
    env,
    chatId,
    reply.trim()
  );

}

else if (
  text === "/status" ||
  text === "🟢 Status"
) {

  const data = await loadData();

  const updated = new Date(data.generated_at);

  const formatted =
    updated.toLocaleString("en-GB",{
      day:"2-digit",
      month:"short",
      hour:"2-digit",
      minute:"2-digit",
    });

  await sendTelegramMessage(
    env,
    chatId,
`🟢 EuroCompass Status

━━━━━━━━━━━━━━

System
✅ Online

Market
🟢 Live

Banks
${data.summary.banks_processed}

Best Bank
${data.summary.lowest_sell.bank}

Best TT Selling
${data.summary.lowest_sell.value.toFixed(4)}

Updated
${formatted}`
  );

}

else if (
  text.startsWith("/recommend") ||
  text === "💶 Recommend" ||
  pendingRecommendations.has(chatId)
) {

  if (text === "💶 Recommend") {

  pendingRecommendations.set(chatId, true);

  await sendTelegramMessage(
    env,
    chatId,
`💶 Germany Transfer

Please enter the EUR amount.

Example

11904`
  );

  return new Response("OK");

}

let parts;

if (pendingRecommendations.has(chatId) && !text.startsWith("/recommend")) {

  parts = ["/recommend", text];

  // don't delete yet

}
else {

  parts = text.split(" ");

}

if (parts.length !== 2) {

  await sendTelegramMessage(
    env,
    chatId,
`Usage

/recommend 12153`
  );

  return new Response("OK");

}

  const euroAmount = Number(parts[1]);

  if (isNaN(euroAmount) || euroAmount <= 0) {

  await sendTelegramMessage(
    env,
    chatId,
    `❌ Invalid amount.

    Please enter a valid EUR amount.

    Example

    11904`
    );

    return new Response("OK");

  }

// valid amount
pendingRecommendations.delete(chatId);

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
`🧭 EuroCompass

💶 Germany Transfer Analysis

━━━━━━━━━━━━━━

💶 Amount
€${euroAmount.toLocaleString()}

🏆 Best Bank
${best.bank}

💱 TT Selling
${best.rate.toFixed(4)} BDT/EUR

💵 Total Cost
${best.total_cost.toLocaleString(undefined,{
minimumFractionDigits:2,
maximumFractionDigits:2
})} BDT

💰 Estimated Saving
≈ ${savings.toLocaleString(undefined,{
minimumFractionDigits:0,
maximumFractionDigits:0
})} BDT

━━━━━━━━━━━━━━

✅ Recommendation

Transfer using ${best.bank} today.`
);

}

return new Response("OK");
	}

    return new Response("404 Not Found", {
      status: 404,
    });
  },
};