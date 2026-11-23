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

    if not banks:
        send_message(
            token,
            chat_id,
            "🧭 EuroCompass Daily Brief\n\n"
            "⚠️ No bank data available today — every collector "
            "appears to have failed this cycle. Please check the "
            "dashboard or collector_status.json directly.",
        )
        return

    best = banks[0]
    worst = banks[-1]

    spread = worst["sell"] - best["sell"]

    saving = spread * 12153

    # Find best student rate if available
    student_banks = [b for b in banks if b.get("student")]
    best_student = None
    if student_banks:
        best_student = min(
            student_banks,
            key=lambda x: x.get("student", {}).get("rate", float('inf'))
        )

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

"""

    if best_student:
        student_rate = best_student.get("student", {}).get("rate", best_student.get("student", {}).get("sell"))
        message += f"📚 Best Student Rate\n{best_student['bank']}\n{student_rate:.4f} BDT/EUR\n\n"

    message += "━━━━━━━━━━━━━━\n\n"

    medals = ["🥇", "🥈", "🥉"]

    for i, bank in enumerate(banks):

        rank = medals[i] if i < 3 else f"{i+1}."

        line = f"{rank} {bank['bank']:<8} {bank['sell']:.4f}"

        if bank.get("student"):
            student_rate = bank.get("student", {}).get("rate", bank.get("student", {}).get("sell"))
            line += f" (📚 {student_rate:.4f})"

        message += line + "\n"

    send_message(
        token,
        chat_id,
        message,
    )


if __name__ == "__main__":
    main()