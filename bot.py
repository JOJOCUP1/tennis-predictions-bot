"""Tennis analysis daily package Telegram bot; Georgian UI."""
import asyncio
import logging
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandObject
from aiogram.types import (
    Message, CallbackQuery, PreCheckoutQuery, InlineKeyboardButton,
    InlineKeyboardMarkup, LabeledPrice,
)
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")
TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
PACKAGE_STARS = int(os.getenv("PACKAGE_STARS", "0"))
SUPPORT = os.getenv("SUPPORT_USERNAME", "").lstrip("@")
DB = ROOT / "tennis.db"
TZ = ZoneInfo("Asia/Tbilisi")
dp = Dispatcher()

RULES = (
    "📜 სერვისის წესები\n\n"
    "1. დღის პაკეტის აღწერითი ფასი: 10 ₾. Telegram-ის გადახდა Stars-ში გამოჩნდება.\n"
    "2. წვდომა მოქმედებს შეძენის დღის ბოლომდე, თბილისის დროით.\n"
    "3. პაკეტით მიიღებთ გამოქვეყნებულ დღიურ მატჩების ანალიზს.\n"
    "4. პროგნოზი არ იძლევა შედეგის ან მოგების გარანტიას.\n"
    "5. სერვისი არ იღებს ფსონებს.\n"
    "6. დაიცავით ადგილობრივი კანონმდებლობა და ასაკობრივი შეზღუდვები.\n"
    "7. ტექნიკურ ან დაბრუნების საკითხებზე დაუკავშირდით მხარდაჭერას."
)

def today():
    return datetime.now(TZ).date().isoformat()

def conn():
    db = sqlite3.connect(DB, timeout=20)
    db.execute("PRAGMA busy_timeout=20000")
    return db

