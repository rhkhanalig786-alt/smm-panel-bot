"""
=========================================================================================
🔥 SMM PANEL BOT - ENTERPRISE V18 ULTIMATE 🔥
(Features: Hot Services, Hindi/Eng Toggle, Confirm Order, Order Tracker, Leaderboard, Reviews, Logs & Conversational AI)
=========================================================================================
"""

import telebot, requests, sqlite3, logging, time, os, urllib.parse, threading, html
from io import BytesIO
from flask import Flask
from telebot.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime

# =======================================================================================
# 1. CONFIGURATION
# =======================================================================================
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

BOT_TOKEN = os.environ.get('BOT_TOKEN', '8228287584:AAH1UHatEvZtqG88NTbGx9kcU99-Z600vc8')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', 'AQ.Ab8RN6K9E8LLYov90BvynM1mZEJ_GYh_7N-LTcu6eefJW2m4YA')

bot = telebot.TeleBot(BOT_TOKEN, threaded=True, num_threads=15)

PROVIDERS = {
    "provider_primary": {
        "url": os.environ.get("API_URL_1", "https://iggrowbot.com/api/v2"),
        "key": os.environ.get("API_KEY_1", "797c2fb97d3fce189d397ef7639cc29f")
    }
}

FREE_VIEWS_SERVICE_ID = int(os.environ.get('FREE_VIEWS_SERVICE_ID', 1753))
FREE_VIEWS_PROVIDER = "https://iggrowbot.com/api/v2"
LOG_CHANNEL = "@csplogs"

ADMIN_ID = 6034840006
UPI_ID = "rahikhann@fam"
SUPPORT_USERNAME = "@itzdevrahi"
MIN_DEPOSIT = 15.0

user_states = {}
db_lock = threading.Lock()

app = Flask(__name__)
@app.route('/')
def home(): return "🔥 SMM V18 ENTERPRISE ONLINE 🔥"

# =======================================================================================
# 2. DATABASE ENGINE
# =======================================================================================
def execute_db(query, params=(), fetch=False, fetch_all=False, return_id=False):
    with db_lock:
        try:
            with sqlite3.connect('panel_v18.db', check_same_thread=False, timeout=20) as conn:
                c = conn.cursor()
                c.execute(query, params)
                if fetch: return c.fetchone()
                if fetch_all: return c.fetchall()
                if return_id:
                    conn.commit()
                    return c.lastrowid
                conn.commit()
                return True
        except Exception as e:
            logging.error(f"DB Error [{query}]: {e}")
            return False

def init_database():
    tables = [
        """CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT, balance REAL DEFAULT 0.0,
            total_spent REAL DEFAULT 0.0, free_views_credits INTEGER DEFAULT 0, referrer_id INTEGER,
            is_banned INTEGER DEFAULT 0, referral_code TEXT UNIQUE, language TEXT DEFAULT 'en', joined_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS orders (
            db_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, provider TEXT, api_order_id TEXT,
            service_id INTEGER, quantity INTEGER, cost REAL, profit REAL DEFAULT 0.0, status TEXT DEFAULT 'pending',
            auto_refill INTEGER DEFAULT 1, last_refill_check TIMESTAMP DEFAULT CURRENT_TIMESTAMP, placed_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS managed_services (
            service_id INTEGER PRIMARY KEY, platform TEXT, category TEXT, name TEXT, provider TEXT DEFAULT 'provider_primary',
            provider_service_id INTEGER, rate REAL, min_qty INTEGER DEFAULT 10, max_qty INTEGER DEFAULT 100000,
            avg_time TEXT DEFAULT 'Instant - 1 Hour', margin REAL DEFAULT 1.50, disabled INTEGER DEFAULT 0
        )""",
        "CREATE TABLE IF NOT EXISTS reviews (review_id INTEGER PRIMARY KEY AUTOINCREMENT, service_id INTEGER, user_id INTEGER, rating INTEGER, date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
        "CREATE TABLE IF NOT EXISTS transactions (tx_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount REAL, status TEXT, date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
        "CREATE TABLE IF NOT EXISTS tickets (ticket_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, message TEXT, status TEXT DEFAULT 'OPEN', reply TEXT)",
        "CREATE TABLE IF NOT EXISTS referrals (referrer_id INTEGER, referred_id INTEGER, reward_claimed INTEGER DEFAULT 1, PRIMARY KEY(referrer_id, referred_id))",
        "CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)"
    ]
    for table in tables: execute_db(table)
    if not execute_db("SELECT value FROM settings WHERE key='global_margin'", fetch=True):
        execute_db("INSERT INTO settings (key, value) VALUES ('global_margin', '1.50')")
    
    try: execute_db("ALTER TABLE orders ADD COLUMN profit REAL DEFAULT 0.0")
    except: pass
    try: execute_db("ALTER TABLE users ADD COLUMN language TEXT DEFAULT 'en'")
    except: pass

def get_lang(uid):
    res = execute_db("SELECT language FROM users WHERE user_id=?", (uid,), fetch=True)
    return res[0] if res else 'en'

def is_banned(uid):
    u = execute_db("SELECT is_banned FROM users WHERE user_id=?", (uid,), fetch=True)
    return u and u[0] == 1

# =======================================================================================
# 3. UTILITIES & AI ENGINE
# =======================================================================================
def call_provider_api(provider_name, action, extra=None):
    prov = PROVIDERS.get(provider_name, PROVIDERS["provider_primary"])
    payload = {'key': prov['key'], 'action': action}
    if extra: payload.update(extra)
    try:
        res = requests.post(prov['url'], data=payload, timeout=15)
        return res.json(), provider_name
    except: return None, provider_name

