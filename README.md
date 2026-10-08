# 🎾 Tennis Predictions Telegram Bot

Georgian-language daily tennis predictions service. Price advertised: **10 GEL per day**. Telegram digital-content payments use **Stars (XTR)**; set the Stars amount independently. No guaranteed winnings; the bot does not accept wagers.

## Run

1. Install Python 3.11+.
2. `pip install -r requirements.txt`
3. Copy `.env.example` to `.env`.
4. Create a bot with [@BotFather](https://t.me/BotFather); set `BOT_TOKEN` and your numeric `ADMIN_ID` (send `/myid` to the bot).
5. Keep `PACKAGE_STARS=0` to disable live payments until you decide the Stars price and test; then set a positive integer.
6. `python bot.py`

## Commands

User: `/start`, `/myid`. Menu: rules, package, predictions, support.

Admin: `/admin`, `/add Player A vs Player B — analysis`, `/list`, `/delete 1`, `/stats`.

Purchases unlock that day's predictions until 23:59 Asia/Tbilisi. The bot stores users, charge IDs, purchases, access grants, and predictions in local SQLite `tennis.db`. Back this up and deploy to persistent storage for production.

**Important:** Only the `.env.example` template belongs in Git. Never commit your Telegram bot token. Confirm local legal restrictions and Telegram policies before offering paid betting-related analysis. Refund/payment support must be established before launch. This MVP uses polling and is not yet production-hardened.
