import os
import requests

from dotenv import load_dotenv

load_dotenv()


def send_notification(message: str):
    """
    Send a Telegram message without starting the bot.
    """

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not token:
        raise RuntimeError("Missing TELEGRAM_BOT_TOKEN")

    if not chat_id:
        raise RuntimeError("Missing TELEGRAM_CHAT_ID")

    url = (
        f"https://api.telegram.org/bot{token}/sendMessage"
    )

    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown",
    }

    response = requests.post(
        url,
        json=payload,
        timeout=20,
    )

    response.raise_for_status()

    return response.json()
if __name__ == "__main__":

    send_notification(
        "🧭 EuroCompass\n\n"
        "Cloud notification test successful!"
    )