def detect_platform(category_str, name_str):
    c = f"{category_str} {name_str}".lower()
    if any(k in c for k in ['instagram', 'ig ', 'reels', 'insta']): return "📸 Instagram"
    elif any(k in c for k in ['telegram', 'tg ', 'tele ']): return "✈️ Telegram"
    elif any(k in c for k in ['youtube', 'yt ', 'shorts']): return "🔴 YouTube"
    elif any(k in c for k in ['facebook', 'fb ']): return "📘 Facebook"
    elif any(k in c for k in ['tiktok', 'tik tok']): return "🎵 TikTok"
    elif any(k in c for k in ['twitter', 'x ', 'tweet']): return "🐦 Twitter / X"
    return "⚡ General Boost"

def ask_gemini_conversational(user_message, history=""):
    if not GEMINI_API_KEY or GEMINI_API_KEY == 'YOUR_GEMINI_API_KEY_HERE': return "AI offline. Please open a human ticket."
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    prompt = (
        "You are the AI Assistant for 'Cheap SMM Panel'. Help the user pick services, understand how to buy, or check rules. "
        "Rules: Min deposit ₹15 via UPI QR. Orders take 1-24 hours. "
        "Keep answers friendly, short, and conversational. Use emojis. "
        "CRITICAL: If they complain about a failed order, refund, payment not added, or ask for an admin/human, "
        "you MUST include the EXACT tag [ESCALATE] in your response to trigger a human ticket."
    )
    payload = {
        "systemInstruction": {"parts": [{"text": prompt}]},
        "contents": [{"parts": [{"text": history + "\nUser: " + user_message}]}]
    }
    try:
        r = requests.post(url, json=payload, timeout=10)
        return r.json()['candidates'][0]['content']['parts'][0]['text']
    except: return "Connection error with AI brain."

# =======================================================================================
# 4. KEYBOARDS & TRANSLATIONS
# =======================================================================================
def main_kb(uid):
    lang = get_lang(uid)
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    
    if lang == 'hi':
        kb.add("🛒 सेवाएं ब्राउज़ करें", "🔥 हॉट / सस्ती सेवाएं")
        kb.add("💰 मेरी प्रोफाइल", "💳 फंड जोड़ें 💸")
        kb.add("📦 ऑर्डर इतिहास", "🏆 लीडरबोर्ड")
        kb.add("🎁 1K फ्री व्यूज", "🤝 रेफरल प्रोग्राम")
        kb.add("💬 AI असिस्टेंट से बात करें", "⚙️ सेटिंग्स (Language)")
    else:
        kb.add("🛒 Browse Services", "🔥 Hot / Cheap Services")
        kb.add("💰 My Profile", "💳 Add Funds 💸")
        kb.add("📦 Order History", "🏆 Leaderboard")
        kb.add("🎁 Claim 1K Free Views", "🤝 Referral Program")
        kb.add("💬 Chat with AI Assistant", "⚙️ Settings (Language)")
        
    if uid == ADMIN_ID:
        kb.add("🧠 Admin: Smart Sync", "👥 Admin: Manage Users")
        kb.add("📈 Admin: Margin", "📢 Admin: Broadcast")
        kb.add("📊 Admin: Stats", "🎫 Admin: Tickets")
    return kb

def back_cancel_kb(uid):
    lang = get_lang(uid)
    if lang == 'hi': return ReplyKeyboardMarkup(resize_keyboard=True, row_width=2).add("🔙 एक कदम पीछे", "❌ मेनू पर रद्द करें")
    return ReplyKeyboardMarkup(resize_keyboard=True, row_width=2).add("🔙 Step Back", "❌ Cancel to Menu")

# =======================================================================================
# 5. USER FLOW & SETTINGS
# =======================================================================================
@bot.message_handler(commands=['start'])
def h_start(m):
    uid = m.from_user.id
    user_states.pop(uid, None)
    u = execute_db("SELECT * FROM users WHERE user_id=?", (uid,), fetch=True)
    if not u:
        referrer_id = None
        args = m.text.split()
        if len(args) > 1 and args[1].startswith('ref_'):
            try:
                if int(args[1].replace('ref_', '')) != uid: referrer_id = int(args[1].replace('ref_', ''))
            except: pass
        execute_db("INSERT INTO users (user_id, username, first_name, referrer_id, referral_code) VALUES (?,?,?,?,?)",
                   (uid, m.from_user.username, m.from_user.first_name, referrer_id, f"REF{uid}"))
        if referrer_id:
            execute_db("INSERT OR IGNORE INTO referrals (referrer_id, referred_id) VALUES (?,?)", (referrer_id, uid))
            execute_db("UPDATE users SET free_views_credits = free_views_credits + 1 WHERE user_id=?", (referrer_id,))
            try: bot.send_message(referrer_id, "🎊 <b>A friend joined!</b>\n🎁 <b>You received +1 Free 1K Views Credit!</b>", parse_mode="HTML")
            except: pass

    if is_banned(uid): return bot.send_message(m.chat.id, "🚫 <b>YOUR ACCOUNT HAS BEEN BANNED.</b>", parse_mode="HTML")
    
    lang = get_lang(uid)
    name = html.escape(m.from_user.first_name or 'User')
    if lang == 'hi':
        msg = f"👋 <b>Cheap SMM Panel में आपका स्वागत है, {name}!</b> 🚀\n\n👇 <b>शुरुआत कैसे करें:</b>\n1️⃣ <b>'💳 फंड जोड़ें'</b> पर टैप करें\n2️⃣ <b>'🛒 सेवाएं ब्राउज़ करें'</b> पर टैप करें\n3️⃣ अपना लिंक पेस्ट करें और ग्रो करें!"
    else:
        msg = f"👋 <b>Welcome to Cheap SMM Panel, {name}!</b> 🚀\n\n👇 <b>HOW TO GET STARTED:</b>\n1️⃣ Tap <b>'💳 Add Funds'</b>\n2️⃣ Tap <b>'🛒 Browse Services'</b>\n3️⃣ Paste your link and grow!"
    bot.send_message(m.chat.id, msg, parse_mode="HTML", reply_markup=main_kb(uid))

