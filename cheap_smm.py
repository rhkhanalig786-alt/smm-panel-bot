"""
====================================================================================================
👑 CHEAP SMM PANEL - ENTERPRISE AUTOMATION ENGINE (V18 STABLE) 👑
====================================================================================================
Architecture : Python 3.10+ | PyTelegramBotAPI (TeleBot) | SQLite3 Multithreaded | Flask Keep-Alive
Components   : Hot Catalog, Bilingual UI, Review Matrix, Order Confirmation, Live Tracker,
               Public Logs, Admin Analytics, Wallet Management, Automated Sync, and Ticket Dispatch.
AI Features  : Fully removed as requested. Direct human admin escalation enabled.
====================================================================================================
"""

import os
import re
import html
import time
import logging
import sqlite3
import threading
import urllib.parse
from io import BytesIO
from datetime import datetime
from flask import Flask
import requests
import telebot
from telebot.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

# ==================================================================================================
# 1. CORE LOGGING & ENVIRONMENT CONFIGURATION
# ==================================================================================================
logging.basicConfig(
    format="%(asctime)s - [%(levelname)s] - %(threadName)s - %(message)s",
    level=logging.INFO
)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8228287584:AAHXnqPr9aSRWrSuVwsga8AJJJTnhfu-KtM")
bot = telebot.TeleBot(BOT_TOKEN, threaded=True, num_threads=20)

PROVIDERS = {
    "provider_primary": {
        "url": os.environ.get("API_URL_1", "https://iggrowbot.com/api/v2"),
        "key": os.environ.get("API_KEY_1", "797c2fb97d3fce189d397ef7639cc29f")
    }
}

FREE_VIEWS_SERVICE_ID = int(os.environ.get('FREE_VIEWS_SERVICE_ID', 1753))
FREE_VIEWS_PROVIDER = "https://iggrowbot.com/api/v2"

ADMIN_ID = int(os.environ.get("ADMIN_ID", 6034840006))
UPI_ID = os.environ.get("UPI_ID", "rahikhann@fam")
SUPPORT_USERNAME = os.environ.get("SUPPORT_USERNAME", "@itzdevrahi")
LOG_CHANNEL = os.environ.get("LOG_CHANNEL", "@csplogs")
MIN_DEPOSIT = float(os.environ.get("MIN_DEPOSIT", 15.0))
DATABASE_NAME = "panel_v18.db"

user_states = {}
db_lock = threading.Lock()

app = Flask(__name__)

@app.route("/")
def keep_alive_endpoint():
    return "⚡ CHEAP SMM PANEL ENGINE ONLINE & RUNNING 24/7 ⚡"

# ==================================================================================================
# 2. LOCALIZATION ENGINE (ENGLISH & HINDI)
# ==================================================================================================
STRINGS = {
    "en": {
        "btn_browse": "🛒 Browse Services",
        "btn_hot": "🔥 Hot / Cheap Services",
        "btn_profile": "💰 My Profile",
        "btn_funds": "💳 Add Funds 💸",
        "btn_history": "📦 Order History",
        "btn_leaderboard": "🏆 Leaderboard",
        "btn_free": "🎁 Claim 1K Free Views",
        "btn_referral": "🤝 Referral Program",
        "btn_support": "📞 Support Desk 🎫",
        "btn_settings": "⚙️ Settings (Language)",
        "btn_back": "🔙 Step Back",
        "btn_cancel": "❌ Cancel to Menu",
        "welcome": (
            "👋 <b>Welcome to Cheap SMM Panel, {name}!</b> 🚀\n\n"
            "Accelerate your social presence across Instagram, Telegram, YouTube & more at direct provider rates.\n\n"
            "<b>Quick Start Guide:</b>\n"
            "1️⃣ Tap <b>'💳 Add Funds'</b> to top up your balance.\n"
            "2️⃣ Tap <b>'🛒 Browse Services'</b> or <b>'🔥 Hot / Cheap Services'</b>.\n"
            "3️⃣ Paste your target link, set quantity, and grow!\n\n"
            "<i>Select an option from the menu below:</i>"
        ),
        "banned": "🚫 <b>YOUR ACCOUNT HAS BEEN SUSPENDED.</b>\nContact @itzdevrahi for assistance.",
        "cancelled": "🚫 <b>Action Cancelled!</b>\n🏠 Returned to the main menu.",
        "wallet_insufficient": "❌ <b>INSUFFICIENT BALANCE!</b>\nRequired: <code>₹{cost:.2f}</code>\nAvailable Wallet: <code>₹{balance:.2f}</code>\nPlease top up first.",
        "link_prompt": "🔗 <b>STEP 1: Enter Public Link</b>\nPaste your profile, video, or post URL below:",
        "qty_prompt": "🔢 <b>STEP 2: Enter Desired Quantity</b>\nType numbers only (e.g., 1000):",
        "order_confirm_header": "🛑 <b>ORDER VERIFICATION & CONFIRMATION</b> 🛑\n━━━━━━━━━━━━━━━━━━━━",
        "order_dispatched": "✅ <b>ORDER PLACED SUCCESSFULLY!</b> 🎉\nReceipt ID: <code>{order_id}</code>\nTotal Charged: <code>₹{cost:.2f}</code>",
        "deposit_min_error": "🚫 Minimum deposit allowed is <b>₹{min_amt:.2f}</b>.",
        "ticket_submitted": "✅ <b>Ticket #{tid} logged successfully!</b>\nOur team will review your message shortly."
    },
    "hi": {
        "btn_browse": "🛒 सेवाएं ब्राउज़ करें",
        "btn_hot": "🔥 हॉट / सस्ती सेवाएं",
        "btn_profile": "💰 मेरी प्रोफाइल",
        "btn_funds": "💳 फंड जोड़ें 💸",
        "btn_history": "📦 ऑर्डर इतिहास",
        "btn_leaderboard": "🏆 लीडरबोर्ड",
        "btn_free": "🎁 1K फ्री व्यूज",
        "btn_referral": "🤝 रेफरल प्रोग्राम",
        "btn_support": "📞 सहायता डेस्क 🎫",
        "btn_settings": "⚙️ सेटिंग्स (Language)",
        "btn_back": "🔙 एक कदम पीछे",
        "btn_cancel": "❌ मेनू पर रद्द करें",
        "welcome": (
            "👋 <b>Cheap SMM Panel में आपका स्वागत है, {name}!</b> 🚀\n\n"
            "इंस्टाग्राम, टेलीग्राम, यूट्यूब आदि पर सबसे सस्ती दरों में अपने सोशल मीडिया को ग्रो करें।\n\n"
            "<b>शुरुआत कैसे करें:</b>\n"
            "1️⃣ <b>'💳 फंड जोड़ें'</b> पर टैप करके बैलेंस लोड करें।\n"
            "2️⃣ <b>'🛒 सेवाएं ब्राउज़ करें'</b> या <b>'🔥 हॉट / सस्ती सेवाएं'</b> चुनें।\n"
            "3️⃣ अपना लिंक डालें, मात्रा चुनें और ऑर्डर कन्फर्म करें!\n\n"
            "<i>नीचे दिए गए मेनू से कोई विकल्प चुनें:</i>"
        ),
        "banned": "🚫 <b>आपका खाता निलंबित कर दिया गया है।</b>\nसहायता के लिए @itzdevrahi से संपर्क करें।",
        "cancelled": "🚫 <b>कार्रवाई रद्द कर दी गई!</b>\n🏠 मुख्य मेनू पर वापस आ गए।",
        "wallet_insufficient": "❌ <b>अपर्याप्त बैलेंस!</b>\nआवश्यक: <code>₹{cost:.2f}</code>\nवॉलेट बैलेंस: <code>₹{balance:.2f}</code>\nकृपया पहले फंड जोड़ें।",
        "link_prompt": "🔗 <b>चरण 1: टारगेट लिंक दर्ज करें</b>\nअपनी प्रोफाइल, वीडियो या पोस्ट का URL नीचे पेस्ट करें:",
        "qty_prompt": "🔢 <b>चरण 2: मात्रा दर्ज करें</b>\nकेवल संख्या लिखें (उदा. 1000):",
        "order_confirm_header": "🛑 <b>ऑर्डर सत्यापन और पुष्टि</b> 🛑\n━━━━━━━━━━━━━━━━━━━━",
        "order_dispatched": "✅ <b>ऑर्डर सफलतापूर्वक भेजा गया!</b> 🎉\nरसीद आईडी: <code>{order_id}</code>\nकुल शुल्क: <code>₹{cost:.2f}</code>",
        "deposit_min_error": "🚫 न्यूनतम जमा राशि <b>₹{min_amt:.2f}</b> है।",
        "ticket_submitted": "✅ <b>टिकट #{tid} सफलतापूर्वक दर्ज किया गया!</b>\nहमारी टीम जल्द ही आपकी सहायता करेगी।"
    }
}

def t(key, uid, **kwargs):
    lang = get_user_language(uid)
    template = STRINGS.get(lang, STRINGS["en"]).get(key, STRINGS["en"].get(key, ""))
    return template.format(**kwargs) if kwargs else template

# ==================================================================================================
# 3. DATABASE INFRASTRUCTURE & TRANSACTION MANAGEMENT
# ==================================================================================================
def execute_db(query, params=(), fetch=False, fetch_all=False, return_id=False):
    with db_lock:
        try:
            with sqlite3.connect(DATABASE_NAME, check_same_thread=False, timeout=30) as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                if fetch:
                    return cursor.fetchone()
                if fetch_all:
                    return cursor.fetchall()
                if return_id:
                    conn.commit()
                    return cursor.lastrowid
                conn.commit()
                return True
        except Exception as err:
            logging.error(f"Database Execution Fault [{query}]: {err}")
            return False

