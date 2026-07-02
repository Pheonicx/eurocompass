import asyncio
import logging
import os
import sys
import locale
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

locale.setlocale(locale.LC_ALL, "")

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

from dashboard.calculator import calculate_transfer_cost
from services.market_service import get_rates, recommend_bank


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def format_bdt(value):
    return f"{value:,.2f} BDT"


def format_eur(value):
    return f"€{value:,.0f}" if value.is_integer() else f"€{value:,.2f}"


def format_rate(value):
    return f"{float(value):.4f}"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.reply_text(
            "🧭 EuroCompass\n\n"
            "Cloud-powered EUR Exchange Rate Intelligence\n\n"
            "Available commands\n\n"
            "/rates\n"
            "/recommend <EUR amount>\n"
            "/refresh"
        )
    except Exception:
        logger.exception("Failed to handle /start")


async def rates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        banks = get_rates()

        if not banks:
            await update.message.reply_text("No market data available.")
            return

        medals = ["🥇", "🥈", "🥉"]
        lines = ["🏦 Today's EUR TT Selling Rates", ""]

        for index, bank in enumerate(banks):
            rank = medals[index] if index < len(medals) else f"{index + 1}."
            lines.extend([
                f"{rank} {bank['bank']}",
                f"TT Selling : {format_rate(bank['sell'])}",
                "",
            ])

        await update.message.reply_text("\n".join(lines).strip())

    except Exception:
        logger.exception("Failed to handle /rates")
        await update.message.reply_text("Could not load rates.")


async def recommend(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not context.args:
            await update.message.reply_text("Usage: /recommend <EUR amount>")
            return

        amount_text = "".join(context.args).replace(",", "")
        euro_amount = float(amount_text)

        if euro_amount <= 0:
            await update.message.reply_text("Amount must be greater than zero.")
            return

        recommendation = recommend_bank(euro_amount)
        banks = get_rates()

        if not recommendation or not banks:
            await update.message.reply_text("No market data available.")
            return

        results = calculate_transfer_cost(banks, euro_amount)
        most_expensive = max(results, key=lambda item: item["total_cost"])
        savings = most_expensive["total_cost"] - recommendation["total_cost"]

        message = (
            "💶 Germany Transfer\n\n"
            "Amount:\n"
            f"{format_eur(euro_amount)}\n\n"
            "🏆 Recommended Bank\n\n"
            f"{recommendation['bank']}\n\n"
            "TT Selling:\n"
            f"{format_rate(recommendation['rate'])}\n\n"
            "Estimated Cost:\n"
            f"{format_bdt(recommendation['total_cost'])}\n\n"
            "Savings Compared With Most Expensive Bank:\n"
            f"{format_bdt(savings)}"
        )

        await update.message.reply_text(message)

    except ValueError:
        await update.message.reply_text("Please provide a valid EUR amount.")
    except Exception:
        logger.exception("Failed to handle /recommend")
        await update.message.reply_text("Could not calculate recommendation.")


async def refresh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.reply_text("Refreshing market...")

        process = await asyncio.create_subprocess_exec(
            sys.executable,
            str(PROJECT_ROOT / "main.py"),
            cwd=str(PROJECT_ROOT),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            logger.error(
                "Market refresh failed with code %s\nstdout=%s\nstderr=%s",
                process.returncode,
                stdout.decode(errors="replace"),
                stderr.decode(errors="replace"),
            )
            await update.message.reply_text("Market refresh failed.")
            return

        logger.info("Market refresh completed successfully")
        banks = get_rates()

        if banks:
            best = banks[0]

            message = (
                "✅ Market Updated\n\n"
                f"🏆 Best TT Selling\n\n"
                f"{best['bank']}\n"
                f"{format_rate(best['sell'])}"
            )

            await update.message.reply_text(message)
        else:
            await update.message.reply_text("Market updated successfully.")

    except Exception:
        logger.exception("Failed to handle /refresh")
        await update.message.reply_text("Market refresh failed.")


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.exception("Unhandled bot error", exc_info=context.error)


def main():
    load_dotenv(PROJECT_ROOT / ".env")

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is missing from .env")

    application = ApplicationBuilder().token(token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("rates", rates))
    application.add_handler(CommandHandler("recommend", recommend))
    application.add_handler(CommandHandler("refresh", refresh))
    application.add_error_handler(error_handler)

    logger.info("EuroCompass Telegram bot started")
    application.run_polling()


if __name__ == "__main__":
    main()