@bot.message_handler(func=lambda m: m.text in ["❌ Cancel to Menu", "❌ मेनू पर रद्द करें"])
def h_cancel(m):
    user_states.pop(m.from_user.id, None)
    bot.send_message(m.chat.id, "🚫 <b>Action Cancelled!</b>", parse_mode="HTML", reply_markup=main_kb(m.from_user.id))

@bot.message_handler(func=lambda m: m.text in ["🔙 Step Back", "🔙 एक कदम पीछे"])
def h_step_back(m):
    uid = m.from_user.id
    current_state = user_states.get(uid, {}).get("state")

    if current_state == "get_qty":
        user_states[uid]["state"] = "get_link"
        bot.send_message(m.chat.id, "🔙 <b>Went 1 step back!</b>\n🔗 <b>STEP 1: Send the Target Link</b>", parse_mode="HTML", reply_markup=back_cancel_kb(uid))
    elif current_state == "get_link":
        user_states.pop(uid, None)
        h_browse(m)
    elif current_state == "fund_ss":
        user_states[uid]["state"] = "fund_amt"
        bot.send_message(m.chat.id, f"🔙 <b>Went 1 step back!</b>\n💸 <b>Enter deposit amount (₹):</b>", parse_mode="HTML", reply_markup=back_cancel_kb(uid))
    else:
        user_states.pop(uid, None)
        bot.send_message(m.chat.id, "🏠 <b>Returned to Main Menu.</b>", parse_mode="HTML", reply_markup=main_kb(uid))

@bot.message_handler(func=lambda m: m.text in ["⚙️ Settings (Language)", "⚙️ सेटिंग्स (Language)"])
def h_settings(m):
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🇺🇸 English", callback_data="lang_en"), InlineKeyboardButton("🇮🇳 हिन्दी (Hindi)", callback_data="lang_hi"))
    bot.send_message(m.chat.id, "⚙️ <b>Select your language / अपनी भाषा चुनें:</b>", parse_mode="HTML", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("lang_"))
def h_set_lang(c):
    lang = c.data.split("_")[1]
    execute_db("UPDATE users SET language=? WHERE user_id=?", (lang, c.from_user.id))
    bot.delete_message(c.message.chat.id, c.message.message_id)
    bot.send_message(c.message.chat.id, "✅ Language Updated! / भाषा बदल दी गई है!", reply_markup=main_kb(c.from_user.id))

# =======================================================================================
# 6. PROFILE, HISTORY & LEADERBOARD
# =======================================================================================
@bot.message_handler(func=lambda m: m.text in ["💰 My Profile", "💰 मेरी प्रोफाइल"])
def h_profile(m):
    u = execute_db("SELECT balance, total_spent, free_views_credits FROM users WHERE user_id=?", (m.from_user.id,), fetch=True)
    if not u: return
    ref_count = execute_db("SELECT COUNT(*) FROM referrals WHERE referrer_id=?", (m.from_user.id,), fetch=True)[0]
    msg = f"👤 <b>YOUR PROFILE</b>\n━━━━━━━━━━━━━━━━━━━\n🆔 <b>ID:</b> <code>{m.from_user.id}</code>\n💳 <b>Wallet:</b> ₹{u[0]:.2f}\n📈 <b>Spent:</b> ₹{u[1]:.2f}\n🎁 <b>Free Views:</b> {u[2]}\n👥 <b>Referrals:</b> {ref_count}"
    bot.send_message(m.chat.id, msg, parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text in ["📦 Order History", "📦 ऑर्डर इतिहास"])
def h_order_history(m):
    orders = execute_db("SELECT db_id, api_order_id, quantity, cost, status FROM orders WHERE user_id=? ORDER BY placed_time DESC LIMIT 5", (m.from_user.id,), fetch_all=True)
    if not orders: return bot.send_message(m.chat.id, "📦 No orders yet!", parse_mode="HTML")
    
    msg = "📦 <b>RECENT ORDERS:</b>\n━━━━━━━━━━━━━━━━━━━\n"
    kb = InlineKeyboardMarkup(row_width=2)
    track_buttons = []
    
    for o in orders:
        msg += f"🧾 <b>Order #{o[0]}</b> | 🔢 {o[2]} units | 💰 ₹{o[3]:.2f}\n📊 <b>Status:</b> <code>{o[4]}</code>\n───────────────────\n"
        if o[4].lower() in ['pending', 'in progress', 'processing']:
            track_buttons.append(InlineKeyboardButton(f"🔍 Track #{o[0]}", callback_data=f"trk_{o[0]}"))
    
    if track_buttons: kb.add(*track_buttons)
    bot.send_message(m.chat.id, msg, parse_mode="HTML", reply_markup=kb if track_buttons else None)

@bot.callback_query_handler(func=lambda c: c.data.startswith("trk_"))
def h_track_order(c):
    bot.answer_callback_query(c.id, "Fetching live API data...")
    db_id = int(c.data.split("_")[1])
    order = execute_db("SELECT provider, api_order_id FROM orders WHERE db_id=? AND user_id=?", (db_id, c.from_user.id), fetch=True)
    if not order: return
    
    res, _ = call_provider_api(order[0], 'status', {'order': order[1]})
    if res and 'status' in res:
        start = res.get('start_count', 'N/A')
        remains = res.get('remains', 'N/A')
        stat = res.get('status', 'Unknown').capitalize()
        execute_db("UPDATE orders SET status=? WHERE db_id=?", (stat, db_id)) 
        
        bot.send_message(c.message.chat.id, f"🔍 <b>LIVE TRACKING (Order #{db_id})</b>\n\n🟢 <b>Start Count:</b> <code>{start}</code>\n⏳ <b>Remaining:</b> <code>{remains}</code>\n📊 <b>Current Status:</b> <code>{stat}</code>", parse_mode="HTML")
    else:
        bot.send_message(c.message.chat.id, "⚠️ Provider API is currently slow or unresponsive. Try again later.")