def init_database():
    schema = [
        """CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            balance REAL DEFAULT 0.0,
            total_spent REAL DEFAULT 0.0,
            free_views_credits INTEGER DEFAULT 0,
            referrer_id INTEGER,
            is_banned INTEGER DEFAULT 0,
            referral_code TEXT UNIQUE,
            language TEXT DEFAULT 'en',
            joined_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );""",
        """CREATE TABLE IF NOT EXISTS orders (
            db_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            provider TEXT,
            api_order_id TEXT,
            service_id INTEGER,
            quantity INTEGER,
            cost REAL,
            profit REAL DEFAULT 0.0,
            status TEXT DEFAULT 'Pending',
            auto_refill INTEGER DEFAULT 1,
            last_refill_check TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            placed_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );""",
        """CREATE TABLE IF NOT EXISTS managed_services (
            service_id INTEGER PRIMARY KEY,
            platform TEXT,
            category TEXT,
            name TEXT,
            provider TEXT DEFAULT 'provider_primary',
            provider_service_id INTEGER,
            rate REAL,
            min_qty INTEGER DEFAULT 10,
            max_qty INTEGER DEFAULT 100000,
            avg_time TEXT DEFAULT 'Instant - 1 Hour',
            margin REAL DEFAULT 1.50,
            disabled INTEGER DEFAULT 0
        );""",
        """CREATE TABLE IF NOT EXISTS reviews (
            review_id INTEGER PRIMARY KEY AUTOINCREMENT,
            service_id INTEGER,
            user_id INTEGER,
            rating INTEGER,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );""",
        """CREATE TABLE IF NOT EXISTS transactions (
            tx_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount REAL,
            status TEXT,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );""",
        """CREATE TABLE IF NOT EXISTS tickets (
            ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            message TEXT,
            status TEXT DEFAULT 'OPEN',
            reply TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );""",
        """CREATE TABLE IF NOT EXISTS referrals (
            referrer_id INTEGER,
            referred_id INTEGER,
            reward_claimed INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY(referrer_id, referred_id)
        );""",
        """CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        );"""
    ]
    for statement in schema:
        execute_db(statement)

    if not execute_db("SELECT value FROM settings WHERE key='global_margin'", fetch=True):
        execute_db("INSERT INTO settings (key, value) VALUES ('global_margin', '1.50')")

    try:
        execute_db("ALTER TABLE orders ADD COLUMN profit REAL DEFAULT 0.0")
    except Exception:
        pass
    try:
        execute_db("ALTER TABLE users ADD COLUMN language TEXT DEFAULT 'en'")
    except Exception:
        pass

def get_user_language(uid):
    row = execute_db("SELECT language FROM users WHERE user_id=?", (uid,), fetch=True)
    return row[0] if row and row[0] else "en"

def is_banned(uid):
    row = execute_db("SELECT is_banned FROM users WHERE user_id=?", (uid,), fetch=True)
    return bool(row and row[0] == 1)

# ==================================================================================================
# 4. PROVIDER GATEWAY & STRING UTILITIES
# ==================================================================================================
def call_provider_api(provider_name, action, extra_data=None):
    config = PROVIDERS.get(provider_name, PROVIDERS["provider_primary"])
    payload = {"key": config["key"], "action": action}
    if extra_data:
        payload.update(extra_data)
    try:
        response = requests.post(config["url"], data=payload, timeout=20)
        return response.json(), provider_name
    except Exception as exc:
        logging.error(f"Provider API communication failure [{provider_name} - {action}]: {exc}")
        return None, provider_name

def detect_platform(category_str, name_str):
    subject = f"{category_str} {name_str}".lower()
    if any(k in subject for k in ["instagram", "ig ", "reels", "insta"]):
        return "📸 Instagram"
    if any(k in subject for k in ["telegram", "tg ", "tele "]):
        return "✈️ Telegram"
    if any(k in subject for k in ["youtube", "yt ", "shorts"]):
        return "🔴 YouTube"
    if any(k in subject for k in ["facebook", "fb "]):
        return "📘 Facebook"
    if any(k in subject for k in ["tiktok", "tik tok"]):
        return "🎵 TikTok"
    if any(k in subject for k in ["twitter", "x ", "tweet"]):
        return "🐦 Twitter / X"
    return "⚡ General Boost"

def sanitize_link(raw_link):
    clean = raw_link.strip()
    clean = re.sub(r"(\?|\&)(igsh|si|utm_[a-z]+|fbclid|ref)=[a-zA-Z0-9_\-]+", "", clean)
    return clean

# ==================================================================================================
# 5. UI GENERATORS & NAVIGATION KEYBOARDS
# ==================================================================================================
def main_kb(uid):
    lang = get_user_language(uid)
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    s = STRINGS.get(lang, STRINGS["en"])

    kb.add(s["btn_browse"], s["btn_hot"])
    kb.add(s["btn_profile"], s["btn_funds"])
    kb.add(s["btn_history"], s["btn_leaderboard"])
    kb.add(s["btn_free"], s["btn_referral"])
    kb.add(s["btn_support"], s["btn_settings"])

    if uid == ADMIN_ID:
        kb.add("🧠 Admin: Smart Sync", "👥 Admin: Manage Users")
        kb.add("📈 Admin: Margin", "📢 Admin: Broadcast")
        kb.add("📊 Admin: Stats", "🎫 Admin: Tickets")
        kb.add("💾 Admin: Backup DB", "🔄 Admin: Restore DB")
    return kb

def back_cancel_kb(uid):
    lang = get_user_language(uid)
    s = STRINGS.get(lang, STRINGS["en"])
    return ReplyKeyboardMarkup(resize_keyboard=True, row_width=2).add(s["btn_back"], s["btn_cancel"])

# ==================================================================================================
# 6. USER WORKFLOW (ENTRY, ONBOARDING & SETTINGS)
# ==================================================================================================
@bot.message_handler(commands=["start"])
def handle_start(m):
    uid = m.from_user.id
    user_states.pop(uid, None)

    user = execute_db("SELECT * FROM users WHERE user_id=?", (uid,), fetch=True)
    if not user:
        referrer_id = None
        args = m.text.split()
        if len(args) > 1 and args[1].startswith("ref_"):
            try:
                candidate = int(args[1].replace("ref_", ""))
                if candidate != uid:
                    referrer_id = candidate
            except Exception:
                pass

        execute_db(
            """INSERT INTO users (user_id, username, first_name, referrer_id, referral_code)
               VALUES (?, ?, ?, ?, ?)""",
            (uid, m.from_user.username, m.from_user.first_name, referrer_id, f"REF{uid}")
        )

        if referrer_id:
            execute_db("INSERT OR IGNORE INTO referrals (referrer_id, referred_id) VALUES (?, ?)", (referrer_id, uid))
            execute_db("UPDATE users SET free_views_credits = free_views_credits + 1 WHERE user_id=?", (referrer_id,))
            try:
                bot.send_message(
                    referrer_id,
                    "🎊 <b>Referral Notification!</b>\nA new user registered via your link!\n🎁 <b>+1 Free 1K Views Credit Awarded!</b>",
                    parse_mode="HTML"
                )
            except Exception:
                pass

    if is_banned(uid):
        return bot.send_message(m.chat.id, t("banned", uid), parse_mode="HTML")

    safe_first = html.escape(m.from_user.first_name or "User")
    welcome_text = t("welcome", uid, name=safe_first)
    bot.send_message(m.chat.id, welcome_text, parse_mode="HTML", reply_markup=main_kb(uid))

@bot.message_handler(func=lambda m: m.text in ["❌ Cancel to Menu", "❌ मेनू पर रद्द करें"])
def handle_cancel_flow(m):
    user_states.pop(m.from_user.id, None)
    bot.send_message(m.chat.id, t("cancelled", m.from_user.id), parse_mode="HTML", reply_markup=main_kb(m.from_user.id))

@bot.message_handler(func=lambda m: m.text in ["🔙 Step Back", "🔙 एक कदम पीछे"])
def handle_step_back(m):
    uid = m.from_user.id
    current_state = user_states.get(uid, {}).get("state")

    if current_state == "get_qty":
        user_states[uid]["state"] = "get_link"
        bot.send_message(m.chat.id, t("link_prompt", uid), parse_mode="HTML", reply_markup=back_cancel_kb(uid))
    elif current_state == "get_link":
        user_states.pop(uid, None)
        handle_browse_catalog(m)
    elif current_state == "fund_ss":
        user_states[uid]["state"] = "fund_amt"
        bot.send_message(m.chat.id, f"💸 <b>Enter deposit amount (₹):</b>\n(Min: <code>₹{MIN_DEPOSIT}</code>)", parse_mode="HTML", reply_markup=back_cancel_kb(uid))
    else:
        user_states.pop(uid, None)
        bot.send_message(m.chat.id, "🏠 <b>Returned to Main Menu.</b>", parse_mode="HTML", reply_markup=main_kb(uid))

