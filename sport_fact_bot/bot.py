"""Sport fact bot (Khmer): "Did you know?" facts with a refresh button and daily delivery."""

import logging
import os
import random
from datetime import time
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from telegram import BotCommand, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.error import Forbidden
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    PicklePersistence,
)

from facts import FACTS

HERE = Path(__file__).resolve().parent
load_dotenv(HERE.parent / ".env")
BOT_TOKEN = os.getenv("FACT_BOT_TOKEN")
if not BOT_TOKEN:
    raise SystemExit("❌ FACT_BOT_TOKEN is missing. Put your bot token in the .env file: FACT_BOT_TOKEN=...")
TIMEZONE = ZoneInfo(os.getenv("TIMEZONE", "Asia/Phnom_Penh"))
DAILY_HOUR = int(os.getenv("DAILY_HOUR", "7"))
DAILY_MINUTE = int(os.getenv("DAILY_MINUTE", "0"))

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s", level=logging.INFO
)
# httpx logs request URLs, which contain the bot token
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

WELCOME_TEXT = (
    "📚 សូមស្វាគមន៍មកកាន់ «តើអ្នកដឹងទេ? — កីឡា»!\n\n"
    "ស្វែងយល់ការពិតគួរឲ្យភ្ញាក់ផ្អើលអំពីពិភពកីឡា។ 🌍\n\n"
    "ពាក្យបញ្ជា៖\n"
    "/fact — ទទួលការពិតកីឡាមួយ\n"
    "/subscribe — ទទួលការពិតកីឡារៀងរាល់ថ្ងៃ\n"
    "/unsubscribe — ឈប់ទទួលប្រចាំថ្ងៃ\n"
    "/help — បង្ហាញសារនេះម្តងទៀត"
)


def pick_fact(exclude: int = -1) -> int:
    choices = [i for i in range(len(FACTS)) if i != exclude]
    return random.choice(choices)


def fact_message(idx: int):
    text = f"💡 <b>តើអ្នកដឹងទេ?</b>\n\n{FACTS[idx]}"
    markup = InlineKeyboardMarkup(
        [[InlineKeyboardButton("🔄 ការពិតមួយទៀត", callback_data=f"more:{idx}")]]
    )
    return text, markup


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(WELCOME_TEXT)


async def fact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text, markup = fact_message(pick_fact())
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=markup)


async def on_more(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    current = int(query.data.split(":")[1])
    text, markup = fact_message(pick_fact(exclude=current))
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=markup)


async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    subs = context.bot_data.setdefault("subscribers", set())
    chat_id = update.effective_chat.id
    if chat_id in subs:
        await update.message.reply_text("✅ អ្នកបានជាវរួចហើយ។")
        return
    subs.add(chat_id)
    await update.message.reply_text(
        f"✅ ជាវបានជោគជ័យ! អ្នកនឹងទទួលការពិតកីឡារៀងរាល់ថ្ងៃ "
        f"ម៉ោង {DAILY_HOUR:02d}:{DAILY_MINUTE:02d}។"
    )


async def unsubscribe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    subs = context.bot_data.setdefault("subscribers", set())
    chat_id = update.effective_chat.id
    if chat_id not in subs:
        await update.message.reply_text("ℹ️ អ្នកមិនទាន់បានជាវនៅឡើយទេ។")
        return
    subs.discard(chat_id)
    await update.message.reply_text("🛑 បានឈប់ផ្ញើការពិតកីឡាប្រចាំថ្ងៃហើយ។")


async def send_daily(context: ContextTypes.DEFAULT_TYPE) -> None:
    subs = context.bot_data.setdefault("subscribers", set())
    for chat_id in list(subs):
        text, markup = fact_message(pick_fact())
        try:
            await context.bot.send_message(
                chat_id, text, parse_mode=ParseMode.HTML, reply_markup=markup
            )
        except Forbidden:
            subs.discard(chat_id)  # user blocked the bot
        except Exception:
            logger.exception("Failed to send daily fact to %s", chat_id)


async def post_init(app: Application) -> None:
    await app.bot.set_my_commands(
        [
            BotCommand("fact", "ទទួលការពិតកីឡាមួយ"),
            BotCommand("subscribe", "ទទួលការពិតកីឡារៀងរាល់ថ្ងៃ"),
            BotCommand("unsubscribe", "ឈប់ទទួលប្រចាំថ្ងៃ"),
            BotCommand("help", "បង្ហាញជំនួយ"),
        ]
    )
    app.job_queue.run_daily(
        send_daily, time=time(DAILY_HOUR, DAILY_MINUTE, tzinfo=TIMEZONE)
    )


def main() -> None:
    persistence = PicklePersistence(filepath=HERE / "fact_data.pickle")
    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .persistence(persistence)
        .post_init(post_init)
        .build()
    )
    app.add_handler(CommandHandler(["start", "help"], start))
    app.add_handler(CommandHandler("fact", fact))
    app.add_handler(CommandHandler("subscribe", subscribe))
    app.add_handler(CommandHandler("unsubscribe", unsubscribe))
    app.add_handler(CallbackQueryHandler(on_more, pattern=r"^more:"))
    app.run_polling()


if __name__ == "__main__":
    main()