@bot.message_handler(func=lambda m: m.text in ["🏆 Leaderboard", "🏆 लीडरबोर्ड", "/leaderboard"])
def h_leaderboard(m):
    top = execute_db("SELECT user_id, SUM(cost) as spent FROM orders WHERE placed_time >= datetime('now', '-7 days') GROUP BY user_id ORDER BY spent DESC LIMIT 5", fetch_all=True)
    msg = "🏆 <b>WEEKLY TOP SPENDERS</b> 🏆\n━━━━━━━━━━━━━━━━━━━\n"
    medals = ["🥇", "🥈", "🥉", "🏅", "🏅"]
    for i, t in enumerate(top):
        msg += f"{medals[i]} <b>User ID:</b> <code>{str(t[0])[:4]}****</code> - Spent: ₹{t[1]:.2f}\n"
    bot.send_message(m.chat.id, msg, parse_mode="HTML")

# =======================================================================================
# 7. ADD FUNDS FLOW
# =======================================================================================
@bot.message_handler(func=lambda m: m.text == "💳 Add Funds 💸" or m.text == "💳 फंड जोड़ें 💸")
def h_add_funds(m):
    if is_banned(m.from_user.id): return bot.send_message(m.chat.id, "🚫 You are banned.", parse_mode="HTML")
    user_states[m.from_user.id] = {"state": "fund_amt"}
    bot.send_message(m.chat.id, f"💸 <b>Enter deposit amount (₹):</b>\n(Minimum: <code>₹{MIN_DEPOSIT}</code>)", parse_mode="HTML", reply_markup=back_cancel_kb(m.from_user.id))

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get("state") == "fund_amt")
def h_fund_qr(m):
    try:
        amt = float(m.text.strip())
        if amt < MIN_DEPOSIT: return bot.send_message(m.chat.id, f"🚫 Minimum deposit is <code>₹{MIN_DEPOSIT}</code>", parse_mode="HTML", reply_markup=back_cancel_kb(m.from_user.id))
        user_states[m.from_user.id] = {"state": "fund_ss", "amt": amt}
        qr = f"https://api.qrserver.com/v1/create-qr-code/?size=400x400&data={urllib.parse.quote(f'upi://pay?pa={UPI_ID}&am={amt}&cu=INR')}"
        res = requests.get(qr, timeout=10)
        bot.send_photo(m.chat.id, BytesIO(res.content), caption=f"💳 <b>PAY EXACTLY ₹{amt}</b>\nUPI ID: <code>{UPI_ID}</code>\n\n📸 <b>Send screenshot here after paying!</b>", parse_mode="HTML", reply_markup=back_cancel_kb(m.from_user.id))
    except: bot.send_message(m.chat.id, "❌ Numbers only.", parse_mode="HTML")

@bot.message_handler(content_types=['photo'])
def h_payment_ss(m):
    uid = m.from_user.id
    if user_states.get(uid, {}).get("state") == "fund_ss":
        amt = user_states[uid]["amt"]
        tx = execute_db("INSERT INTO transactions (user_id, amount, status) VALUES (?, ?, 'PENDING')", (uid, amt), return_id=True)
        kb = InlineKeyboardMarkup().add(InlineKeyboardButton("✅ Approve", callback_data=f"ap_{tx}_{uid}_{amt}"), InlineKeyboardButton("❌ Reject", callback_data=f"rj_{tx}_{uid}"))
        bot.send_photo(ADMIN_ID, m.photo[-1].file_id, caption=f"🚨 <b>DEPOSIT</b>\nUser: <code>{uid}</code>\nAmount: <code>₹{amt}</code>\nTXN: <code>{tx}</code>", parse_mode="HTML", reply_markup=kb)
        bot.send_message(m.chat.id, "✅ <b>Screenshot Received!</b> Waiting for admin approval.", parse_mode="HTML", reply_markup=main_kb(uid))
        user_states.pop(uid, None)

# =======================================================================================
# 8. CONVERSATIONAL AI ASSISTANT
# =======================================================================================
@bot.message_handler(func=lambda m: m.text in ["💬 Chat with AI Assistant", "💬 AI असिस्टेंट से बात करें"])
def h_chat_ai_start(m):
    user_states[m.from_user.id] = {"state": "ai_chat", "history": ""}
    bot.send_message(m.chat.id, "🤖 <b>AI Assistant Online!</b>\n\nI can help you pick the best services, explain how to add funds, or answer panel questions! Type your message below. (Type 'Exit' to leave).", parse_mode="HTML", reply_markup=back_cancel_kb(m.from_user.id))

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get("state") == "ai_chat")
def h_ai_chat_process(m):
    uid = m.from_user.id
    if m.text.lower() in ["exit", "quit", "cancel", "stop"]:
        user_states.pop(uid, None)
        return bot.send_message(m.chat.id, "🏠 <b>Returned to Main Menu.</b>", parse_mode="HTML", reply_markup=main_kb(uid))

    bot.send_chat_action(m.chat.id, 'typing')
    hist = user_states[uid].get("history", "")
    ai_reply = ask_gemini_conversational(m.text, hist)
    
    if "[ESCALATE]" in ai_reply:
        clean = ai_reply.replace("[ESCALATE]", "").strip()
        if clean: bot.send_message(m.chat.id, f"🤖 <b>AI:</b> {clean}", parse_mode="HTML")
        tid = execute_db("INSERT INTO tickets (user_id, message) VALUES (?,?)", (uid, m.text), return_id=True)
        bot.send_message(m.chat.id, f"✅ <b>I have escalated this issue! Ticket #{tid} created.</b> A human admin will review this shortly.", parse_mode="HTML", reply_markup=main_kb(uid))
        try: bot.send_message(ADMIN_ID, f"🚨 <b>AI ESCALATED TICKET #{tid}</b>\nFrom: <code>{uid}</code>\n💬 {m.text}", parse_mode="HTML")
        except: pass
        user_states.pop(uid, None)
    else:
        new_hist = hist + f"\nUser: {m.text}\nAI: {ai_reply}"
        user_states[uid]["history"] = new_hist[-1000:] 
        bot.send_message(m.chat.id, f"🤖 <b>AI:</b> {ai_reply}", parse_mode="HTML")