@bot.message_handler(func=lambda m: m.text in ["⚙️ Settings (Language)", "⚙️ सेटिंग्स (Language)"])
def handle_language_settings(m):
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("🇺🇸 English", callback_data="set_lang_en"),
        InlineKeyboardButton("🇮🇳 हिन्दी (Hindi)", callback_data="set_lang_hi")
    )
    bot.send_message(m.chat.id, "⚙️ <b>Select your interface language / अपनी भाषा चुनें:</b>", parse_mode="HTML", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("set_lang_"))
def callback_update_language(c):
    lang_code = c.data.replace("set_lang_", "")
    execute_db("UPDATE users SET language=? WHERE user_id=?", (lang_code, c.from_user.id))
    bot.answer_callback_query(c.id)
    bot.delete_message(c.message.chat.id, c.message.message_id)
    confirm_text = "✅ Language switched to English!" if lang_code == "en" else "✅ भाषा बदलकर हिन्दी कर दी गई है!"
    bot.send_message(c.message.chat.id, confirm_text, reply_markup=main_kb(c.from_user.id))

# ==================================================================================================
# 7. METRICS, ACCOUNT PROFILES & PRESTIGE LEADERBOARD
# ==================================================================================================
@bot.message_handler(func=lambda m: m.text in ["💰 My Profile", "💰 मेरी प्रोफाइल"])
def handle_view_profile(m):
    uid = m.from_user.id
    user = execute_db("SELECT balance, total_spent, free_views_credits FROM users WHERE user_id=?", (uid,), fetch=True)
    if not user:
        return
    referrals_count = execute_db("SELECT COUNT(*) FROM referrals WHERE referrer_id=?", (uid,), fetch=True)[0]

    card = (
        f"👤 <b>CLIENT ACCOUNT PROFILE</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 <b>Account ID:</b> <code>{uid}</code>\n"
        f"💳 <b>Wallet Balance:</b> <code>₹{user[0]:.2f}</code>\n"
        f"📈 <b>Lifetime Spent:</b> <code>₹{user[1]:.2f}</code>\n"
        f"🎁 <b>Free Views Credits:</b> <code>{user[2]}</code>\n"
        f"👥 <b>Active Referrals:</b> <code>{referrals_count}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )
    bot.send_message(m.chat.id, card, parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text in ["📦 Order History", "📦 ऑर्डर इतिहास"])
def handle_order_history(m):
    uid = m.from_user.id
    orders = execute_db(
        """SELECT db_id, api_order_id, quantity, cost, status, service_id
           FROM orders WHERE user_id=? ORDER BY placed_time DESC LIMIT 6""",
        (uid,),
        fetch_all=True
    )
    if not orders:
        return bot.send_message(m.chat.id, "📦 <b>No transactions or orders recorded yet.</b>", parse_mode="HTML")

    msg = "📦 <b>RECENT ACCOUNT ORDERS</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    kb = InlineKeyboardMarkup(row_width=2)
    track_buttons = []

    for item in orders:
        svc_info = execute_db("SELECT name FROM managed_services WHERE service_id=?", (item[5],), fetch=True)
        svc_name = svc_info[0] if svc_info else "Social Service"
        msg += (
            f"🧾 <b>Order #{item[0]}</b> | <code>{item[4].upper()}</code>\n"
            f"🏷️ <i>{html.escape(svc_name[:35])}</i>\n"
            f"🔢 Units: <code>{item[2]:,}</code> | 💰 Billed: <code>₹{item[3]:.2f}</code>\n"
            f"──────────────────────────\n"
        )
        if item[4].lower() in ["pending", "in progress", "processing"]:
            track_buttons.append(InlineKeyboardButton(f"🔍 Track #{item[0]}", callback_data=f"track_order_{item[0]}"))

    if track_buttons:
        kb.add(*track_buttons)

    bot.send_message(m.chat.id, msg, parse_mode="HTML", reply_markup=kb if track_buttons else None)

@bot.callback_query_handler(func=lambda c: c.data.startswith("track_order_"))
def callback_track_order_status(c):
    bot.answer_callback_query(c.id, "Connecting to provider network...")
    db_id = int(c.data.replace("track_order_", ""))
    order = execute_db("SELECT provider, api_order_id FROM orders WHERE db_id=? AND user_id=?", (db_id, c.from_user.id), fetch=True)
    if not order:
        return

    data, _ = call_provider_api(order[0], "status", {"order": order[1]})
    if data and "status" in data:
        start_count = data.get("start_count", "N/A")
        remaining = data.get("remains", "N/A")
        current_status = data.get("status", "Unknown").capitalize()
        execute_db("UPDATE orders SET status=? WHERE db_id=?", (current_status, db_id))

        status_card = (
            f"🔍 <b>REAL-TIME ORDER TRACKER</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🆔 <b>Order ID:</b> <code>#{db_id}</code>\n"
            f"📊 <b>API Dispatch Status:</b> <code>{current_status}</code>\n"
            f"🟢 <b>Start Counter:</b> <code>{start_count}</code>\n"
            f"⏳ <b>Remaining Units:</b> <code>{remaining}</code>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        bot.send_message(c.message.chat.id, status_card, parse_mode="HTML")
    else:
        bot.send_message(c.message.chat.id, "⚠️ Provider API node is temporarily busy. Please re-check in 5 minutes.")

@bot.message_handler(func=lambda m: m.text in ["🏆 Leaderboard", "🏆 लीडरबोर्ड", "/leaderboard"])
def handle_leaderboard_display(m):
    leaders = execute_db(
        """SELECT user_id, SUM(cost) as total_volume
           FROM orders
           WHERE placed_time >= datetime('now', '-7 days')
           GROUP BY user_id
           ORDER BY total_volume DESC LIMIT 5""",
        fetch_all=True
    )
    text = (
        "🏆 <b>WEEKLY SPENDERS LEADERBOARD</b> 🏆\n"
        "<i>Top creators and agencies with highest volume over the past 7 days:</i>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    )
    medals = ["🥇", "🥈", "🥉", "🏅", "🏅"]
    if not leaders:
        text += "<i>No order data recorded this week yet. Be the first!</i>\n"
    else:
        for idx, row in enumerate(leaders):
            uid_masked = f"{str(row[0])[:4]}****"
            text += f"{medals[idx]} <b>User:</b> <code>{uid_masked}</code> — Volume: <b>₹{row[1]:.2f}</b>\n"

    text += "━━━━━━━━━━━━━━━━━━━━━━━━━━\n🔥 <i>Leaderboard resets weekly. Scale your channels to dominate!</i>"
    bot.send_message(m.chat.id, text, parse_mode="HTML")

# ==================================================================================================
# 8. REFERRAL PROGRAM & FREE VIEWS ENGINE
# ==================================================================================================
@bot.message_handler(func=lambda m: m.text in ["🤝 Referral Program", "🤝 रेफरल प्रोग्राम"])
def handle_referral_overview(m):
    uid = m.from_user.id
    user = execute_db("SELECT free_views_credits FROM users WHERE user_id=?", (uid,), fetch=True)
    count = execute_db("SELECT COUNT(*) FROM referrals WHERE referrer_id=?", (uid,), fetch=True)[0]
    bot_user = bot.get_me().username
    link = f"https://t.me/{bot_user}?start=ref_{uid}"

    body = (
        f"🤝 <b>AFFILIATE REWARD SYSTEM</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔗 <b>Your Exclusive Invite Link:</b>\n"
        f"<code>{link}</code>\n\n"
        f"👥 <b>Friends Joined:</b> <code>{count}</code>\n"
        f"🎁 <b>Available 1K Views Credits:</b> <code>{user[0]}</code>\n\n"
        f"💡 <i>Earn 1,000 Free Video Views for every creator who registers through your link!</i>"
    )
    bot.send_message(m.chat.id, body, parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text in ["🎁 Claim 1K Free Views", "🎁 1K फ्री व्यूज"])
def handle_claim_free_views(m):
    uid = m.from_user.id
    credits = execute_db("SELECT free_views_credits FROM users WHERE user_id=?", (uid,), fetch=True)[0]
    if credits <= 0:
        return bot.send_message(
            m.chat.id,
            "❌ <b>You currently have 0 free views credits!</b>\nShare your referral link in the '🤝 Referral Program' tab to earn more.",
            parse_mode="HTML"
        )

    user_states[uid] = {"state": "wait_free_link"}
    bot.send_message(
        m.chat.id,
        f"🎁 <b>You have {credits} free views credit(s)!</b>\n\n🔗 Send the public post or reel link below to claim 1,000 views:",
        parse_mode="HTML",
        reply_markup=back_cancel_kb(uid)
    )

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get("state") == "wait_free_link")
def handle_process_free_views(m):
    uid = m.from_user.id
    clean_target = sanitize_link(m.text)

    credits = execute_db("SELECT free_views_credits FROM users WHERE user_id=?", (uid,), fetch=True)[0]
    if credits <= 0:
        user_states.pop(uid, None)
        return bot.send_message(m.chat.id, "❌ No credits remaining.", reply_markup=main_kb(uid))

    bot.send_message(m.chat.id, "⏳ <i>Contacting dispatch server...</i>", parse_mode="HTML")
    api_res, prov_used = call_provider_api(
        FREE_VIEWS_PROVIDER,
        "add",
        {"service": FREE_VIEWS_SERVICE_ID, "link": clean_target, "quantity": 1000}
    )

    if api_res and "order" in api_res:
        execute_db("UPDATE users SET free_views_credits = free_views_credits - 1 WHERE user_id=?", (uid,))
        execute_db(
            """INSERT INTO orders (user_id, provider, api_order_id, service_id, quantity, cost, profit, auto_refill)
               VALUES (?, ?, ?, ?, ?, 0.0, 0.0, 0)""",
            (uid, prov_used, api_res["order"], FREE_VIEWS_SERVICE_ID, 1000)
        )
        bot.send_message(
            m.chat.id,
            f"✅ <b>FREE ORDER DISPATCHED!</b> 🎉\nReceipt ID: <code>{api_res['order']}</code>\n1,000 views are on the way!",
            parse_mode="HTML",
            reply_markup=main_kb(uid)
        )
    else:
        bot.send_message(m.chat.id, "❌ <b>Delivery failed.</b> Ensure your link is public and valid.", reply_markup=main_kb(uid))
    user_states.pop(uid, None)

# ==================================================================================================
# 9. DIRECT HUMAN SUPPORT TICKET DESK
# ==================================================================================================
@bot.message_handler(func=lambda m: m.text in ["📞 Support Desk 🎫", "📞 सहायता डेस्क 🎫"])
def handle_support_overview(m):
    uid = m.from_user.id
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("💬 Direct Chat with Admin", url=f"https://t.me/{SUPPORT_USERNAME.replace('@', '')}"),
        InlineKeyboardButton("🎫 Open Support Ticket", callback_data="ticket_create_entry")
    )
    bot.send_message(
        m.chat.id,
        "📞 <b>CUSTOMER SUPPORT DESK</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━━\nNeed assistance with an order, custom volume, or payment? Choose below:",
        parse_mode="HTML",
        reply_markup=kb
    )

@bot.callback_query_handler(func=lambda c: c.data == "ticket_create_entry")
def callback_initiate_ticket(c):
    bot.answer_callback_query(c.id)
    user_states[c.from_user.id] = {"state": "waiting_ticket_body"}
    bot.send_message(
        c.message.chat.id,
        "📝 <b>Please explain your issue or request in detail below:</b>\nInclude order IDs if applicable.",
        parse_mode="HTML",
        reply_markup=back_cancel_kb(c.from_user.id)
    )

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get("state") == "waiting_ticket_body")
def handle_save_ticket(m):
    uid = m.from_user.id
    body_text = m.text.strip()
    ticket_id = execute_db("INSERT INTO tickets (user_id, message) VALUES (?, ?)", (uid, body_text), return_id=True)
    user_states.pop(uid, None)

    bot.send_message(m.chat.id, t("ticket_submitted", uid, tid=ticket_id), parse_mode="HTML", reply_markup=main_kb(uid))

    admin_kb = InlineKeyboardMarkup().add(
        InlineKeyboardButton(f"✉️ Reply Ticket #{ticket_id}", callback_data=f"adm_ticket_reply_{ticket_id}_{uid}")
    )
    admin_alert = (
        f"🚨 <b>NEW SUPPORT TICKET #{ticket_id}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>From User:</b> <code>{uid}</code> (@{m.from_user.username or 'N/A'})\n"
        f"💬 <b>Message:</b>\n{html.escape(body_text)}"
    )
    try:
        bot.send_message(ADMIN_ID, admin_alert, parse_mode="HTML", reply_markup=admin_kb)
    except Exception:
        pass

