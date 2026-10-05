"""Telegram bot that sends short, well-known sport quotes in Khmer."""

import json
import logging
import os
import random
from datetime import time
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from telegram import BotCommand, Update
from telegram.constants import ParseMode
from telegram.error import Forbidden
from telegram.ext import Application, CommandHandler, ContextTypes

from quotes import QUOTES

load_dotenv()

BOT_TOKEN = os.environ["BOT_TOKEN"]
TIMEZONE = ZoneInfo(os.getenv("TIMEZONE", "Asia/Phnom_Penh"))
DAILY_HOUR = int(os.getenv("DAILY_HOUR", "7"))
DAILY_MINUTE = int(os.getenv("DAILY_MINUTE", "0"))
SUBSCRIBERS_FILE = Path(__file__).with_name("subscribers.json")

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

WELCOME_TEXT = (
    "👋 សូមស្វាគមន៍!\n\n"
    "បូតនេះផ្ញើសម្រង់សម្តីល្បីៗពីពិភពកីឡា ឲ្យអ្នកគិត — ម្តងមួយ ខ្លី និងច្បាស់។ ⚽🏀🥊\n\n"
    "ពាក្យបញ្ជា៖\n"
    "/quote — ទទួលសម្រង់សម្តីកីឡាចៃដន្យ\n"
    "/subscribe — ទទួលសម្រង់សម្តីរៀងរាល់ថ្ងៃដោយស្វ័យប្រវត្តិ\n"
    "/unsubscribe — ឈប់ទទួលសម្រង់សម្តីប្រចាំថ្ងៃ\n"
    "/help — បង្ហាញសារនេះម្តងទៀត"
)


# ---------- subscriber storage ----------

def load_subscribers() -> set:
    if SUBSCRIBERS_FILE.exists():
        return set(json.loads(SUBSCRIBERS_FILE.read_text()))
    return set()


def save_subscribers(subs: set) -> None:
    SUBSCRIBERS_FILE.write_text(json.dumps(sorted(subs)))


# ---------- helpers ----------

def random_quote() -> str:
    text, author = random.choice(QUOTES)
    return f"🏆 <i>«{text}»</i>\n\n— <b>{author}</b>"


# ---------- command handlers ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(WELCOME_TEXT)


async def quote(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(random_quote(), parse_mode=ParseMode.HTML)


async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    subs = context.bot_data["subscribers"]
    chat_id = update.effective_chat.id
    if chat_id in subs:
        await update.message.reply_text("✅ អ្នកបានជាវរួចហើយ។")
        return
    subs.add(chat_id)
    save_subscribers(subs)
    await update.message.reply_text(
        f"✅ ជាវបានជោគជ័យ! អ្នកនឹងទទួលសម្រង់សម្តីកីឡារៀងរាល់ថ្ងៃ "
        f"ម៉ោង {DAILY_HOUR:02d}:{DAILY_MINUTE:02d}។"
    )


async def unsubscribe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    subs = context.bot_data["subscribers"]
    chat_id = update.effective_chat.id
    if chat_id not in subs:
        await update.message.reply_text("ℹ️ អ្នកមិនទាន់បានជាវនៅឡើយទេ។")
        return
    subs.discard(chat_id)
    save_subscribers(subs)
    await update.message.reply_text("🛑 បានឈប់ផ្ញើសម្រង់សម្តីប្រចាំថ្ងៃហើយ។")


# ---------- daily job ----------

async def send_daily(context: ContextTypes.DEFAULT_TYPE) -> None:
    subs = context.bot_data["subscribers"]
    blocked = set()
    for chat_id in list(subs):
        try:
            await context.bot.send_message(
                chat_id, random_quote(), parse_mode=ParseMode.HTML
            )
        except Forbidden:
            blocked.add(chat_id)  # user blocked the bot
        except Exception:
            logger.exception("Failed to send daily quote to %s", chat_id)
    if blocked:
        subs -= blocked
        save_subscribers(subs)


async def post_init(app: Application) -> None:
    app.bot_data["subscribers"] = load_subscribers()
    await app.bot.set_my_commands(
        [
            BotCommand("quote", "ទទួលសម្រង់សម្តីកីឡាចៃដន្យ"),
            BotCommand("subscribe", "ទទួលសម្រង់សម្តីរៀងរាល់ថ្ងៃ"),
            BotCommand("unsubscribe", "ឈប់ទទួលសម្រង់សម្តីប្រចាំថ្ងៃ"),
            BotCommand("help", "បង្ហាញជំនួយ"),
        ]
    )
    app.job_queue.run_daily(
        send_daily, time=time(DAILY_HOUR, DAILY_MINUTE, tzinfo=TIMEZONE)
    )


def main() -> None:
    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler(["start", "help"], start))
    app.add_handler(CommandHandler("quote", quote))
    app.add_handler(CommandHandler("subscribe", subscribe))
    app.add_handler(CommandHandler("unsubscribe", unsubscribe))
    logger.info("Bot is running…")
    app.run_polling()


if __name__ == "__main__":
    main()
