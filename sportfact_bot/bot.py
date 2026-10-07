"""Sportfact bot (Khmer): button-driven sport knowledge + a quick quiz to test yourself."""

import logging
import os
import random
import sys
from pathlib import Path

from dotenv import load_dotenv
from telegram import BotCommand, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    PicklePersistence,
)

HERE = Path(__file__).resolve().parent
# Reuse the content of the fact bot and the quiz bot.
sys.path.insert(0, str(HERE.parent / "sport_fact_bot"))
sys.path.insert(0, str(HERE.parent / "sport_quiz_bot"))
from facts import FACTS  # noqa: E402
from questions import QUESTIONS  # noqa: E402

load_dotenv(HERE.parent / ".env")
BOT_TOKEN = os.getenv("SPORTFACT_BOT_TOKEN")
if not BOT_TOKEN:
    raise SystemExit("❌ SPORTFACT_BOT_TOKEN is missing. Put your bot token in the .env file: SPORTFACT_BOT_TOKEN=...")

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s", level=logging.INFO
)
# httpx logs request URLs, which contain the bot token
logging.getLogger("httpx").setLevel(logging.WARNING)

WELCOME_TEXT = (
    "🧠 សូមស្វាគមន៍មកកាន់ <b>Sportfact!</b>\n\n"
    "ស្វែងយល់ពីចំណេះដឹងកីឡាដែលគួរឱ្យចាប់អារម្មណ៍ និងសាកល្បងចំណេះដឹងរបស់អ្នក។\n\n"
    "ចុចប៊ូតុងខាងក្រោម ដើម្បីចាប់ផ្តើម។"
)

BTN_FACT = InlineKeyboardButton("🧠 ចំណេះដឹងកីឡា", callback_data="fact")
BTN_MORE = InlineKeyboardButton("🔄 ចំណេះដឹងមួយទៀត", callback_data="fact")
BTN_QUIZ = InlineKeyboardButton("❓ សាកល្បងចំណេះដឹង", callback_data="quiz")
BTN_HOME = InlineKeyboardButton("🏠 ទំព័រដើម", callback_data="home")

LETTERS = ["ក", "ខ", "គ", "ឃ"]


# ---------- message builders ----------

def welcome_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[BTN_FACT], [BTN_MORE]])


def fact_text(context: ContextTypes.DEFAULT_TYPE) -> str:
    last = context.user_data.get("last_fact", -1)
    idx = random.choice([i for i in range(len(FACTS)) if i != last])
    context.user_data["last_fact"] = idx
    return f"💡 <b>តើអ្នកដឹងទេ?</b>\n\n{FACTS[idx]}"


def fact_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[BTN_MORE], [BTN_QUIZ], [BTN_HOME]])


def quiz_message(context: ContextTypes.DEFAULT_TYPE):
    qid = random.randrange(len(QUESTIONS))
    item = QUESTIONS[qid]
    buttons = [
        [InlineKeyboardButton(f"{LETTERS[i]}. {opt}", callback_data=f"ans:{qid}:{i}")]
        for i, opt in enumerate(item["options"])
    ]
    return f"❓ <b>{item['q']}</b>", InlineKeyboardMarkup(buttons)


# ---------- handlers ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        WELCOME_TEXT, parse_mode=ParseMode.HTML, reply_markup=welcome_markup()
    )


async def fact_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        fact_text(context), parse_mode=ParseMode.HTML, reply_markup=fact_markup()
    )


async def quiz_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text, markup = quiz_message(context)
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=markup)


async def on_fact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    text = fact_text(context)
    if query.message.text and query.message.text.startswith("💡"):
        # Already a fact message: swap the fact in place.
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=fact_markup())
    else:
        # From the welcome or a quiz result: keep that message, send a new one.
        await query.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=fact_markup())


async def on_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    await query.edit_message_reply_markup(None)
    text, markup = quiz_message(context)
    await query.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=markup)


async def on_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    _, qid, choice = query.data.split(":")
    item = QUESTIONS[int(qid)]
    correct = int(choice) == item["answer"]

    score = context.user_data.setdefault("score", {"correct": 0, "total": 0})
    score["total"] += 1
    score["correct"] += int(correct)

    await query.answer("✅ ត្រូវហើយ!" if correct else "❌ ខុសហើយ!")
    result = "✅ <b>ត្រឹមត្រូវ!</b>" if correct else "❌ <b>មិនត្រឹមត្រូវទេ។</b>"
    await query.edit_message_text(
        f"❓ <b>{item['q']}</b>\n\n"
        f"{result}\n"
        f"ចម្លើយត្រូវ៖ <b>{item['options'][item['answer']]}</b>\n"
        f"💡 {item['explain']}\n\n"
        f"📊 ពិន្ទុ៖ {score['correct']}/{score['total']}",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("➡️ សំណួរបន្ទាប់", callback_data="quiz")],
                [BTN_FACT],
                [BTN_HOME],
            ]
        ),
    )


async def on_home(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    await query.edit_message_reply_markup(None)
    await query.message.reply_text(
        WELCOME_TEXT, parse_mode=ParseMode.HTML, reply_markup=welcome_markup()
    )


async def post_init(app: Application) -> None:
    await app.bot.set_my_commands(
        [
            BotCommand("start", "ទំព័រដើម"),
            BotCommand("fact", "ចំណេះដឹងកីឡា"),
            BotCommand("quiz", "សាកល្បងចំណេះដឹង"),
        ]
    )


def main() -> None:
    persistence = PicklePersistence(filepath=HERE / "sportfact_data.pickle")
    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .persistence(persistence)
        .post_init(post_init)
        .build()
    )
    app.add_handler(CommandHandler(["start", "help"], start))
    app.add_handler(CommandHandler("fact", fact_cmd))
    app.add_handler(CommandHandler("quiz", quiz_cmd))
    app.add_handler(CallbackQueryHandler(on_fact, pattern=r"^fact$"))
    app.add_handler(CallbackQueryHandler(on_quiz, pattern=r"^quiz$"))
    app.add_handler(CallbackQueryHandler(on_answer, pattern=r"^ans:"))
    app.add_handler(CallbackQueryHandler(on_home, pattern=r"^home$"))
    app.run_polling()


if __name__ == "__main__":
    main()