# ==================================================================================================
# 10. CAPITAL DEPOSITS & UPI RECONCILIATION
# ==================================================================================================
@bot.message_handler(func=lambda m: m.text in ["💳 Add Funds 💸", "💳 फंड जोड़ें 💸"])
def handle_add_funds_entry(m):
    uid = m.from_user.id
    if is_banned(uid):
        return bot.send_message(m.chat.id, t("banned", uid), parse_mode="HTML")

    user_states[uid] = {"state": "fund_amt"}
    bot.send_message(
        m.chat.id,
        f"💸 <b>Enter Deposit Amount in INR (₹):</b>\n(Minimum: <code>₹{MIN_DEPOSIT:.2f}</code>)",
        parse_mode="HTML",
        reply_markup=back_cancel_kb(uid)
    )

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get("state") == "fund_amt")
def handle_fund_amount_specified(m):
    uid = m.from_user.id
    try:
        amount = float(m.text.strip())
        if amount < MIN_DEPOSIT:
            return bot.send_message(m.chat.id, t("deposit_min_error", uid, min_amt=MIN_DEPOSIT), parse_mode="HTML", reply_markup=back_cancel_kb(uid))

        user_states[uid] = {"state": "fund_ss", "deposit_amt": amount}
        upi_payload = f"upi://pay?pa={UPI_ID}&am={amount:.2f}&cu=INR"
        qr_service = f"https://api.qrserver.com/v1/create-qr-code/?size=400x400&data={urllib.parse.quote(upi_payload)}"
        response = requests.get(qr_service, timeout=12)

        caption = (
            f"💳 <b>UPI PAYMENT GATEWAY</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"💰 <b>Amount:</b> <code>₹{amount:.2f}</code>\n"
            f"🆔 <b>UPI ID:</b> <code>{UPI_ID}</code>\n\n"
            f"📲 Scan the QR Code via PhonePe, Google Pay, or Paytm.\n"
            f"📸 <b>Send the payment confirmation screenshot here once paid.</b>"
        )
        bot.send_photo(m.chat.id, BytesIO(response.content), caption=caption, parse_mode="HTML", reply_markup=back_cancel_kb(uid))
    except ValueError:
        bot.send_message(m.chat.id, "❌ Please enter valid digits only.", reply_markup=back_cancel_kb(uid))

