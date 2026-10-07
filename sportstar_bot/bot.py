"""SportStar bot (Khmer): browse famous athletes by sport and play "guess the athlete"."""

import logging
import os
import random
from pathlib import Path

from dotenv import load_dotenv
from telegram import BotCommand, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.error import BadRequest
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    PicklePersistence,
)

from stars import CATEGORIES, STARS

HERE = Path(__file__).resolve().parent
load_dotenv(HERE.parent / ".env")
BOT_TOKEN = os.getenv("SPORTSTAR_BOT_TOKEN")
if not BOT_TOKEN:
    raise SystemExit("❌ SPORTSTAR_BOT_TOKEN is missing. Put your bot token in the .env file: SPORTSTAR_BOT_TOKEN=...")

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s", level=logging.INFO
)
# httpx logs request URLs, which contain the bot token
logging.getLogger("httpx").setLevel(logging.WARNING)

WELCOME_TEXT = (
    "⭐ សូមស្វាគមន៍មកកាន់ <b>SportStar!</b>\n\n"
    "ស្គាល់កីឡាករល្បីៗលើពិភពលោក និងលេងហ្គេមទាយឈ្មោះកីឡាករ។\n\n"
    "ជ្រើសប៊ូតុងខាងក្រោម ដើម្បីចាប់ផ្តើម។"
)

BTN_HOME = InlineKeyboardButton("🏠 ទំព័រដើម", callback_data="home")
POINTS = [3, 2, 1]  # points for a correct guess after 1, 2 or 3 hints


# ---------- screens (text, markup) ----------

def home_screen():
    return WELCOME_TEXT, InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("⭐ ស្គាល់កីឡាករ", callback_data="cats")],
            [InlineKeyboardButton("🎯 ទាយកីឡាករ", callback_data="game")],
            [InlineKeyboardButton("🏆 ពិន្ទុរបស់ខ្ញុំ", callback_data="points")],
        ]
    )


def categories_screen():
    rows = [[InlineKeyboardButton(label, callback_data=f"cat:{key}")]
            for key, label in CATEGORIES.items()]
    rows.append([BTN_HOME])
    return "⭐ <b>ជ្រើសប្រភេទកីឡា៖</b>", InlineKeyboardMarkup(rows)


def category_screen(cat: str):
    rows = [[InlineKeyboardButton(f"{s['flag']} {s['name']}", callback_data=f"star:{i}")]
            for i, s in enumerate(STARS) if s["cat"] == cat]
    rows.append([InlineKeyboardButton("⬅️ ត្រឡប់ក្រោយ", callback_data="cats")])
    return f"<b>{CATEGORIES[cat]}</b>\n\nជ្រើសកីឡាករ៖", InlineKeyboardMarkup(rows)


def star_screen(sid: int):
    s = STARS[sid]
    facts = "\n".join(f"• {f}" for f in s["facts"])
    return (
        f"{s['flag']} <b>{s['name']}</b>\n{CATEGORIES[s['cat']]}\n\n{facts}",
        InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("⬅️ ត្រឡប់ក្រោយ", callback_data=f"cat:{s['cat']}")],
                [BTN_HOME],
            ]
        ),
    )


def game_screen(game: dict):
    s = STARS[game["sid"]]
    shown = game["hints"]
    hints = "\n".join(f"{i + 1}. {h}" for i, h in enumerate(s["hints"][:shown]))
    rows = [[InlineKeyboardButton(STARS[o]["name"], callback_data=f"pick:{game['id']}:{o}")]
            for o in game["options"]]
    if shown < len(s["hints"]):
        rows.append([InlineKeyboardButton("💡 ជំនួយបន្ថែម", callback_data=f"hint:{game['id']}")])
    return (
        f"🎯 <b>តើខ្ញុំជានរណា?</b>\n\n{hints}\n\n"
        f"ទាយត្រូវឥឡូវ បាន <b>{POINTS[shown - 1]} ពិន្ទុ</b>",
        InlineKeyboardMarkup(rows),
    )


# ---------- helpers ----------

