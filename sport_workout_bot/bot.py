"""Sport workout bot (Khmer): pick a level from a button menu, get a workout, track progress."""

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

from workouts import LEVELS, TIPS, WORKOUTS

HERE = Path(__file__).resolve().parent
load_dotenv(HERE.parent / ".env")
BOT_TOKEN = os.getenv("WORKOUT_BOT_TOKEN")
if not BOT_TOKEN:
    raise SystemExit("❌ WORKOUT_BOT_TOKEN is missing. Put your bot token in the .env file: WORKOUT_BOT_TOKEN=...")

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s", level=logging.INFO
)
# httpx logs request URLs, which contain the bot token
logging.getLogger("httpx").setLevel(logging.WARNING)

WELCOME_TEXT = (
    "💪 សូមស្វាគមន៍មកកាន់ គ្រូបង្វឹកកីឡា!\n\n"
    "ជ្រើសកម្រិតរបស់អ្នក ហើយទទួលលំហាត់ប្រាណសម្រាប់ថ្ងៃនេះ។ 🏋️\n\n"
    "ពាក្យបញ្ជា៖\n"
    "/workout — ជ្រើសលំហាត់តាមកម្រិត\n"
    "/tip — គន្លឹះសុខភាព និងការហាត់ប្រាណ\n"
    "/done — កត់ត្រាថាអ្នកហាត់រួចហើយ\n"
    "/stats — មើលចំនួនដងដែលអ្នកបានហាត់\n"
    "/help — បង្ហាញសារនេះម្តងទៀត"
)

MENU_TEXT = "🏋️ <b>ជ្រើសកម្រិតលំហាត់របស់អ្នក៖</b>"


def level_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(label, callback_data=f"lvl:{key}")]
         for key, label in LEVELS.items()]
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(WELCOME_TEXT)


async def workout(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        MENU_TEXT, parse_mode=ParseMode.HTML, reply_markup=level_menu()
    )


async def on_level(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    level = query.data.split(":")[1]
    routine = random.choice(WORKOUTS[level])
    await query.edit_message_text(
        f"<b>លំហាត់ថ្ងៃនេះ — {LEVELS[level]}</b>\n\n{routine}\n\n"
        "ហាត់រួចហើយ? ចុចប៊ូតុងខាងក្រោម ✅",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("✅ ហាត់រួចហើយ", callback_data="done")],
                [InlineKeyboardButton("🔄 លំហាត់ផ្សេង", callback_data=f"lvl:{level}")],
                [InlineKeyboardButton("⬅️ ត្រឡប់ក្រោយ", callback_data="menu")],
            ]
        ),
    )


async def on_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        MENU_TEXT, parse_mode=ParseMode.HTML, reply_markup=level_menu()
    )


def record_done(context: ContextTypes.DEFAULT_TYPE) -> str:
    count = context.user_data.get("done", 0) + 1
    context.user_data["done"] = count
    return f"🎉 អស្ចារ្យណាស់! អ្នកបានហាត់សរុប {count} ដងហើយ។ បន្តទៀត! 💪"


async def on_done_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer("✅")
    await query.edit_message_reply_markup(None)  # one tap per workout
    await query.message.reply_text(record_done(context))


async def done(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(record_done(context))


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    count = context.user_data.get("done", 0)
    if count == 0:
        await update.message.reply_text("អ្នកមិនទាន់បានហាត់នៅឡើយទេ។ ចុច /workout ដើម្បីចាប់ផ្តើម!")
    else:
        await update.message.reply_text(f"📊 អ្នកបានហាត់សរុប {count} ដង។")


async def tip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(random.choice(TIPS))


async def post_init(app: Application) -> None:
    await app.bot.set_my_commands(
        [
            BotCommand("workout", "ជ្រើសលំហាត់តាមកម្រិត"),
            BotCommand("tip", "គន្លឹះសុខភាព"),
            BotCommand("done", "កត់ត្រាថាហាត់រួច"),
            BotCommand("stats", "មើលចំនួនដងដែលបានហាត់"),
            BotCommand("help", "បង្ហាញជំនួយ"),
        ]
    )


def main() -> None:
    persistence = PicklePersistence(filepath=HERE / "workout_data.pickle")
    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .persistence(persistence)
        .post_init(post_init)
        .build()
    )
    app.add_handler(CommandHandler(["start", "help"], start))
    app.add_handler(CommandHandler("workout", workout))
    app.add_handler(CommandHandler("tip", tip))
    app.add_handler(CommandHandler("done", done))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CallbackQueryHandler(on_level, pattern=r"^lvl:"))
    app.add_handler(CallbackQueryHandler(on_menu, pattern=r"^menu$"))
    app.add_handler(CallbackQueryHandler(on_done_button, pattern=r"^done$"))
    app.run_polling()


if __name__ == "__main__":
    main()