@bot.message_handler(content_types=["photo"])
def handle_payment_screenshot(m):
    uid = m.from_user.id
    state_record = user_states.get(uid, {})
    if state_record.get("state") == "fund_ss":
        deposit_amount = state_record["deposit_amt"]
        tx_id = execute_db(
            "INSERT INTO transactions (user_id, amount, status) VALUES (?, ?, 'PENDING')",
            (uid, deposit_amount),
            return_id=True
        )

        approval_kb = InlineKeyboardMarkup().add(
            InlineKeyboardButton("✅ Approve", callback_data=f"txpay_ap_{tx_id}_{uid}_{deposit_amount}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"txpay_rj_{tx_id}_{uid}")
        )
        caption = (
            f"🚨 <b>NEW WALLET DEPOSIT SUBMITTED</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 <b>Client:</b> <code>{uid}</code> (@{m.from_user.username or 'N/A'})\n"
            f"💰 <b>Amount:</b> <code>₹{deposit_amount:.2f}</code>\n"
            f"🧾 <b>Transaction Reference:</b> <code>#{tx_id}</code>"
        )
        bot.send_photo(ADMIN_ID, m.photo[-1].file_id, caption=caption, parse_mode="HTML", reply_markup=approval_kb)
        bot.send_message(
            m.chat.id,
            "✅ <b>Screenshot Received!</b>\nOur admin team is validating your transaction. Your balance will update automatically.",
            parse_mode="HTML",
            reply_markup=main_kb(uid)
        )
        user_states.pop(uid, None)

@bot.callback_query_handler(func=lambda c: c.data.startswith("txpay_"))
def callback_admin_payment_verdict(c):
    if c.from_user.id != ADMIN_ID:
        return
    bot.answer_callback_query(c.id)
    tokens = c.data.split("_")
    action = tokens[1]
    tx_id = tokens[2]
    client_uid = int(tokens[3])

    if action == "ap":
        amount_to_add = float(tokens[4])
        execute_db("UPDATE users SET balance=balance+? WHERE user_id=?", (amount_to_add, client_uid))
        execute_db("UPDATE transactions SET status='APPROVED' WHERE tx_id=?", (tx_id,))
        bot.edit_message_caption(
            f"✅ <b>DEPOSIT APPROVED</b>\nTXN ID: <code>#{tx_id}</code> | Credited: <code>₹{amount_to_add:.2f}</code> to <code>{client_uid}</code>",
            c.message.chat.id,
            c.message.message_id,
            parse_mode="HTML"
        )
        try:
            bot.send_message(
                client_uid,
                f"🎉 <b>FUNDS CREDITED!</b>\n<code>₹{amount_to_add:.2f}</code> has been credited to your wallet balance!",
                parse_mode="HTML"
            )
        except Exception:
            pass
    else:
        execute_db("UPDATE transactions SET status='REJECTED' WHERE tx_id=?", (tx_id,))
        bot.edit_message_caption(
            f"❌ <b>DEPOSIT REJECTED</b>\nTXN ID: <code>#{tx_id}</code> for client <code>{client_uid}</code>",
            c.message.chat.id,
            c.message.message_id,
            parse_mode="HTML"
        )
        try:
            bot.send_message(
                client_uid,
                "❌ <b>Deposit Verification Unsuccessful.</b>\nPlease open a support ticket if you believe this is an error.",
                parse_mode="HTML"
            )
        except Exception:
            pass

# ==================================================================================================
# 11. CATALOG DISCOVERY & HOT / CHEAPEST SERVICE ENGINE
# ==================================================================================================
@bot.message_handler(func=lambda m: m.text in ["🔥 Hot / Cheap Services", "🔥 हॉट / सस्ती सेवाएं"])
def handle_hot_services_catalog(m):
    uid = m.from_user.id
    if is_banned(uid):
        return

    cheapest_rows = execute_db(
        """SELECT service_id, platform, name, MIN(rate * margin) as final_unit_rate
           FROM managed_services
           WHERE disabled=0
           GROUP BY platform
           ORDER BY final_unit_rate ASC""",
        fetch_all=True
    )
    if not cheapest_rows:
        return bot.send_message(m.chat.id, "⚠️ Catalog empty. Admin must run Smart Sync.")

    kb = InlineKeyboardMarkup(row_width=1)
    for entry in cheapest_rows:
        kb.add(InlineKeyboardButton(f"🔥 {entry[1]} — ₹{entry[3]:.2f}/1K", callback_data=f"buy_now_{entry[0]}"))

    bot.send_message(
        m.chat.id,
        "🔥 <b>LOWEST RATE GUARANTEED SERVICES</b> 📉\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "<i>Direct access to the lowest-cost baseline services per network:</i>",
        parse_mode="HTML",
        reply_markup=kb
    )

@bot.message_handler(func=lambda m: m.text in ["🛒 Browse Services", "🛒 सेवाएं ब्राउज़ करें"])
def handle_browse_catalog(m):
    uid = m.from_user.id
    if is_banned(uid):
        return

    user_states.pop(uid, None)
    platforms = execute_db("SELECT DISTINCT platform FROM managed_services WHERE disabled=0 ORDER BY platform ASC", fetch_all=True)
    if not platforms:
        return bot.send_message(m.chat.id, "⚠️ No catalog records loaded. Admin sync required.")

    kb = InlineKeyboardMarkup(row_width=2)
    for idx, p in enumerate(platforms):
        kb.add(InlineKeyboardButton(f"{p[0]}", callback_data=f"nav_plt_{idx}"))

    bot.send_message(
        m.chat.id,
        "🛒 <b>SELECT SOCIAL NETWORK PLATFORM:</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━━\nChoose your network to explore categories:",
        parse_mode="HTML",
        reply_markup=kb
    )

@bot.callback_query_handler(func=lambda c: c.data.startswith("nav_plt_"))
def callback_platform_categories(c):
    bot.answer_callback_query(c.id)
    idx = int(c.data.replace("nav_plt_", ""))
    platforms = execute_db("SELECT DISTINCT platform FROM managed_services WHERE disabled=0 ORDER BY platform ASC", fetch_all=True)
    if idx >= len(platforms):
        return
    platform_name = platforms[idx][0]

    categories = execute_db("SELECT DISTINCT category FROM managed_services WHERE platform=? AND disabled=0", (platform_name,), fetch_all=True)
    kb = InlineKeyboardMarkup(row_width=1)
    for c_idx, cat in enumerate(categories):
        kb.add(InlineKeyboardButton(f"📁 {cat[0]}", callback_data=f"nav_cat_{idx}_{c_idx}"))
    kb.add(InlineKeyboardButton("🔙 Back to Networks", callback_data="nav_back_platforms"))

    bot.edit_message_text(
        f"📂 <b>{platform_name.upper()} CATEGORIES</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━━\nSelect a sub-category:",
        c.message.chat.id,
        c.message.message_id,
        parse_mode="HTML",
        reply_markup=kb
    )

@bot.callback_query_handler(func=lambda c: c.data == "nav_back_platforms")
def callback_return_to_platforms(c):
    bot.answer_callback_query(c.id)
    platforms = execute_db("SELECT DISTINCT platform FROM managed_services WHERE disabled=0 ORDER BY platform ASC", fetch_all=True)
    kb = InlineKeyboardMarkup(row_width=2)
    for idx, p in enumerate(platforms):
        kb.add(InlineKeyboardButton(f"{p[0]}", callback_data=f"nav_plt_{idx}"))

    bot.edit_message_text(
        "🛒 <b>SELECT SOCIAL NETWORK PLATFORM:</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━━\nChoose your network to explore categories:",
        c.message.chat.id,
        c.message.message_id,
        parse_mode="HTML",
        reply_markup=kb
    )

@bot.callback_query_handler(func=lambda c: c.data.startswith("nav_cat_"))
def callback_category_services(c):
    bot.answer_callback_query(c.id)
    _, _, p_idx, c_idx = c.data.split("_")
    p_idx, c_idx = int(p_idx), int(c_idx)

    platforms = execute_db("SELECT DISTINCT platform FROM managed_services WHERE disabled=0 ORDER BY platform ASC", fetch_all=True)
    if p_idx >= len(platforms):
        return
    platform_name = platforms[p_idx][0]

    categories = execute_db("SELECT DISTINCT category FROM managed_services WHERE platform=? AND disabled=0", (platform_name,), fetch_all=True)
    if c_idx >= len(categories):
        return
    category_name = categories[c_idx][0]

    services = execute_db(
        """SELECT service_id, name, rate, margin FROM managed_services
           WHERE platform=? AND category=? AND disabled=0""",
        (platform_name, category_name),
        fetch_all=True
    )
    kb = InlineKeyboardMarkup(row_width=1)
    for s in services:
        unit_price = s[2] * s[3]
        kb.add(InlineKeyboardButton(f"⭐ {s[1][:32]}.. — ₹{unit_price:.2f}/1K", callback_data=f"card_view_{s[0]}_{p_idx}_{c_idx}"))
    kb.add(InlineKeyboardButton(f"🔙 Back to {platform_name}", callback_data=f"nav_plt_{p_idx}"))

    bot.edit_message_text(
        f"📂 <b>{html.escape(category_name.upper())}</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━━\nSelect a service package below:",
        c.message.chat.id,
        c.message.message_id,
        parse_mode="HTML",
        reply_markup=kb
    )

@bot.callback_query_handler(func=lambda c: c.data.startswith("card_view_"))
def callback_inspect_service_card(c):
    bot.answer_callback_query(c.id)
    _, _, sid, p_idx, c_idx = c.data.split("_")
    svc = execute_db(
        """SELECT service_id, platform, name, rate, min_qty, max_qty, avg_time, margin
           FROM managed_services WHERE service_id=?""",
        (int(sid),),
        fetch=True
    )
    if not svc:
        return

    avg_rating = execute_db("SELECT AVG(rating) FROM reviews WHERE service_id=?", (svc[0],), fetch=True)[0]
    rating_string = f"{avg_rating:.1f}/5.0 ⭐" if avg_rating else "No reviews logged yet"
    calculated_price = svc[3] * svc[7]

    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("🚀 Order Package Now", callback_data=f"buy_now_{svc[0]}"))
    kb.add(InlineKeyboardButton("🔙 Back to Services List", callback_data=f"nav_cat_{p_idx}_{c_idx}"))

    card_text = (
        f"🏷️ <b>SERVICE PROFILE CARD</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 <b>Service:</b> {html.escape(svc[2])}\n"
        f"💰 <b>Rate:</b> <code>₹{calculated_price:.2f}</code> per 1,000 units\n"
        f"📊 <b>Order Bounds:</b> Min: <code>{svc[4]:,}</code> | Max: <code>{svc[5]:,}</code>\n"
        f"⏱️ <b>Avg Speed:</b> <code>{svc[6]}</code>\n"
        f"♻️ <b>Auto-Refill:</b> <code>Active Guarantee</code> 🛡️\n"
        f"⭐ <b>Client Rating:</b> <code>{rating_string}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )
    bot.edit_message_text(card_text, c.message.chat.id, c.message.message_id, parse_mode="HTML", reply_markup=kb)

# ==================================================================================================
# 12. CHECKOUT ENGINE WITH MANDATORY DOUBLE-CONFIRMATION
# ==================================================================================================
@bot.callback_query_handler(func=lambda c: c.data.startswith("buy_now_"))
def callback_begin_checkout(c):
    bot.answer_callback_query(c.id)
    uid = c.from_user.id
    if is_banned(uid):
        return bot.send_message(c.message.chat.id, t("banned", uid), parse_mode="HTML")

    sid = int(c.data.replace("buy_now_", ""))
    user_states[uid] = {"state": "get_link", "sid": sid}
    bot.send_message(c.message.chat.id, t("link_prompt", uid), parse_mode="HTML", reply_markup=back_cancel_kb(uid))

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get("state") == "get_link")
def handle_link_submission(m):
    uid = m.from_user.id
    clean_target = sanitize_link(m.text)
    user_states[uid].update({"state": "get_qty", "link": clean_target})
    bot.send_message(m.chat.id, t("qty_prompt", uid), parse_mode="HTML", reply_markup=back_cancel_kb(uid))

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get("state") == "get_qty")
def handle_quantity_submission(m):
    uid = m.from_user.id
    state = user_states[uid]
    try:
        quantity = int(m.text.strip())
    except ValueError:
        return bot.send_message(m.chat.id, "❌ Integers only. Please re-enter:", reply_markup=back_cancel_kb(uid))

    svc = execute_db(
        """SELECT provider, provider_service_id, rate, margin, min_qty, max_qty, name
           FROM managed_services WHERE service_id=?""",
        (state["sid"],),
        fetch=True
    )
    if not svc:
        return

    if quantity < svc[4] or quantity > svc[5]:
        return bot.send_message(
            m.chat.id,
            f"🚫 <b>Quantity Out of Bounds!</b>\nMinimum: <code>{svc[4]:,}</code> | Maximum: <code>{svc[5]:,}</code>",
            parse_mode="HTML",
            reply_markup=back_cancel_kb(uid)
        )

    cost = (quantity / 1000.0) * (svc[2] * svc[3])
    profit = cost - ((quantity / 1000.0) * svc[2])
    wallet_balance = execute_db("SELECT balance FROM users WHERE user_id=?", (uid,), fetch=True)[0]

    if wallet_balance < cost:
        user_states.pop(uid, None)
        return bot.send_message(
            m.chat.id,
            t("wallet_insufficient", uid, cost=cost, balance=wallet_balance),
            parse_mode="HTML",
            reply_markup=main_kb(uid)
        )

    # Double Confirmation State Staging
    user_states[uid].update({
        "state": "confirm_order",
        "qty": quantity,
        "cost": cost,
        "profit": profit,
        "p_sid": svc[1],
        "prov": svc[0],
        "s_name": svc[6]
    })

    receipt = (
        f"{t('order_confirm_header', uid)}\n"
        f"🏷️ <b>Service:</b> {html.escape(svc[6])}\n"
        f"🔗 <b>Target Link:</b> <code>{state['link']}</code>\n"
        f"🔢 <b>Volume:</b> <code>{quantity:,}</code>\n"
        f"💰 <b>Total Due:</b> <code>₹{cost:.2f}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"⚠️ <i>Orders dispatch instantly once verified. Please ensure the link is public and accessible!</i>"
    )
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("✅ Confirm & Pay", callback_data="order_decide_yes"),
        InlineKeyboardButton("❌ Abort Order", callback_data="order_decide_no")
    )
    bot.send_message(m.chat.id, receipt, parse_mode="HTML", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data in ["order_decide_yes", "order_decide_no"])