async def show(query, screen) -> None:
    text, markup = screen
    try:
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=markup)
    except BadRequest as e:
        if "not modified" not in str(e):
            raise


def new_game(context: ContextTypes.DEFAULT_TYPE) -> dict:
    sid = random.randrange(len(STARS))
    others = random.sample([i for i in range(len(STARS)) if i != sid], 3)
    options = others + [sid]
    random.shuffle(options)
    game = {"id": context.user_data.get("game_id", 0) + 1, "sid": sid,
            "options": options, "hints": 1}
    context.user_data["game_id"] = game["id"]
    context.user_data["game"] = game
    return game


def current_game(context: ContextTypes.DEFAULT_TYPE, gid: str):
    game = context.user_data.get("game")
    return game if game and str(game["id"]) == gid else None


# ---------- handlers ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text, markup = home_screen()
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=markup)


async def game_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text, markup = game_screen(new_game(context))
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=markup)


async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    action, _, arg = query.data.partition(":")

    if action == "home":
        await query.answer()
        await show(query, home_screen())
    elif action == "cats":
        await query.answer()
        await show(query, categories_screen())
    elif action == "cat":
        await query.answer()
        await show(query, category_screen(arg))
    elif action == "star":
        await query.answer()
        await show(query, star_screen(int(arg)))
    elif action == "game":
        await query.answer()
        await show(query, game_screen(new_game(context)))
    elif action == "points":
        p = context.user_data.get("points", 0)
        w = context.user_data.get("wins", 0)
        await query.answer(f"🏆 ពិន្ទុ៖ {p} | ទាយត្រូវ៖ {w} ដង", show_alert=True)
    elif action == "hint":
        game = current_game(context, arg)
        if not game:
            await query.answer("ហ្គេមនេះចប់ហើយ។", show_alert=True)
            return
        await query.answer()
        game["hints"] = min(game["hints"] + 1, len(STARS[game["sid"]]["hints"]))
        await show(query, game_screen(game))
    elif action == "pick":
        gid, choice = arg.split(":")
        game = current_game(context, gid)
        if not game:
            await query.answer("ហ្គេមនេះចប់ហើយ។", show_alert=True)
            return
        await on_pick(query, context, game, int(choice))


async def on_pick(query, context, game: dict, choice: int) -> None:
    star = STARS[game["sid"]]
    context.user_data["game"] = None  # one answer per game
    if choice == game["sid"]:
        gained = POINTS[game["hints"] - 1]
        context.user_data["points"] = context.user_data.get("points", 0) + gained
        context.user_data["wins"] = context.user_data.get("wins", 0) + 1
        await query.answer("🎉 ត្រូវហើយ!")
        result = f"🎉 <b>ត្រឹមត្រូវ!</b> +{gained} ពិន្ទុ"
    else:
        await query.answer("❌ ខុសហើយ!")
        result = "❌ <b>មិនត្រឹមត្រូវទេ។</b>"
    facts = "\n".join(f"• {f}" for f in star["facts"])
    await query.edit_message_text(
        f"{result}\n\nចម្លើយ៖ {star['flag']} <b>{star['name']}</b>\n\n{facts}\n\n"
        f"🏆 ពិន្ទុសរុប៖ {context.user_data.get('points', 0)}",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("🎯 លេងម្តងទៀត", callback_data="game")], [BTN_HOME]]
        ),
    )


async def post_init(app: Application) -> None:
    await app.bot.set_my_commands(
        [
            BotCommand("start", "ទំព័រដើម"),
            BotCommand("game", "ទាយកីឡាករ"),
        ]
    )


def main() -> None:
    persistence = PicklePersistence(filepath=HERE / "sportstar_data.pickle")
    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .persistence(persistence)
        .post_init(post_init)
        .build()
    )
    app.add_handler(CommandHandler(["start", "help"], start))
    app.add_handler(CommandHandler("game", game_cmd))
    app.add_handler(CallbackQueryHandler(on_button))
    app.run_polling()


if __name__ == "__main__":
    main()