# =======================================================================================
# 9. PLATFORM BROWSING & HOT SERVICES
# =======================================================================================
@bot.message_handler(func=lambda m: m.text in ["🔥 Hot / Cheap Services", "🔥 हॉट / सस्ती सेवाएं"])
def h_hot_services(m):
    if is_banned(m.from_user.id): return
    hot = execute_db("SELECT service_id, platform, name, MIN(rate*margin) FROM managed_services WHERE disabled=0 GROUP BY platform", fetch_all=True)
    if not hot: return bot.send_message(m.chat.id, "⚠️ No services loaded.")
    
    kb = InlineKeyboardMarkup(row_width=1)
    for s in hot:
        kb.add(InlineKeyboardButton(f"🔥 {s[1]} - ₹{s[3]:.2f}/1K", callback_data=f"buy_{s[0]}"))
    
    bot.send_message(m.chat.id, "🔥 <b>TRENDING & CHEAPEST SERVICES</b> 📉\n━━━━━━━━━━━━━━━━━━━\n<i>The absolute lowest prices guaranteed!</i>👇", parse_mode="HTML", reply_markup=kb)

@bot.message_handler(func=lambda m: m.text in ["🛒 Browse Services", "🛒 सेवाएं ब्राउज़ करें", "🛒 Browse Services 🚀"])
def h_browse(m):
    if is_banned(m.from_user.id): return bot.send_message(m.chat.id, "🚫 You are banned.")
    user_states.pop(m.from_user.id, None)
    platforms = execute_db("SELECT DISTINCT platform FROM managed_services WHERE disabled=0 ORDER BY platform ASC", fetch_all=True)
    if not platforms: return bot.send_message(m.chat.id, "⚠️ No services loaded! Admin needs to run Smart Sync.")
    kb = InlineKeyboardMarkup(row_width=2)
    for idx, p in enumerate(platforms): kb.add(InlineKeyboardButton(f"{p[0]}", callback_data=f"plt_{idx}"))
    bot.send_message(m.chat.id, "🛒 <b>CHOOSE YOUR PLATFORM:</b> 🌐✨\n━━━━━━━━━━━━━━━━━━━\n👇 <i>Select platform:</i>", parse_mode="HTML", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("plt_"))
def h_platform_view(c):
    bot.answer_callback_query(c.id)
    idx = int(c.data.split("_")[1])
    platforms = execute_db("SELECT DISTINCT platform FROM managed_services WHERE disabled=0 ORDER BY platform ASC", fetch_all=True)
    if idx >= len(platforms): return
    platform_name = platforms[idx][0]
    cats = execute_db("SELECT DISTINCT category FROM managed_services WHERE platform=? AND disabled=0", (platform_name,), fetch_all=True)
    kb = InlineKeyboardMarkup(row_width=1)
    for c_idx, cat in enumerate(cats): kb.add(InlineKeyboardButton(f"📁 {cat[0]}", callback_data=f"cat_{idx}_{c_idx}"))
    kb.add(InlineKeyboardButton("🔙 Back to Platforms", callback_data="back_platforms"))
    bot.edit_message_text(f"📂 <b>{platform_name.upper()} CATEGORIES</b> 🚀\n━━━━━━━━━━━━━━━━━━━\n👇 <i>Select a category:</i>", c.message.chat.id, c.message.message_id, parse_mode="HTML", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data == "back_platforms")
def h_back_platforms(c):
    bot.answer_callback_query(c.id)
    platforms = execute_db("SELECT DISTINCT platform FROM managed_services WHERE disabled=0 ORDER BY platform ASC", fetch_all=True)
    kb = InlineKeyboardMarkup(row_width=2)
    for idx, p in enumerate(platforms): kb.add(InlineKeyboardButton(f"{p[0]}", callback_data=f"plt_{idx}"))
    bot.edit_message_text("🛒 <b>CHOOSE PLATFORM:</b>\n👇 <i>Select platform:</i>", c.message.chat.id, c.message.message_id, parse_mode="HTML", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("cat_"))
def h_category_services(c):
    bot.answer_callback_query(c.id)
    _, p_idx, c_idx = c.data.split("_")
    p_idx, c_idx = int(p_idx), int(c_idx)
    platforms = execute_db("SELECT DISTINCT platform FROM managed_services WHERE disabled=0 ORDER BY platform ASC", fetch_all=True)
    platform_name = platforms[p_idx][0]
    cats = execute_db("SELECT DISTINCT category FROM managed_services WHERE platform=? AND disabled=0", (platform_name,), fetch_all=True)
    category_name = cats[c_idx][0]
    svcs = execute_db("SELECT service_id, name, rate, margin FROM managed_services WHERE platform=? AND category=? AND disabled=0", (platform_name, category_name), fetch_all=True)
    
    kb = InlineKeyboardMarkup(row_width=1)
    for s in svcs: kb.add(InlineKeyboardButton(f"⭐ {s[1][:30]}.. - ₹{(s[2]*s[3]):.2f}/1K", callback_data=f"card_{s[0]}_{p_idx}_{c_idx}"))
    kb.add(InlineKeyboardButton(f"🔙 Back to {platform_name}", callback_data=f"plt_{p_idx}"))
    bot.edit_message_text(f"📂 <b>{html.escape(category_name.upper())}</b> 📊\n━━━━━━━━━━━━━━━━━━━\n👇 <i>Tap a service:</i>", c.message.chat.id, c.message.message_id, parse_mode="HTML", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("card_"))