def callback_resolve_confirmation(c):
    bot.answer_callback_query(c.id)
    uid = c.from_user.id
    state = user_states.get(uid)

    if not state or state.get("state") != "confirm_order":
        return bot.delete_message(c.message.chat.id, c.message.message_id)

    if c.data == "order_decide_no":
        user_states.pop(uid, None)
        bot.edit_message_text("🚫 <b>Order Aborted.</b> Your wallet balance was not charged.", c.message.chat.id, c.message.message_id, parse_mode="HTML")
        return bot.send_message(c.message.chat.id, "🏠 <b>Main Menu</b>", reply_markup=main_kb(uid))

    bot.edit_message_text("⏳ <i>Processing order via automated API gateway...</i>", c.message.chat.id, c.message.message_id, parse_mode="HTML")
    api_res, prov_used = call_provider_api(
        state["prov"],
        "add",
        {"service": state["p_sid"], "link": state["link"], "quantity": state["qty"]}
    )

    if api_res and "order" in api_res:
        execute_db("UPDATE users SET balance=balance-?, total_spent=total_spent+? WHERE user_id=?", (state["cost"], state["cost"], uid))
        execute_db(
            """INSERT INTO orders (user_id, provider, api_order_id, service_id, quantity, cost, profit, auto_refill)
               VALUES (?, ?, ?, ?, ?, ?, ?, 1)""",
            (uid, prov_used, api_res["order"], state["sid"], state["qty"], state["cost"], state["profit"])
        )

        bot.delete_message(c.message.chat.id, c.message.message_id)
        bot.send_message(
            c.message.chat.id,
            t("order_dispatched", uid, order_id=api_res["order"], cost=state["cost"]),
            parse_mode="HTML",
            reply_markup=main_kb(uid)
        )

        # Broadcast order details to Log Channel
        broadcast_receipt = (
            f"🛍️ <b>NEW ORDER DISPATCHED</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 <b>Client:</b> <code>{uid}</code>\n"
            f"🏷️ <b>Service:</b> {html.escape(state['s_name'])}\n"
            f"🔢 <b>Volume:</b> <code>{state['qty']:,}</code>\n"
            f"💰 <b>Total Paid:</b> <code>₹{state['cost']:.2f}</code>\n"
            f"🔗 <b>Target:</b> {state['link']}"
        )
        try:
            bot.send_message(LOG_CHANNEL, broadcast_receipt, parse_mode="HTML")
        except Exception as log_err:
            logging.warning(f"Could not transmit log to {LOG_CHANNEL}: {log_err}")
    else:
        bot.delete_message(c.message.chat.id, c.message.message_id)
        bot.send_message(
            c.message.chat.id,
            "❌ <b>Provider Network Error!</b> Order could not be queued at this time. Your wallet was not billed.",
            parse_mode="HTML",
            reply_markup=main_kb(uid)
        )
    user_states.pop(uid, None)

# ==================================================================================================
# 13. CLIENT FEEDBACK & RATING MATRIX
# ==================================================================================================
@bot.callback_query_handler(func=lambda c: c.data.startswith("rate_service_"))
def callback_save_review(c):
    tokens = c.data.split("_")
    sid = int(tokens[2])
    score = int(tokens[3])
    execute_db("INSERT INTO reviews (service_id, user_id, rating) VALUES (?, ?, ?)", (sid, c.from_user.id, score))
    bot.edit_message_text(
        f"✅ <b>Thank you for your rating!</b> You rated this service {score} Star(s) ⭐",
        c.message.chat.id,
        c.message.message_id,
        parse_mode="HTML"
    )

# ==================================================================================================
# 14. COMPREHENSIVE ADMIN CONTROL DASHBOARD
# ==================================================================================================
@bot.message_handler(func=lambda m: m.text in ["📊 Admin: Stats", "/stats"] and m.from_user.id == ADMIN_ID)
def handle_admin_stats_view(m):
    profit_record = execute_db("SELECT SUM(profit) FROM orders WHERE date(placed_time) = date('now')", fetch=True)
    today_profit = profit_record[0] if profit_record and profit_record[0] else 0.0

    active_users = execute_db("SELECT COUNT(*) FROM users WHERE is_banned=0", fetch=True)[0]
    total_custody_funds = execute_db("SELECT SUM(balance) FROM users", fetch=True)[0] or 0.0
    orders_today_count = execute_db("SELECT COUNT(*) FROM orders WHERE date(placed_time) = date('now')", fetch=True)[0]

    dashboard = (
        f"📊 <b>EXECUTIVE ANALYTICS DASHBOARD</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💵 <b>Gross Profit Today:</b> <code>₹{today_profit:.2f}</code>\n"
        f"👥 <b>Active Users Base:</b> <code>{active_users:,}</code>\n"
        f"💰 <b>Client Balances Outstanding:</b> <code>₹{total_custody_funds:.2f}</code>\n"
        f"📦 <b>Orders Placed Today:</b> <code>{orders_today_count:,}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )
    bot.send_message(ADMIN_ID, dashboard, parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text == "👥 Admin: Manage Users" and m.from_user.id == ADMIN_ID)
def handle_admin_user_manager_prompt(m):
    user_states[ADMIN_ID] = {"state": "adm_wait_uid"}
    bot.send_message(
        ADMIN_ID,
        "🔍 <b>CLIENT MANAGEMENT CONSOLE</b>\nEnter the Telegram User ID to inspect or configure:",
        parse_mode="HTML",
        reply_markup=back_cancel_kb(ADMIN_ID)
    )

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get("state") == "adm_wait_uid" and m.from_user.id == ADMIN_ID)
def handle_admin_inspect_user(m):
    try:
        target_uid = int(m.text.strip())
    except ValueError:
        return bot.send_message(ADMIN_ID, "❌ User ID must be numeric.", reply_markup=back_cancel_kb(ADMIN_ID))

    target = execute_db("SELECT username, first_name, balance, total_spent, is_banned FROM users WHERE user_id=?", (target_uid,), fetch=True)
    if not target:
        return bot.send_message(ADMIN_ID, "❌ User ID not registered in database.", reply_markup=back_cancel_kb(ADMIN_ID))

    status_str = "🔴 BANNED" if target[4] else "🟢 ACTIVE"
    dossier = (
        f"👤 <b>CLIENT DOSSIER</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 <b>Target ID:</b> <code>{target_uid}</code>\n"
        f"👤 <b>Name:</b> {html.escape(target[1] or 'N/A')} (@{target[0] or 'N/A'})\n"
        f"💳 <b>Wallet Balance:</b> <code>₹{target[2]:.2f}</code>\n"
        f"📈 <b>Lifetime Volume:</b> <code>₹{target[3]:.2f}</code>\n"
        f"🛡️ <b>Account Status:</b> <code>{status_str}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("➕ Add Balance", callback_data=f"adm_act_add_{target_uid}"),
        InlineKeyboardButton("➖ Deduct Balance", callback_data=f"adm_act_sub_{target_uid}")
    )
    if target[4]:
        kb.add(InlineKeyboardButton("✅ Unban User", callback_data=f"adm_act_unban_{target_uid}"))
    else:
        kb.add(InlineKeyboardButton("🚫 Ban User", callback_data=f"adm_act_ban_{target_uid}"))

    user_states.pop(ADMIN_ID, None)
    bot.send_message(ADMIN_ID, dossier, parse_mode="HTML", reply_markup=main_kb(ADMIN_ID))
    bot.send_message(ADMIN_ID, "⚙️ <b>Select Admin Action:</b>", parse_mode="HTML", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("adm_act_"))
