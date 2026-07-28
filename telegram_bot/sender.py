import os
import requests

from dotenv import load_dotenv

load_dotenv()


def _is_markdown_parse_error(response) -> bool:
    """
    Telegram returns HTTP 400 with a specific "can't parse entities"
    description when parse_mode="Markdown" text contains unbalanced
    special characters (_, *, `, [) -- something raw exception text or
    validation-rejection reasons can easily trigger without any actual
    formatting having been intended. Only this specific failure should
    trigger a plain-text retry; any other 400 (bad chat_id, etc.) should
    still fail loudly rather than be silently swallowed.
    """
    if response.status_code != 400:
        return False
    try:
        description = response.json().get("description", "")
    except (ValueError, AttributeError):
        return False
    return "can't parse entities" in description.lower()


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

    if response.status_code == 400 and _is_markdown_parse_error(response):
        # The message itself (often raw exception text this code doesn't
        # control) broke Markdown parsing. Losing bold/italic formatting
        # is fine; losing the alert entirely is not -- retry once as
        # plain text with the exact same content. Build a fresh dict
        # rather than mutating `payload` in place, so what the first
        # request actually sent stays intact and inspectable.
        plain_payload = {
            "chat_id": chat_id,
            "text": message,
        }
        response = requests.post(
            url,
            json=plain_payload,
            timeout=20,
        )

    response.raise_for_status()

    return response.json()
if __name__ == "__main__":

    send_notification(
        "🧭 EuroCompass\n\n"
        "Cloud notification test successful!"
    )