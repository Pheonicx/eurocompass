import json
import os
from datetime import datetime

import requests


EXPORT_FILE = "exports/latest.json"


def load_data():
    with open(EXPORT_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def send_message(token, chat_id, text):
    url = f"https://api.telegram.org/bot{token}/sendMessage"

    response = requests.post(
        url,
        json={
            "chat_id": chat_id,
            "text": text,
        },
        timeout=30,
    )

    response.raise_for_status()


def main():

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not token:
        raise RuntimeError("Missing TELEGRAM_BOT_TOKEN")

    if not chat_id:
        raise RuntimeError("Missing TELEGRAM_CHAT_ID")

    data = load_data()

    banks = sorted(
        data["banks"],
        key=lambda x: x["sell"],
    )

    best = banks[0]
    worst = banks[-1]

    spread = worst["sell"] - best["sell"]

    saving = spread * 12153

    updated = datetime.fromisoformat(
        data["generated_at"]
    )

    message = f"""🧭 EuroCompass Daily Brief

📅 {updated.strftime("%d %b %Y")}
🕘 09:00 Bangladesh Time

🏆 Best Bank
{best["bank"]}

💱 TT Selling
{best["sell"]:.4f} BDT/EUR

💰 Estimated Saving
≈ {saving:,.0f} BDT

📊 Market Spread
{spread:.4f} BDT

━━━━━━━━━━━━━━

"""

    medals = ["🥇", "🥈", "🥉"]

    for i, bank in enumerate(banks):

        rank = medals[i] if i < 3 else f"{i+1}."

        message += (
            f"{rank} "
            f"{bank['bank']:<8} "
            f"{bank['sell']:.4f}\n"
        )

    send_message(
        token,
        chat_id,
        message,
    )


if __name__ == "__main__":
    main()