def callback_admin_user_action_dispatch(c):
    if c.from_user.id != ADMIN_ID:
        return
    bot.answer_callback_query(c.id)
    _, _, action, target_uid = c.data.split("_")
    target_uid = int(target_uid)

    if action == "add":
        user_states[ADMIN_ID] = {"state": "adm_input_add", "target_uid": target_uid}
        bot.send_message(ADMIN_ID, f"➕ Enter amount to <b>ADD</b> to User <code>{target_uid}</code>:", parse_mode="HTML", reply_markup=back_cancel_kb(ADMIN_ID))
    elif action == "sub":
        user_states[ADMIN_ID] = {"state": "adm_input_sub", "target_uid": target_uid}
        bot.send_message(ADMIN_ID, f"➖ Enter amount to <b>DEDUCT</b> from User <code>{target_uid}</code>:", parse_mode="HTML", reply_markup=back_cancel_kb(ADMIN_ID))
    elif action == "ban":
        execute_db("UPDATE users SET is_banned=1 WHERE user_id=?", (target_uid,))
        bot.edit_message_text(f"🚫 <b>User {target_uid} has been BANNED.</b>", c.message.chat.id, c.message.message_id, parse_mode="HTML")
    elif action == "unban":
        execute_db("UPDATE users SET is_banned=0 WHERE user_id=?", (target_uid,))
        bot.edit_message_text(f"✅ <b>User {target_uid} has been UNBANNED.</b>", c.message.chat.id, c.message.message_id, parse_mode="HTML")

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get("state") in ["adm_input_add", "adm_input_sub"] and m.from_user.id == ADMIN_ID)
def handle_admin_adjust_balance_final(m):
    meta = user_states[ADMIN_ID]
    action_type = meta["state"]
    target_uid = meta["target_uid"]
    try:
        amount = float(m.text.strip())
    except ValueError:
        return bot.send_message(ADMIN_ID, "❌ Numeric amounts only.", reply_markup=back_cancel_kb(ADMIN_ID))

    if action_type == "adm_input_add":
        execute_db("UPDATE users SET balance=balance+? WHERE user_id=?", (amount, target_uid))
        execute_db("INSERT INTO transactions (user_id, amount, status) VALUES (?, ?, 'ADMIN_CREDIT')", (target_uid, amount))
        bot.send_message(ADMIN_ID, f"✅ Added <code>₹{amount:.2f}</code> to client <code>{target_uid}</code>.", parse_mode="HTML", reply_markup=main_kb(ADMIN_ID))
        try:
            bot.send_message(target_uid, f"🎁 <b>Wallet Adjustment:</b> Admin added <code>₹{amount:.2f}</code> to your account!", parse_mode="HTML")
        except Exception:
            pass
    else:
        current_bal = execute_db("SELECT balance FROM users WHERE user_id=?", (target_uid,), fetch=True)[0]
        new_balance = max(0.0, current_bal - amount)
        execute_db("UPDATE users SET balance=? WHERE user_id=?", (new_balance, target_uid))
        execute_db("INSERT INTO transactions (user_id, amount, status) VALUES (?, ?, 'ADMIN_DEBIT')", (target_uid, -amount))
        bot.send_message(ADMIN_ID, f"✅ Deducted <code>₹{amount:.2f}</code> from client <code>{target_uid}</code>.\nNew Balance: <code>₹{new_balance:.2f}</code>", parse_mode="HTML", reply_markup=main_kb(ADMIN_ID))
        try:
            bot.send_message(target_uid, f"⚠️ <b>Wallet Adjustment:</b> <code>₹{amount:.2f}</code> was deducted by admin.", parse_mode="HTML")
        except Exception:
            pass
    user_states.pop(ADMIN_ID, None)

@bot.message_handler(func=lambda m: m.text == "🧠 Admin: Smart Sync" and m.from_user.id == ADMIN_ID)
def handle_admin_smart_sync(m):
    bot.send_message(ADMIN_ID, "🧠 <i>Initializing provider sync matrix...</i>", parse_mode="HTML")
    res, _ = call_provider_api("provider_primary", "services")
    if not res or not isinstance(res, list):
        return bot.send_message(ADMIN_ID, "❌ Failed to fetch services from Provider API.")

    execute_db("DELETE FROM managed_services")
    margin_mult = float(execute_db("SELECT value FROM settings WHERE key='global_margin'", fetch=True)[0])

    categorized = {}
    for s in res:
        c_name = s.get("category", "General")
        if c_name not in categorized:
            categorized[c_name] = []
        categorized[c_name].append(s)

    inserted_count = 0
    for cat_title, items in categorized.items():
        cat_lower = cat_title.lower()
        if any(x in cat_lower for x in ["like", "view", "share"]):
            items.sort(key=lambda x: float(x.get("rate", 9999)))
            selected = items[:2]
        elif any(x in cat_lower for x in ["follower", "subscriber"]):
            hq = [x for x in items if any(k in x.get("name", "").lower() for k in ["refill", "guarantee", "hq"])]
            if not hq:
                hq = items
            hq.sort(key=lambda x: float(x.get("rate", 0)), reverse=True)
            selected = hq[-3:]
        else:
            items.sort(key=lambda x: float(x.get("rate", 9999)))
            selected = items[:1]

        for item in selected:
            try:
                platform = detect_platform(cat_title, item.get("name", ""))
                speed_str = "10-60 Mins" if "instant" in item.get("name", "").lower() else "1-24 Hours"
                execute_db(
                    """INSERT OR REPLACE INTO managed_services
                       (service_id, platform, category, name, provider, provider_service_id, rate, min_qty, max_qty, avg_time, margin, disabled)
                       VALUES (?, ?, ?, ?, 'provider_primary', ?, ?, ?, ?, ?, ?, 0)""",
                    (
                        int(item["service"]),
                        platform,
                        cat_title,
                        item["name"],
                        int(item["service"]),
                        float(item["rate"]),
                        int(item.get("min", 10)),
                        int(item.get("max", 100000)),
                        speed_str,
                        margin_mult
                    )
                )
                inserted_count += 1
            except Exception:
                continue

    bot.send_message(ADMIN_ID, f"✅ <b>Smart Sync Finished!</b>\nSuccessfully loaded <code>{inserted_count}</code> optimized services into the catalog.", parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text == "📈 Admin: Margin" and m.from_user.id == ADMIN_ID)
def handle_admin_margin_prompt(m):
    user_states[ADMIN_ID] = {"state": "adm_margin_input"}
    bot.send_message(
        ADMIN_ID,
        "📈 <b>PROFIT MARGIN CONFIGURATION</b>\nEnter new markup percentage (e.g., <code>50</code> for 50% profit):",
        parse_mode="HTML",
        reply_markup=back_cancel_kb(ADMIN_ID)
    )

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get("state") == "adm_margin_input" and m.from_user.id == ADMIN_ID)
def handle_admin_set_margin(m):
    try:
        percentage = float(m.text.strip())
        multiplier = 1.0 + (percentage / 100.0)
        execute_db("UPDATE settings SET value=? WHERE key='global_margin'", (str(multiplier),))
        execute_db("UPDATE managed_services SET margin=?", (multiplier,))
        bot.send_message(ADMIN_ID, f"✅ Global profit margin updated to <b>{percentage:.1f}%</b> (Factor: {multiplier:.2f}x).", parse_mode="HTML", reply_markup=main_kb(ADMIN_ID))
    except ValueError:
        bot.send_message(ADMIN_ID, "❌ Please enter a valid number.", reply_markup=back_cancel_kb(ADMIN_ID))
    user_states.pop(ADMIN_ID, None)

@bot.message_handler(func=lambda m: m.text == "📢 Admin: Broadcast" and m.from_user.id == ADMIN_ID)
def handle_admin_broadcast_prompt(m):
    user_states[ADMIN_ID] = {"state": "adm_broadcast_msg"}
    bot.send_message(ADMIN_ID, "📢 <b>MASS BROADCAST DISPATCH</b>\nEnter the announcement message below:", parse_mode="HTML", reply_markup=back_cancel_kb(ADMIN_ID))

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get("state") == "adm_broadcast_msg" and m.from_user.id == ADMIN_ID)
def handle_admin_broadcast_execute(m):
    all_users = execute_db("SELECT user_id FROM users WHERE is_banned=0", fetch_all=True)
    sent_counter = 0
    bot.send_message(ADMIN_ID, f"⏳ <i>Broadcasting to {len(all_users)} clients...</i>", parse_mode="HTML")
    for row in all_users:
        try:
            bot.send_message(row[0], f"📢 <b>PLATFORM ANNOUNCEMENT:</b>\n\n{m.text}", parse_mode="HTML")
            sent_counter += 1
            time.sleep(0.04)
        except Exception:
            pass
    bot.send_message(ADMIN_ID, f"✅ Broadcast successfully received by <code>{sent_counter}</code> accounts.", parse_mode="HTML", reply_markup=main_kb(ADMIN_ID))
    user_states.pop(ADMIN_ID, None)

@bot.message_handler(func=lambda m: m.text == "🎫 Admin: Tickets" and m.from_user.id == ADMIN_ID)
def handle_admin_ticket_queue(m):
    open_tickets = execute_db("SELECT ticket_id, user_id, message, created_at FROM tickets WHERE status='OPEN' LIMIT 5", fetch_all=True)
    if not open_tickets:
        return bot.send_message(ADMIN_ID, "✅ <b>No pending support tickets.</b>", parse_mode="HTML")

    for t_item in open_tickets:
        kb = InlineKeyboardMarkup().add(
            InlineKeyboardButton(f"✉️ Reply Ticket #{t_item[0]}", callback_data=f"adm_ticket_reply_{t_item[0]}_{t_item[1]}"),
            InlineKeyboardButton(f"🔒 Close #{t_item[0]}", callback_data=f"adm_ticket_close_{t_item[0]}")
        )
        msg_out = (
            f"🎫 <b>TICKET #{t_item[0]} (OPEN)</b>\n"
            f"👤 <b>Client:</b> <code>{t_item[1]}</code>\n"
            f"🕒 <b>Received:</b> <code>{t_item[3]}</code>\n"
            f"💬 <b>Issue:</b>\n{html.escape(t_item[2])}"
        )
        bot.send_message(ADMIN_ID, msg_out, parse_mode="HTML", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("adm_ticket_reply_"))