def h_card_view(c):
    bot.answer_callback_query(c.id)
    _, sid, p_idx, c_idx = c.data.split("_")
    svc = execute_db("SELECT service_id, platform, name, rate, min_qty, max_qty, avg_time, margin FROM managed_services WHERE service_id=?", (int(sid),), fetch=True)
    if not svc: return
    
    avg_rating = execute_db("SELECT AVG(rating) FROM reviews WHERE service_id=?", (svc[0],), fetch=True)[0]
    rating_str = f"{avg_rating:.1f}/5.0 ⭐" if avg_rating else "No reviews yet"
    
    final_price = svc[3] * svc[7]
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("🚀 Order This Service Now", callback_data=f"buy_{svc[0]}"))
    kb.add(InlineKeyboardButton("🔙 Back to Services", callback_data=f"cat_{p_idx}_{c_idx}"))
    
    msg = (f"🏷️ <b>SERVICE DETAILS</b> 📋\n━━━━━━━━━━━━━━━━━━━\n📌 <b>Service:</b> {html.escape(svc[2])}\n"
           f"💰 <b>Price:</b> <code>₹{final_price:.2f}</code> per 1,000\n📊 <b>Limits:</b> Min <code>{svc[4]:,}</code> — Max <code>{svc[5]:,}</code>\n"
           f"⏱️ <b>Avg Speed:</b> <code>{svc[6]}</code>\n♻️ <b>Auto-Refill:</b> <code>Active</code> 🛡️\n"
           f"⭐ <b>Customer Rating:</b> {rating_str}")
    bot.edit_message_text(msg, c.message.chat.id, c.message.message_id, parse_mode="HTML", reply_markup=kb)

# =======================================================================================
# 10. ORDERING & DOUBLE CONFIRMATION SYSTEM
# =======================================================================================
@bot.callback_query_handler(func=lambda c: c.data.startswith("buy_"))
def h_buy_service(c):
    bot.answer_callback_query(c.id)
    if is_banned(c.from_user.id): return bot.send_message(c.message.chat.id, "🚫 You are banned.")
    sid = int(c.data.split("_")[1])
    user_states[c.from_user.id] = {"state": "get_link", "sid": sid}
    bot.send_message(c.message.chat.id, "🔗 <b>STEP 1: Send the Target Link</b> 📌\n<i>Paste the public URL:</i>", parse_mode="HTML", reply_markup=back_cancel_kb(c.from_user.id))

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get("state") == "get_link")
def h_link_input(m):
    user_states[m.from_user.id].update({"state": "get_qty", "link": m.text.strip()})
    bot.send_message(m.chat.id, "✅ <b>Link Received!</b> 🔗\n\n🔢 <b>STEP 2: Enter Quantity</b> 📊\n<i>Type numbers only:</i>", parse_mode="HTML", reply_markup=back_cancel_kb(m.from_user.id))

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get("state") == "get_qty")
def h_qty_input(m):
    uid = m.from_user.id
    state = user_states[uid]
    try: qty = int(m.text.strip())
    except: return bot.send_message(m.chat.id, "❌ Numbers only.", reply_markup=back_cancel_kb(uid))

    svc = execute_db("SELECT provider, provider_service_id, rate, margin, min_qty, max_qty, name FROM managed_services WHERE service_id=?", (state["sid"],), fetch=True)
    if not svc: return
    if qty < svc[4] or qty > svc[5]:
        return bot.send_message(m.chat.id, f"🚫 <b>Out of Range!</b> Min: <code>{svc[4]}</code> | Max: <code>{svc[5]}</code>", parse_mode="HTML", reply_markup=back_cancel_kb(uid))

    cost = (qty / 1000.0) * (svc[2] * svc[3])
    profit = cost - ((qty / 1000.0) * svc[2])
    u_bal = execute_db("SELECT balance FROM users WHERE user_id=?", (uid,), fetch=True)[0]
    
    if u_bal < cost: 
        user_states.pop(uid, None)
        return bot.send_message(m.chat.id, f"❌ <b>INSUFFICIENT BALANCE!</b>\nNeed: ₹{cost:.2f} | Wallet: ₹{u_bal:.2f}", parse_mode="HTML", reply_markup=main_kb(uid))

    # Save state for confirmation
    user_states[uid].update({"state": "confirm_order", "qty": qty, "cost": cost, "profit": profit, "p_sid": svc[1], "prov": svc[0], "s_name": svc[6]})
    
    msg = (f"🛑 <b>ORDER CONFIRMATION</b> 🛑\n━━━━━━━━━━━━━━━━━━━\n"
           f"📌 <b>Service:</b> {html.escape(svc[6])}\n"
           f"🔗 <b>Link:</b> <code>{state['link']}</code>\n"
           f"📦 <b>Quantity:</b> <code>{qty:,}</code>\n"
           f"💰 <b>Total Cost:</b> <code>₹{cost:.2f}</code>\n━━━━━━━━━━━━━━━━━━━\n"
           f"<i>Please double-check your link. Orders cannot be canceled once placed!</i>")
           
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("✅ Confirm & Pay", callback_data="pay_yes"), InlineKeyboardButton("❌ Cancel Order", callback_data="pay_no"))
    bot.send_message(m.chat.id, msg, parse_mode="HTML", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data in ["pay_yes", "pay_no"])
