# Khmer Sport Quote Bot 🏆

A Telegram bot that sends short, famous sport quotes in Khmer.

## Setup
1. Talk to @BotFather on Telegram → `/newbot` → copy the token.
2. `cp .env.example .env` and paste the token into `BOT_TOKEN`.
3. Install and run:
   ```bash
   python3 -m venv .venv
   .venv/bin/pip install -r requirements.txt
   .venv/bin/python bot.py
   ```

## Commands
- `/start`, `/help` — welcome message
- `/quote` — random sport quote
- `/subscribe` — daily quote (time set by `DAILY_HOUR`/`DAILY_MINUTE`, Cambodia time)
- `/unsubscribe` — stop daily quotes

Add more quotes in `quotes.py`. Subscribers are saved in `subscribers.json`.

---

## 3 more sport bots (Khmer)

| Folder | Style | Commands |
|---|---|---|
| `sport_quiz_bot/` | 🧠 Quiz game — answer with buttons, score saved | `/quiz` `/score` `/reset` |
| `sport_fact_bot/` | 📚 "Did you know?" — 🔄 button for another fact, daily delivery | `/fact` `/subscribe` `/unsubscribe` |
| `sport_workout_bot/` | 💪 Workout coach — pick a level, mark workouts done | `/workout` `/tip` `/done` `/stats` |

Each bot needs its own token from @BotFather (`QUIZ_BOT_TOKEN`, `FACT_BOT_TOKEN`, `WORKOUT_BOT_TOKEN` in `.env`). Run each in its own terminal:

```bash
.venv/bin/python sport_quiz_bot/bot.py
.venv/bin/python sport_fact_bot/bot.py
.venv/bin/python sport_workout_bot/bot.py
```

## Sportfact bot (button menu)

`sportfact_bot/` — welcome screen with buttons **🧠 ចំណេះដឹងកីឡា** / **🔄 ចំណេះដឹងមួយទៀត**,
plus **❓ សាកល្បងចំណេះដឹង** (quiz) and **🏠 ទំព័រដើម**. Reuses `sport_fact_bot/facts.py`
and `sport_quiz_bot/questions.py`. Token: `SPORTFACT_BOT_TOKEN`.

```bash
.venv/bin/python sportfact_bot/bot.py
```

## SportStar bot (athletes + guessing game)

`sportstar_bot/` — browse famous athletes by sport (⚽ 🏀 🥊 🏅) and play
**🎯 ទាយកីឡាករ**: guess the athlete from hints (3 / 2 / 1 points). Token: `SPORTSTAR_BOT_TOKEN`.

```bash
.venv/bin/python sportstar_bot/bot.py
```
