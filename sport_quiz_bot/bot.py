"""Sport quiz bot (Khmer): multiple-choice questions with buttons and a score."""

import logging
import os
import random
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

from questions import QUESTIONS

HERE = Path(__file__).resolve().parent
load_dotenv(HERE.parent / ".env")
BOT_TOKEN = os.getenv("QUIZ_BOT_TOKEN")
if not BOT_TOKEN:
    raise SystemExit("❌ QUIZ_BOT_TOKEN is missing. Put your bot token in the .env file: QUIZ_BOT_TOKEN=...")

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s", level=logging.INFO
)
# httpx logs request URLs, which contain the bot token
logging.getLogger("httpx").setLevel(logging.WARNING)

WELCOME_TEXT = (
    "🧠 សូមស្វាគមន៍មកកាន់ កម្រងសំណួរកីឡា!\n\n"
    "សាកល្បងចំណេះដឹងកីឡារបស់អ្នក — ជ្រើសចម្លើយដោយចុចប៊ូតុង។ ⚽🏀🏸\n\n"
    "ពាក្យបញ្ជា៖\n"
    "/quiz — ចាប់ផ្តើមសំណួរ\n"
    "/score — មើលពិន្ទុរបស់អ្នក\n"
    "/reset — លុបពិន្ទុ ហើយចាប់ផ្តើមថ្មី\n"
    "/help — បង្ហាញសារនេះម្តងទៀត"
)

LETTERS = ["ក", "ខ", "គ", "ឃ"]


async def send_question(chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
    qid = random.randrange(len(QUESTIONS))
    item = QUESTIONS[qid]
    buttons = [
        [InlineKeyboardButton(f"{LETTERS[i]}. {opt}", callback_data=f"ans:{qid}:{i}")]
        for i, opt in enumerate(item["options"])
    ]
    await context.bot.send_message(
        chat_id,
        f"❓ <b>{item['q']}</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(WELCOME_TEXT)


async def quiz(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await send_question(update.effective_chat.id, context)


async def on_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    _, qid, choice = query.data.split(":")
    item = QUESTIONS[int(qid)]
    correct = int(choice) == item["answer"]

    score = context.user_data.setdefault("score", {"correct": 0, "total": 0})
    score["total"] += 1
    if correct:
        score["correct"] += 1

    await query.answer("✅ ត្រូវហើយ!" if correct else "❌ ខុសហើយ!")
    result = "✅ <b>ត្រឹមត្រូវ!</b>" if correct else "❌ <b>មិនត្រឹមត្រូវទេ។</b>"
    answer_text = item["options"][item["answer"]]
    await query.edit_message_text(
        f"❓ <b>{item['q']}</b>\n\n"
        f"{result}\n"
        f"ចម្លើយត្រូវ៖ <b>{answer_text}</b>\n"
        f"💡 {item['explain']}\n\n"
        f"📊 ពិន្ទុ៖ {score['correct']}/{score['total']}",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("➡️ សំណួរបន្ទាប់", callback_data="next")]]
        ),
    )


async def on_next(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    await query.edit_message_reply_markup(None)  # stop double-clicking "next"
    await send_question(query.message.chat_id, context)


async def score(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    s = context.user_data.get("score", {"correct": 0, "total": 0})
    if s["total"] == 0:
        await update.message.reply_text("អ្នកមិនទាន់បានឆ្លើយសំណួរណាមួយទេ។ ចុច /quiz ដើម្បីចាប់ផ្តើម!")
        return
    percent = round(s["correct"] * 100 / s["total"])
    await update.message.reply_text(
        f"📊 ពិន្ទុរបស់អ្នក៖ {s['correct']}/{s['total']} ({percent}%)"
    )


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data["score"] = {"correct": 0, "total": 0}
    await update.message.reply_text("🔄 បានលុបពិន្ទុហើយ។ ចុច /quiz ដើម្បីចាប់ផ្តើមថ្មី!")


async def post_init(app: Application) -> None:
    await app.bot.set_my_commands(
        [
            BotCommand("quiz", "ចាប់ផ្តើមសំណួរកីឡា"),
            BotCommand("score", "មើលពិន្ទុរបស់អ្នក"),
            BotCommand("reset", "លុបពិន្ទុ"),
            BotCommand("help", "បង្ហាញជំនួយ"),
        ]
    )


def main() -> None:
    persistence = PicklePersistence(filepath=HERE / "quiz_data.pickle")
    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .persistence(persistence)
        .post_init(post_init)
        .build()
    )
    app.add_handler(CommandHandler(["start", "help"], start))
    app.add_handler(CommandHandler("quiz", quiz))
    app.add_handler(CommandHandler("score", score))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(CallbackQueryHandler(on_answer, pattern=r"^ans:"))
    app.add_handler(CallbackQueryHandler(on_next, pattern=r"^next$"))
    app.run_polling()


if __name__ == "__main__":
    main()