def h_confirm_order(c):
    bot.answer_callback_query(c.id)
    uid = c.from_user.id
    state = user_states.get(uid)
    if not state or state.get("state") != "confirm_order": 
        return bot.delete_message(c.message.chat.id, c.message.message_id)
    
    if c.data == "pay_no":
        user_states.pop(uid, None)
        bot.edit_message_text("🚫 <b>Order Cancelled.</b> Your wallet was not charged.", c.message.chat.id, c.message.message_id, parse_mode="HTML")
        return bot.send_message(c.message.chat.id, "🏠 <b>Main Menu</b>", reply_markup=main_kb(uid))
        
    # Execute Order
    bot.edit_message_text("⏳ <i>Processing order securely...</i>", c.message.chat.id, c.message.message_id, parse_mode="HTML")
    api_res, prov_used = call_provider_api(state["prov"], 'add', {'service': state["p_sid"], 'link': state['link'], 'quantity': state['qty']})
    
    if api_res and 'order' in api_res:
        execute_db("UPDATE users SET balance=balance-?, total_spent=total_spent+? WHERE user_id=?", (state["cost"], state["cost"], uid))
        execute_db("INSERT INTO orders (user_id, provider, api_order_id, service_id, quantity, cost, profit, auto_refill) VALUES (?,?,?,?,?,?,?,1)",
                   (uid, prov_used, api_res['order'], state["sid"], state["qty"], state["cost"], state["profit"]))
        
        bot.delete_message(c.message.chat.id, c.message.message_id)
        bot.send_message(c.message.chat.id, f"✅ <b>ORDER DISPATCHED!</b> 🎉\n🧾 <b>ID:</b> <code>{api_res['order']}</code>\n💰 <b>Paid:</b> ₹{state['cost']:.2f}", parse_mode="HTML", reply_markup=main_kb(uid))
        
        # Broadcast to Log Channel
        log_msg = (f"🛍️ <b>NEW ORDER PLACED</b>\n━━━━━━━━━━━━━━━━━━━\n"
                   f"👤 <b>User:</b> <code>{uid}</code>\n"
                   f"🏷️ <b>Service:</b> {html.escape(state['s_name'])}\n"
                   f"📦 <b>Qty:</b> {state['qty']:,}\n"
                   f"💰 <b>Cost:</b> ₹{state['cost']:.2f}\n"
                   f"🔗 <b>Link:</b> {state['link']}")
        try: bot.send_message(LOG_CHANNEL, log_msg, parse_mode="HTML")
        except: pass
    else: 
        bot.delete_message(c.message.chat.id, c.message.message_id)
        bot.send_message(c.message.chat.id, "❌ <b>Provider Error! Server might be busy. Wallet not charged.</b>", parse_mode="HTML", reply_markup=main_kb(uid))
    user_states.pop(uid, None)

# =======================================================================================
# 11. REVIEWS SYSTEM
# =======================================================================================
@bot.callback_query_handler(func=lambda c: c.data.startswith("rate_"))
def h_save_rating(c):
    parts = c.data.split("_")
    sid, rating = int(parts[1]), int(parts[2])
    execute_db("INSERT INTO reviews (service_id, user_id, rating) VALUES (?,?,?)", (sid, c.from_user.id, rating))
    bot.edit_message_text(f"✅ <b>Thank you!</b> You rated this service {rating} Stars ⭐", c.message.chat.id, c.message.message_id, parse_mode="HTML")

# =======================================================================================
# 12. ADMIN CONTROLS (Stats, Broadcast, Sync, Users)
# =======================================================================================
@bot.callback_query_handler(func=lambda c: c.data.startswith(("ap_", "rj_")))
def h_admin_approval(c):
    bot.answer_callback_query(c.id)
    if c.from_user.id != ADMIN_ID: return
    p = c.data.split("_")
    action, tx, uid = p[0], p[1], p[2]
    if action == "ap":
        amt = float(p[3])
        execute_db("UPDATE users SET balance=balance+? WHERE user_id=?", (amt, uid))
        execute_db("UPDATE transactions SET status='APPROVED' WHERE tx_id=?", (tx,))
        bot.edit_message_caption(f"✅ <b>APPROVED TXN-{tx}</b> | Added ₹{amt}", c.message.chat.id, c.message.message_id, parse_mode="HTML")
        try: bot.send_message(uid, f"🎉 <b>PAYMENT APPROVED!</b> <code>₹{amt}</code> added to wallet!", parse_mode="HTML")
        except: pass
    else:
        execute_db("UPDATE transactions SET status='REJECTED' WHERE tx_id=?", (tx,))
        bot.edit_message_caption(f"❌ <b>REJECTED TXN-{tx}</b>", c.message.chat.id, c.message.message_id, parse_mode="HTML")
        try: bot.send_message(uid, f"❌ <b>DEPOSIT REJECTED!</b> Contact Support.", parse_mode="HTML")
        except: pass

@bot.message_handler(func=lambda m: m.text == "📊 Admin: Stats" and m.from_user.id == ADMIN_ID)
def h_admin_stats(m):
    profit_row = execute_db("SELECT SUM(profit) FROM orders WHERE date(placed_time) = date('now')", fetch=True)
    profit_today = profit_row[0] if profit_row and profit_row[0] else 0.0
    active_users = execute_db("SELECT COUNT(*) FROM users WHERE is_banned=0", fetch=True)[0]
    wallet_funds = execute_db("SELECT SUM(balance) FROM users", fetch=True)[0] or 0.0
    orders_today = execute_db("SELECT COUNT(*) FROM orders WHERE date(placed_time) = date('now')", fetch=True)[0]
    msg = (f"📊 <b>ADMIN ANALYTICS</b> 📊\n━━━━━━━━━━━━━━━━━━━\n💵 <b>Profit Today:</b> <code>₹{profit_today:.2f}</code>\n"
           f"👥 <b>Active Users:</b> <code>{active_users}</code>\n💰 <b>User Wallets:</b> <code>₹{wallet_funds:.2f}</code>\n"
           f"📦 <b>Orders Today:</b> <code>{orders_today}</code>\n━━━━━━━━━━━━━━━━━━━")
    bot.send_message(ADMIN_ID, msg, parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text == "🧠 Admin: Smart Sync" and m.from_user.id == ADMIN_ID)