def callback_admin_ticket_reply(c):
    if c.from_user.id != ADMIN_ID:
        return
    bot.answer_callback_query(c.id)
    _, _, _, tid, target_uid = c.data.split("_")
    user_states[ADMIN_ID] = {"state": "adm_send_ticket_reply", "ticket_id": int(tid), "target_uid": int(target_uid)}
    bot.send_message(ADMIN_ID, f"✉️ <b>Type response for Ticket #{tid} (Client: {target_uid}):</b>", parse_mode="HTML", reply_markup=back_cancel_kb(ADMIN_ID))

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get("state") == "adm_send_ticket_reply" and m.from_user.id == ADMIN_ID)
def handle_admin_send_ticket_reply_action(m):
    data = user_states[ADMIN_ID]
    tid = data["ticket_id"]
    client_uid = data["target_uid"]
    reply_text = m.text.strip()

    execute_db("UPDATE tickets SET status='RESOLVED', reply=? WHERE ticket_id=?", (reply_text, tid))
    try:
        client_msg = (
            f"📬 <b>SUPPORT TICKET UPDATE</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🧾 <b>Ticket ID:</b> <code>#{tid}</code>\n"
            f"💬 <b>Admin Response:</b>\n{html.escape(reply_text)}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        bot.send_message(client_uid, client_msg, parse_mode="HTML")
        bot.send_message(ADMIN_ID, f"✅ Reply delivered to client <code>{client_uid}</code>. Ticket closed.", reply_markup=main_kb(ADMIN_ID))
    except Exception as exc:
        bot.send_message(ADMIN_ID, f"⚠️ Failed to deliver DM to user: {exc}", reply_markup=main_kb(ADMIN_ID))
    user_states.pop(ADMIN_ID, None)

@bot.callback_query_handler(func=lambda c: c.data.startswith("adm_ticket_close_"))
def callback_admin_close_ticket(c):
    if c.from_user.id != ADMIN_ID:
        return
    bot.answer_callback_query(c.id)
    tid = int(c.data.replace("adm_ticket_close_", ""))
    execute_db("UPDATE tickets SET status='CLOSED' WHERE ticket_id=?", (tid,))
    bot.edit_message_text(f"🔒 <b>Ticket #{tid} marked as CLOSED.</b>", c.message.chat.id, c.message.message_id, parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text == "💾 Admin: Backup DB" and m.from_user.id == ADMIN_ID)
def handle_admin_backup_archive(m):
    uid = m.from_user.id
    bot.send_message(uid, "⏳ <i>Generating verified SQLite snapshot...</i>", parse_mode="HTML")
    backup_filename = f"backup_{int(time.time())}.db"
    try:
        with db_lock:
            with sqlite3.connect(DATABASE_NAME) as src, sqlite3.connect(backup_filename) as dst:
                src.backup(dst)
        with open(backup_filename, "rb") as archive:
            bot.send_document(uid, archive, caption="💾 <b>DATABASE SNAPSHOT ARCHIVE</b>\nVerified operational backup.", parse_mode="HTML")
    except Exception as exc:
        bot.send_message(uid, f"❌ Backup failure: <code>{exc}</code>", parse_mode="HTML")
    finally:
        if os.path.exists(backup_filename):
            os.remove(backup_filename)

@bot.message_handler(func=lambda m: m.text == "🔄 Admin: Restore DB" and m.from_user.id == ADMIN_ID)
def handle_admin_restore_init(m):
    user_states[ADMIN_ID] = {"state": "adm_wait_db_upload"}
    bot.send_message(ADMIN_ID, "⚠️ <b>RESTORE DATABASE:</b> Upload the valid <code>.db</code> file below:", parse_mode="HTML", reply_markup=back_cancel_kb(ADMIN_ID))

@bot.message_handler(content_types=["document"])
def handle_admin_restore_file(m):
    uid = m.from_user.id
    if uid == ADMIN_ID and user_states.get(uid, {}).get("state") == "adm_wait_db_upload":
        if not m.document.file_name.endswith(".db"):
            return bot.send_message(uid, "❌ Invalid file extension. Must be a .db file.", reply_markup=main_kb(uid))

        temp_name = f"staging_{int(time.time())}.db"
        try:
            bot.send_message(uid, "⏳ <i>Mounting and verifying restore database...</i>", parse_mode="HTML")
            downloaded = bot.download_file(bot.get_file(m.document.file_id).file_path)
            with open(temp_name, "wb") as f_out:
                f_out.write(downloaded)

            with db_lock:
                with sqlite3.connect(temp_name) as src, sqlite3.connect(DATABASE_NAME) as dst:
                    src.backup(dst)

            bot.send_message(uid, "✅ <b>DATABASE RESTORE SUCCESSFUL!</b> All records synchronized.", parse_mode="HTML", reply_markup=main_kb(uid))
        except Exception as exc:
            bot.send_message(uid, f"❌ Database restore failed: {exc}", reply_markup=main_kb(uid))
        finally:
            user_states.pop(uid, None)
            if os.path.exists(temp_name):
                os.remove(temp_name)

# ==================================================================================================
# 15. BACKGROUND WORKER (LIVE STATUS DMs, AUTO-REFILLS & REVIEWS)
# ==================================================================================================
def background_monitoring_worker():
    while True:
        try:
            # 1. Query Active Pending / Processing Orders
            active_orders = execute_db(
                """SELECT db_id, provider, api_order_id, status, user_id, quantity, service_id
                   FROM orders WHERE status IN ('Pending', 'In progress', 'Processing')""",
                fetch_all=True
            )
            if active_orders:
                for o in active_orders:
                    res, _ = call_provider_api(o[1], "status", {"order": o[2]})
                    if res and "status" in res:
                        updated_status = res["status"].capitalize()
                        if updated_status != o[3]:
                            execute_db("UPDATE orders SET status=? WHERE db_id=?", (updated_status, o[0]))

                            # Live DM Notification
                            if updated_status in ["Completed", "Partial", "Canceled"]:
                                svc_record = execute_db("SELECT name FROM managed_services WHERE service_id=?", (o[6],), fetch=True)
                                svc_title = svc_record[0] if svc_record else "Social Growth Service"
                                symbol = "✅" if updated_status == "Completed" else "⚠️"

                                try:
                                    alert_dm = (
                                        f"{symbol} <b>REAL-TIME ORDER STATUS UPDATE</b>\n"
                                        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                                        f"🧾 <b>Order ID:</b> <code>#{o[0]}</code>\n"
                                        f"🏷️ <b>Service:</b> {html.escape(svc_title)}\n"
                                        f"🔢 <b>Volume:</b> <code>{o[5]:,}</code>\n"
                                        f"📊 <b>New Status:</b> <code>{updated_status.upper()}</code>\n"
                                        f"━━━━━━━━━━━━━━━━━━━━━━━━━━"
                                    )
                                    bot.send_message(o[4], alert_dm, parse_mode="HTML")

                                    # Trigger Star Rating if Completed
                                    if updated_status == "Completed":
                                        review_kb = InlineKeyboardMarkup(row_width=5)
                                        review_kb.add(
                                            InlineKeyboardButton("1 ⭐", callback_data=f"rate_service_{o[6]}_1"),
                                            InlineKeyboardButton("2 ⭐", callback_data=f"rate_service_{o[6]}_2"),
                                            InlineKeyboardButton("3 ⭐", callback_data=f"rate_service_{o[6]}_3"),
                                            InlineKeyboardButton("4 ⭐", callback_data=f"rate_service_{o[6]}_4"),
                                            InlineKeyboardButton("5 ⭐", callback_data=f"rate_service_{o[6]}_5")
                                        )
                                        bot.send_message(
                                            o[4],
                                            "⭐ <b>How was the delivery speed and retention?</b>\nPlease rate your experience:",
                                            parse_mode="HTML",
                                            reply_markup=review_kb
                                        )
                                except Exception:
                                    pass

            # 2. Automated Provider Refill Trigger
            refill_targets = execute_db(
                """SELECT db_id, provider, api_order_id, user_id
                   FROM orders
                   WHERE auto_refill=1 AND status IN ('Completed', 'Partial')""",
                fetch_all=True
            )
            if refill_targets:
                for ro in refill_targets:
                    refill_res, _ = call_provider_api(ro[1], "refill", {"order": ro[2]})
                    if refill_res and "refill" in refill_res:
                        execute_db("UPDATE orders SET last_refill_check=CURRENT_TIMESTAMP WHERE db_id=?", (ro[0],))

        except Exception as worker_err:
            logging.error(f"Worker Loop Exception: {worker_err}")

        time.sleep(300)

# ==================================================================================================
# 16. APPLICATION INITIALIZATION & MULTITHREADED RUNTIME
# ==================================================================================================
if __name__ == "__main__":
    init_database()

    try:
        bot.remove_webhook()
        time.sleep(1)
    except Exception:
        pass

    polling_thread = threading.Thread(
        target=lambda: bot.infinity_polling(skip_pending=True, timeout=60),
        name="TelegramPollingDaemon",
        daemon=True
    )
    polling_thread.start()

    worker_thread = threading.Thread(
        target=background_monitoring_worker,
        name="BackgroundMonitorDaemon",
        daemon=True
    )
    worker_thread.start()

    server_port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=server_port)