def init_db():
    with conn() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY, username TEXT, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT, day TEXT NOT NULL,
            content TEXT NOT NULL, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS payments (
            charge_id TEXT PRIMARY KEY, user_id INTEGER NOT NULL,
            day TEXT NOT NULL, stars INTEGER NOT NULL,
            created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS access_grants (
            user_id INTEGER NOT NULL, day TEXT NOT NULL,
            PRIMARY KEY(user_id, day));
        """)

def has_access(user_id, day):
    if user_id == ADMIN_ID:
        return True
    with conn() as db:
        return db.execute(
            "SELECT 1 FROM access_grants WHERE user_id=? AND day=?",
            (user_id, day)
        ).fetchone() is not None

def menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎾 დღის პროგნოზები", callback_data="predictions")],
        [InlineKeyboardButton(text="💎 დღის პაკეტი — 10 ₾", callback_data="package")],
        [InlineKeyboardButton(text="📜 წესები", callback_data="rules")],
        [InlineKeyboardButton(text="📞 მხარდაჭერა", callback_data="support")],
    ])

@dp.message(Command("start"))
async def start(msg: Message):
    with conn() as db:
        db.execute(
            "INSERT OR IGNORE INTO users VALUES (?, ?, ?)",
            (msg.from_user.id, msg.from_user.username, datetime.now(TZ).isoformat())
        )
    await msg.answer(
        "🎾 Tennis Predictions\n\n"
        "დღის ჩოგბურთის მატჩების ანალიზები და პროგნოზები. "
        "მოგება გარანტირებული არ არის.\n\nაირჩიეთ მოქმედება:",
        reply_markup=menu()
    )

@dp.message(Command("myid"))
async def myid(msg: Message):
    await msg.answer(f"თქვენი Telegram ID: {msg.from_user.id}")

@dp.callback_query(F.data == "rules")
async def rules(q: CallbackQuery):
    await q.answer()
    await q.message.answer(RULES)

@dp.callback_query(F.data == "support")
async def support(q: CallbackQuery):
    await q.answer()
    await q.message.answer(
        f"📞 მხარდაჭერა: @{SUPPORT}" if SUPPORT else
        "მხარდაჭერის საკონტაქტო ჯერ არ არის მითითებული."
    )

@dp.callback_query(F.data == "predictions")
async def predictions(q: CallbackQuery):
    await q.answer()
    day = today()
    if not has_access(q.from_user.id, day):
        await q.message.answer(
            "🔒 საჭიროა დღის პაკეტის შეძენა.", reply_markup=menu()
        )
        return
    with conn() as db:
        rows = db.execute(
            "SELECT content FROM predictions WHERE day=? ORDER BY id",
            (day,)
        ).fetchall()
    if not rows:
        await q.message.answer("დღევანდელი პროგნოზები ჯერ არ გამოქვეყნებულა.")
    for (content,) in rows:
        await q.message.answer("🎾 " + content)

@dp.callback_query(F.data == "package")
async def package(q: CallbackQuery):
    await q.answer()
    day = today()
    if has_access(q.from_user.id, day):
        await q.message.answer("✅ დღევანდელი წვდომა უკვე გაქვთ.")
    elif PACKAGE_STARS <= 0:
        await q.message.answer(
            "💎 დღის პაკეტი — 10 ₾\n"
            "მოქმედებს დღევანდელი დღის ბოლომდე თბილისის დროით.\n"
            "⚙️ გადახდები ჯერ გამორთულია; საჭიროა Stars ფასის დაყენება."
        )
    else:
        await q.message.answer_invoice(
            title="დღის ჩოგბურთის პროგნოზები",
            description=f"პროგნოზები {day} დღისთვის. მოგება გარანტირებული არ არის.",
            payload=f"daily:{day}:{q.from_user.id}",
            currency="XTR",
            prices=[LabeledPrice(label="დღის პაკეტი", amount=PACKAGE_STARS)],
            provider_token="",
        )

@dp.pre_checkout_query()
async def checkout(q: PreCheckoutQuery):
    valid = (
        PACKAGE_STARS > 0 and q.currency == "XTR"
        and q.total_amount == PACKAGE_STARS
        and q.invoice_payload == f"daily:{today()}:{q.from_user.id}"
        and not has_access(q.from_user.id, today())
    )
    await q.answer(
        ok=valid,
        error_message=None if valid else "ინვოისი ვადაგასულია ან წვდომა უკვე აქტიურია."
    )

@dp.message(F.successful_payment)
async def paid(msg: Message):
    p = msg.successful_payment
    parts = p.invoice_payload.split(":")
    valid = (
        len(parts) == 3 and parts[0] == "daily"
        and parts[2] == str(msg.from_user.id)
        and p.currency == "XTR"
        and p.total_amount == PACKAGE_STARS
        and bool(p.telegram_payment_charge_id)
    )
    if not valid:
        logging.error("Unmatched charge ID: %s", p.telegram_payment_charge_id)
        await msg.answer("გადახდა მიღებულია. წვდომის გასახსნელად მიმართეთ მხარდაჭერას.")
        return
    day = parts[1]
    with conn() as db:
        inserted = db.execute(
            "INSERT OR IGNORE INTO payments VALUES (?, ?, ?, ?, ?)",
            (p.telegram_payment_charge_id, msg.from_user.id,
             day, p.total_amount, datetime.now(TZ).isoformat())
        ).rowcount
        if inserted:
            db.execute(
                "INSERT OR IGNORE INTO access_grants VALUES (?, ?)",
                (msg.from_user.id, day)
            )
    if day == today():
        await msg.answer("✅ გადახდა მიღებულია! დღევანდელი პროგნოზები ხელმისაწვდომია.", reply_markup=menu())
    else:
        await msg.answer("გადახდა მიღებულია, მაგრამ შეძენის დღე დასრულდა. დაუკავშირდით მხარდაჭერას.")

@dp.message(Command("admin"))
async def admin(msg: Message):
    if msg.from_user.id == ADMIN_ID:
        await msg.answer(
            "🔐 ადმინპანელი\n"
            "/add ტექსტი — პროგნოზის დამატება\n"
            "/list — დღევანდელი პროგნოზები\n"
            "/delete ID — წაშლა\n"
            "/stats — სტატისტიკა"
        )

@dp.message(Command("add"))
async def add(msg: Message, command: CommandObject):
    if msg.from_user.id != ADMIN_ID:
        return
    content = (command.args or "").strip()
    if not content or len(content) > 3000:
        await msg.answer("ფორმატი: /add Player A vs Player B — ანალიზი (მაქს. 3000 სიმბოლო)")
        return
    with conn() as db:
        result = db.execute(
            "INSERT INTO predictions(day, content, created_at) VALUES (?, ?, ?)",
            (today(), content, datetime.now(TZ).isoformat())
        )
        ident = result.lastrowid
    await msg.answer(f"✅ პროგნოზი #{ident} დაემატა.")

@dp.message(Command("list"))
async def list_predictions(msg: Message):
    if msg.from_user.id != ADMIN_ID:
        return
    with conn() as db:
        rows = db.execute(
            "SELECT id, content FROM predictions WHERE day=? ORDER BY id",
            (today(),)
        ).fetchall()
    if not rows:
        await msg.answer("დღეს პროგნოზები არ არის.")
    for ident, content in rows:
        await msg.answer(f"#{ident}: {content}")

@dp.message(Command("delete"))
async def delete(msg: Message, command: CommandObject):
    if msg.from_user.id != ADMIN_ID:
        return
    try:
        ident = int(command.args or "")
    except ValueError:
        await msg.answer("ფორმატი: /delete 1")
        return
    with conn() as db:
        count = db.execute(
            "DELETE FROM predictions WHERE id=? AND day=?",
            (ident, today())
        ).rowcount
    await msg.answer("✅ წაიშალა." if count else "პროგნოზი ვერ მოიძებნა.")

@dp.message(Command("stats"))
async def stats(msg: Message):
    if msg.from_user.id != ADMIN_ID:
        return
    with conn() as db:
        users = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        sales = db.execute(
            "SELECT COUNT(*) FROM payments WHERE day=?", (today(),)
        ).fetchone()[0]
    await msg.answer(f"📊 მომხმარებლები: {users}\nდღევანდელი შესყიდვები: {sales}")

async def main():
    if not TOKEN or TOKEN == "PASTE_BOTFATHER_TOKEN_HERE" or ADMIN_ID <= 0:
        raise SystemExit("შეავსეთ BOT_TOKEN და ADMIN_ID .env ფაილში")
    if PACKAGE_STARS < 0:
        raise SystemExit("PACKAGE_STARS არ შეიძლება იყოს უარყოფითი")
    logging.basicConfig(level=logging.INFO)
    init_db()
    bot = Bot(TOKEN)
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