def h_admin_smart_sync(m):
    bot.send_message(ADMIN_ID, "🧠 <i>Smart Sync running...</i>", parse_mode="HTML")
    res, _ = call_provider_api("provider_primary", "services")
    if not res or not isinstance(res, list): return bot.send_message(ADMIN_ID, "❌ API Failed.")
    execute_db("DELETE FROM managed_services")
    margin = float(execute_db("SELECT value FROM settings WHERE key='global_margin'", fetch=True)[0])
    
    categories = {}
    for s in res:
        cat_name = s.get('category', 'General')
        if cat_name not in categories: categories[cat_name] = []
        categories[cat_name].append(s)
        
    added = 0
    for cat_name, svcs in categories.items():
        cat_lower = cat_name.lower()
        if any(x in cat_lower for x in ['like', 'view', 'share']):
            svcs.sort(key=lambda x: float(x.get('rate', 9999)))
            best = svcs[:2]
        elif any(x in cat_lower for x in ['follower', 'subscriber']):
            hq = [x for x in svcs if any(k in x.get('name', '').lower() for k in ['refill', 'guarantee', 'hq'])]
            if not hq: hq = svcs
            hq.sort(key=lambda x: float(x.get('rate', 0)), reverse=True)
            best = hq[-3:]
        else:
            svcs.sort(key=lambda x: float(x.get('rate', 9999)))
            best = svcs[:1]
            
        for s in best:
            try:
                platform = detect_platform(cat_name, s.get('name', ''))
                avg = "10-60 Mins" if "instant" in s.get('name', '').lower() else "1-24 Hours"
                execute_db("""INSERT OR REPLACE INTO managed_services (service_id, platform, category, name, provider, provider_service_id, rate, min_qty, max_qty, avg_time, margin, disabled) VALUES (?, ?, ?, ?, 'provider_primary', ?, ?, ?, ?, ?, ?, 0)""",
                    (int(s['service']), platform, cat_name, s['name'], int(s['service']), float(s['rate']), int(s.get('min', 10)), int(s.get('max', 100000)), avg, margin))
                added += 1
            except: continue
    bot.send_message(ADMIN_ID, f"✅ <b>Sync Complete!</b> {added} services added.", parse_mode="HTML")

# =======================================================================================
# 13. BACKGROUND TASKS (Notifications, Refill)
# =======================================================================================
def auto_refill_and_status_monitor():
    while True:
        try:
            # 1. Check Order Statuses
            orders = execute_db("SELECT db_id, provider, api_order_id, status, user_id, quantity, service_id FROM orders WHERE status IN ('pending', 'In progress', 'Processing', 'Pending')", fetch_all=True)
            if orders:
                for o in orders:
                    res, _ = call_provider_api(o[1], 'status', {'order': o[2]})
                    if res and 'status' in res:
                        new_status = res['status'].capitalize()
                        if new_status != o[3]:
                            execute_db("UPDATE orders SET status=? WHERE db_id=?", (new_status, o[0]))
                            
                            # Live DM Notification
                            if new_status in ['Completed', 'Partial', 'Canceled']:
                                svc = execute_db("SELECT name FROM managed_services WHERE service_id=?", (o[6],), fetch=True)
                                svc_name = svc[0] if svc else "Service"
                                emoji = "✅" if new_status == "Completed" else "⚠️"
                                
                                try: 
                                    bot.send_message(o[4], f"{emoji} <b>Order Update!</b> 🎉\nYour order of <b>{o[5]:,} {html.escape(svc_name)}</b> is now <b>{new_status.upper()}</b>!", parse_mode="HTML")
                                    # Prompt for review if completed
                                    if new_status == "Completed":
                                        r_kb = InlineKeyboardMarkup(row_width=5)
                                        r_kb.add(
                                            InlineKeyboardButton("1", callback_data=f"rate_{o[6]}_1"), InlineKeyboardButton("2", callback_data=f"rate_{o[6]}_2"),
                                            InlineKeyboardButton("3", callback_data=f"rate_{o[6]}_3"), InlineKeyboardButton("4", callback_data=f"rate_{o[6]}_4"),
                                            InlineKeyboardButton("5 ⭐", callback_data=f"rate_{o[6]}_5")
                                        )
                                        bot.send_message(o[4], "How was the speed and quality? Please rate 1 to 5 stars:", reply_markup=r_kb)
                                except: pass

            # 2. Trigger Auto-Refills
            refillable = execute_db("SELECT db_id, provider, api_order_id, user_id FROM orders WHERE auto_refill=1 AND status IN ('Completed', 'Partial')", fetch_all=True)
            if refillable:
                for ro in refillable:
                    res, _ = call_provider_api(ro[1], 'refill', {'order': ro[2]})
                    if res and 'refill' in res: 
                        execute_db("UPDATE orders SET last_refill_check=CURRENT_TIMESTAMP WHERE db_id=?", (ro[0],))
                        
        except Exception as e:
            logging.error(f"Monitor error: {e}")
        time.sleep(300)

if __name__ == '__main__':
    init_database()
    try: bot.remove_webhook(); time.sleep(1)
    except: pass
    threading.Thread(target=lambda: bot.infinity_polling(skip_pending=True, timeout=60), daemon=True).start()
    threading.Thread(target=auto_refill_and_status_monitor, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
