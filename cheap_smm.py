"""
=========================================================================================
🔥 SMM PANEL BOT - ENTERPRISE V17 ULTIMATE 🔥
(NEW: AI Support Chatbot, Admin Analytics Dashboard, Live Auto-DMs for Order Updates)
=========================================================================================
"""

import telebot, requests, sqlite3, logging, time, os, urllib.parse, threading, html
from io import BytesIO
from flask import Flask
from telebot.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton

# =======================================================================================
# 1. CONFIGURATION
# =======================================================================================
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

# ⚠️ REPLACE THESE WITH YOUR KEYS!
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8228287584:AAGbp8FiWPTx-2IPd0LxVDNRU8tjgwrwKN0')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', 'AQ.Ab8RN6K9E8LLYov90BvynM1mZEJ_GYh_7N-LTcu6eefJW2m4YA')

bot = telebot.TeleBot(BOT_TOKEN, threaded=True, num_threads=10)

PROVIDERS = {
    "provider_primary": {
        "url": os.environ.get("API_URL_1", "https://iggrowbot.com/api/v2"),
        "key": os.environ.get("API_KEY_1", "797c2fb97d3fce189d397ef7639cc29f")
    }
}

FREE_VIEWS_SERVICE_ID = int(os.environ.get('FREE_VIEWS_SERVICE_ID', 1753))
FREE_VIEWS_PROVIDER = "https://iggrowbot.com/api/v2"

ADMIN_ID = 6034840006
UPI_ID = "rahikhann@fam"
SUPPORT_USERNAME = "@itzdevrahi"
MIN_DEPOSIT = 15.0

user_states = {}
db_lock = threading.Lock()

app = Flask(__name__)
@app.route('/')
def home(): return "🔥 SMM V17 ENTERPRISE ONLINE (WITH AI & ANALYTICS) 🔥"

# =======================================================================================
# 2. DATABASE ENGINE
# =======================================================================================
def execute_db(query, params=(), fetch=False, fetch_all=False, return_id=False):
    with db_lock:
        try:
            with sqlite3.connect('panel_v17.db', check_same_thread=False, timeout=20) as conn:
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
            is_banned INTEGER DEFAULT 0, referral_code TEXT UNIQUE, joined_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
        "CREATE TABLE IF NOT EXISTS transactions (tx_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount REAL, status TEXT, date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
        "CREATE TABLE IF NOT EXISTS tickets (ticket_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, message TEXT, status TEXT DEFAULT 'OPEN', reply TEXT)",
        "CREATE TABLE IF NOT EXISTS referrals (referrer_id INTEGER, referred_id INTEGER, reward_claimed INTEGER DEFAULT 1, PRIMARY KEY(referrer_id, referred_id))",
        "CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)"
    ]
    for table in tables: execute_db(table)
    if not execute_db("SELECT value FROM settings WHERE key='global_margin'", fetch=True):
        execute_db("INSERT INTO settings (key, value) VALUES ('global_margin', '1.50')")
    
    # Safely retrofit 'profit' column if upgrading from an older DB version
    try: execute_db("ALTER TABLE orders ADD COLUMN profit REAL DEFAULT 0.0")
    except: pass

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

def ask_gemini_support(user_message):
    if not GEMINI_API_KEY or GEMINI_API_KEY == 'YOUR_GEMINI_API_KEY_HERE': return None
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    prompt = (
        "You are the AI Support Agent for 'Cheap SMM Panel'. Keep answers extremely brief, polite, and helpful. "
        "Rules: 1. Min deposit is ₹15 via UPI. 2. Users must upload a screenshot after paying to add funds. "
        "3. Orders take 1-24 hours depending on the service. "
        "If a user complains about a failed payment, refund, complex error, or requests human help, "
        "you MUST include the exact word [ESCALATE] in your response so our system forwards it to the human admin."
    )
    payload = {
        "systemInstruction": {"parts": [{"text": prompt}]},
        "contents": [{"parts": [{"text": user_message}]}]
    }
    try:
        r = requests.post(url, json=payload, timeout=10)
        return r.json()['candidates'][0]['content']['parts'][0]['text']
    except: return None

# =======================================================================================
# 4. KEYBOARDS
# =======================================================================================
def main_kb(uid):
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add("🛒 Browse Services 🚀", "🎁 Claim Free 1K Views 🌟")
    kb.add("💰 My Profile 👤", "💳 Add Funds 💸")
    kb.add("📦 Order History 📜", "🤝 Referral Program 👥")
    kb.add("📞 Support 🎫")
    if uid == ADMIN_ID:
        kb.add("🧠 Admin: Smart Sync", "👥 Admin: Manage Users")
        kb.add("📈 Admin: Margin", "📢 Admin: Broadcast")
        kb.add("📊 Admin: Stats", "🎫 Admin: Tickets")
        kb.add("💾 Admin: Backup DB", "🔄 Admin: Restore DB")
    return kb

def back_cancel_kb():
    return ReplyKeyboardMarkup(resize_keyboard=True, row_width=2).add("🔙 Step Back", "❌ Cancel to Menu")

# =======================================================================================
# 5. USER FLOW
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

    msg = f"👋 <b>Welcome to Cheap SMM Panel, {html.escape(m.from_user.first_name or 'User')}!</b> 🚀\n\n👇 <b>HOW TO GET STARTED:</b>\n1️⃣ Tap <b>'💳 Add Funds'</b>\n2️⃣ Tap <b>'🛒 Browse Services'</b>\n3️⃣ Paste your link and grow!"
    bot.send_message(m.chat.id, msg, parse_mode="HTML", reply_markup=main_kb(uid))

@bot.message_handler(func=lambda m: m.text == "❌ Cancel to Menu")
def h_cancel(m):
    user_states.pop(m.from_user.id, None)
    bot.send_message(m.chat.id, "🚫 <b>Cancelled!</b>\n🏠 <i>Back at the main menu.</i>", parse_mode="HTML", reply_markup=main_kb(m.from_user.id))

@bot.message_handler(func=lambda m: m.text == "🔙 Step Back")
def h_step_back(m):
    uid = m.from_user.id
    current_state = user_states.get(uid, {}).get("state")

    if current_state == "get_qty":
        user_states[uid]["state"] = "get_link"
        bot.send_message(m.chat.id, "🔙 <b>Went 1 step back!</b>\n🔗 <b>STEP 1: Send the Target Link</b>", parse_mode="HTML", reply_markup=back_cancel_kb())
    elif current_state == "get_link":
        user_states.pop(uid, None)
        h_browse(m)
    elif current_state == "fund_ss":
        user_states[uid]["state"] = "fund_amt"
        bot.send_message(m.chat.id, f"🔙 <b>Went 1 step back!</b>\n💸 <b>Enter deposit amount (₹):</b>", parse_mode="HTML", reply_markup=back_cancel_kb())
    else:
        user_states.pop(uid, None)
        bot.send_message(m.chat.id, "🏠 <b>Returned to Main Menu.</b>", parse_mode="HTML", reply_markup=main_kb(uid))

@bot.message_handler(func=lambda m: m.text == "💰 My Profile 👤")
def h_profile(m):
    u = execute_db("SELECT balance, total_spent, free_views_credits FROM users WHERE user_id=?", (m.from_user.id,), fetch=True)
    if not u: return
    ref_count = execute_db("SELECT COUNT(*) FROM referrals WHERE referrer_id=?", (m.from_user.id,), fetch=True)[0]
    msg = f"👤 <b>YOUR PROFILE</b>\n━━━━━━━━━━━━━━━━━━━\n🆔 <b>ID:</b> <code>{m.from_user.id}</code>\n💳 <b>Wallet:</b> ₹{u[0]:.2f}\n📈 <b>Spent:</b> ₹{u[1]:.2f}\n🎁 <b>Free Views:</b> {u[2]}\n👥 <b>Referrals:</b> {ref_count}"
    bot.send_message(m.chat.id, msg, parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text == "📦 Order History 📜")
def h_order_history(m):
    orders = execute_db("SELECT api_order_id, quantity, cost, status FROM orders WHERE user_id=? ORDER BY placed_time DESC LIMIT 5", (m.from_user.id,), fetch_all=True)
    if not orders: return bot.send_message(m.chat.id, "📦 No orders yet!", parse_mode="HTML")
    msg = "📦 <b>RECENT ORDERS:</b>\n━━━━━━━━━━━━━━━━━━━\n"
    for o in orders: msg += f"🧾 <b>ID:</b> <code>{o[0]}</code> | 🔢 {o[1]} | 💰 ₹{o[2]:.2f}\n📊 <b>Status:</b> <code>{o[3]}</code>\n───────────────────\n"
    bot.send_message(m.chat.id, msg, parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text == "🤝 Referral Program 👥")
def h_referral(m):
    u = execute_db("SELECT free_views_credits FROM users WHERE user_id=?", (m.from_user.id,), fetch=True)
    ref_count = execute_db("SELECT COUNT(*) FROM referrals WHERE referrer_id=?", (m.from_user.id,), fetch=True)[0]
    link = f"https://t.me/{bot.get_me().username}?start=ref_{m.from_user.id}"
    msg = f"🤝 <b>REFERRAL REWARDS</b>\n🔗 <b>Your Link:</b>\n<code>{link}</code>\n\n👥 <b>Friends Joined:</b> {ref_count}\n🎁 <b>Free Credits:</b> {u[0]}\n\n<i>Get 1,000 Free Views for every friend who joins!</i>"
    bot.send_message(m.chat.id, msg, parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text == "🎁 Claim Free 1K Views 🌟")
def h_claim_free(m):
    credits = execute_db("SELECT free_views_credits FROM users WHERE user_id=?", (m.from_user.id,), fetch=True)[0]
    if credits <= 0: return bot.send_message(m.chat.id, "❌ <b>You have 0 Free Credits!</b>", parse_mode="HTML")
    user_states[m.from_user.id] = {"state": "claim_free_link"}
    bot.send_message(m.chat.id, f"🎁 <b>You have {credits} free credit(s)!</b>\n\n🔗 <b>Send the public post link for 1,000 views:</b>", parse_mode="HTML", reply_markup=back_cancel_kb())

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get("state") == "claim_free_link")
def h_process_free_claim(m):
    uid = m.from_user.id
    if execute_db("SELECT free_views_credits FROM users WHERE user_id=?", (uid,), fetch=True)[0] <= 0: return
    bot.send_message(m.chat.id, "⏳ <i>Processing free views...</i>", parse_mode="HTML")
    api_res, prov_used = call_provider_api(FREE_VIEWS_PROVIDER, 'add', {'service': FREE_VIEWS_SERVICE_ID, 'link': m.text.strip(), 'quantity': 1000})
    if api_res and 'order' in api_res:
        execute_db("UPDATE users SET free_views_credits = free_views_credits - 1 WHERE user_id=?", (uid,))
        execute_db("INSERT INTO orders (user_id, provider, api_order_id, service_id, quantity, cost, profit, auto_refill) VALUES (?,?,?,?,?,?,?,0)", 
                   (uid, prov_used, api_res['order'], FREE_VIEWS_SERVICE_ID, 1000, 0.0, 0.0))
        bot.send_message(m.chat.id, f"✅ <b>SUCCESS! 1,000 FREE VIEWS ORDERED!</b>\n🧾 <b>ID:</b> <code>{api_res['order']}</code>", parse_mode="HTML", reply_markup=main_kb(uid))
    else: bot.send_message(m.chat.id, "❌ <b>Failed! Check your link.</b>", parse_mode="HTML", reply_markup=main_kb(uid))
    user_states.pop(uid, None)

# =======================================================================================
# 6. AI SUPPORT & TICKETS
# =======================================================================================
@bot.message_handler(func=lambda m: m.text == "📞 Support 🎫")
def h_support(m):
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("💬 Direct Chat", url=f"https://t.me/{SUPPORT_USERNAME.replace('@','')}"), InlineKeyboardButton("🎫 Open Ticket (AI Support)", callback_data="make_ticket"))
    bot.send_message(m.chat.id, "📞 <b>SUPPORT DESK</b>", parse_mode="HTML", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data == "make_ticket")
def h_ticket_init(c):
    bot.answer_callback_query(c.id)
    user_states[c.from_user.id] = {"state": "waiting_ticket_text"}
    bot.send_message(c.message.chat.id, "📝 <b>Type your message/issue below:</b>\n<i>Our AI assistant will try to help you instantly!</i>", parse_mode="HTML", reply_markup=back_cancel_kb())

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get("state") == "waiting_ticket_text")
def h_ticket_save(m):
    uid = m.from_user.id
    bot.send_message(m.chat.id, "⏳ <i>AI Support is typing...</i>", parse_mode="HTML")
    
    ai_reply = ask_gemini_support(m.text)
    
    if ai_reply:
        if "[ESCALATE]" in ai_reply:
            clean_reply = ai_reply.replace("[ESCALATE]", "").strip()
            if clean_reply: bot.send_message(m.chat.id, f"🤖 <b>AI:</b> {clean_reply}", parse_mode="HTML")
            
            tid = execute_db("INSERT INTO tickets (user_id, message) VALUES (?,?)", (uid, m.text), return_id=True)
            bot.send_message(m.chat.id, f"✅ <b>Ticket #{tid} created!</b> A human admin will review this shortly.", parse_mode="HTML", reply_markup=main_kb(uid))
            try: bot.send_message(ADMIN_ID, f"🚨 <b>ESCALATED TICKET #{tid}</b>\nFrom: <code>{uid}</code>\n💬 {m.text}", parse_mode="HTML")
            except: pass
            user_states.pop(uid, None)
        else:
            bot.send_message(m.chat.id, f"🤖 <b>AI Support:</b> {ai_reply}\n\n<i>Did this solve your issue? If not, simply type 'human' to open a ticket for the admin.</i>", parse_mode="HTML")
            user_states[uid] = {"state": "wait_human_ticket", "last_msg": m.text}
    else:
        # Fallback if API fails
        tid = execute_db("INSERT INTO tickets (user_id, message) VALUES (?,?)", (uid, m.text), return_id=True)
        bot.send_message(m.chat.id, f"✅ <b>Ticket #{tid} submitted!</b>", parse_mode="HTML", reply_markup=main_kb(uid))
        try: bot.send_message(ADMIN_ID, f"🚨 <b>NEW TICKET #{tid}</b>\nFrom: <code>{uid}</code>\n💬 {m.text}", parse_mode="HTML")
        except: pass
        user_states.pop(uid, None)

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get("state") == "wait_human_ticket")
def h_escalate_ticket(m):
    uid = m.from_user.id
    if m.text.lower() == 'human':
        last_msg = user_states[uid].get("last_msg", "User requested human help.")
        tid = execute_db("INSERT INTO tickets (user_id, message) VALUES (?,?)", (uid, last_msg), return_id=True)
        bot.send_message(m.chat.id, f"✅ <b>Ticket #{tid} submitted to admin!</b> They will reply soon.", parse_mode="HTML", reply_markup=main_kb(uid))
        try: bot.send_message(ADMIN_ID, f"🚨 <b>HUMAN TICKET #{tid}</b>\nFrom: <code>{uid}</code>\n💬 {last_msg}", parse_mode="HTML")
        except: pass
    else:
        bot.send_message(m.chat.id, "🏠 <b>Returned to Main Menu.</b>", parse_mode="HTML", reply_markup=main_kb(uid))
    user_states.pop(uid, None)

# =======================================================================================
# 7. ADD FUNDS FLOW
# =======================================================================================
@bot.message_handler(func=lambda m: m.text == "💳 Add Funds 💸")
def h_add_funds(m):
    if is_banned(m.from_user.id): return bot.send_message(m.chat.id, "🚫 You are banned.", parse_mode="HTML")
    user_states[m.from_user.id] = {"state": "fund_amt"}
    bot.send_message(m.chat.id, f"💸 <b>Enter deposit amount (₹):</b>\n(Minimum: <code>₹{MIN_DEPOSIT}</code>)", parse_mode="HTML", reply_markup=back_cancel_kb())

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get("state") == "fund_amt")
def h_fund_qr(m):
    try:
        amt = float(m.text.strip())
        if amt < MIN_DEPOSIT: return bot.send_message(m.chat.id, f"🚫 Minimum deposit is <code>₹{MIN_DEPOSIT}</code>", parse_mode="HTML", reply_markup=back_cancel_kb())
        user_states[m.from_user.id] = {"state": "fund_ss", "amt": amt}
        qr = f"https://api.qrserver.com/v1/create-qr-code/?size=400x400&data={urllib.parse.quote(f'upi://pay?pa={UPI_ID}&am={amt}&cu=INR')}"
        res = requests.get(qr, timeout=10)
        bot.send_photo(m.chat.id, BytesIO(res.content), caption=f"💳 <b>PAY EXACTLY ₹{amt}</b>\nUPI ID: <code>{UPI_ID}</code>\n\n📸 <b>Send screenshot here after paying!</b>", parse_mode="HTML", reply_markup=back_cancel_kb())
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

# =======================================================================================
# 8. ADMIN DASHBOARD & CONTROLS
# =======================================================================================
@bot.message_handler(func=lambda m: m.text == "📊 Admin: Stats" or m.text == "/stats")
def h_admin_stats(m):
    if m.from_user.id != ADMIN_ID: return
    
    profit_row = execute_db("SELECT SUM(profit) FROM orders WHERE date(placed_time) = date('now')", fetch=True)
    profit_today = profit_row[0] if profit_row and profit_row[0] else 0.0
    
    active_users = execute_db("SELECT COUNT(*) FROM users WHERE is_banned=0", fetch=True)[0]
    wallet_funds = execute_db("SELECT SUM(balance) FROM users", fetch=True)[0] or 0.0
    orders_today = execute_db("SELECT COUNT(*) FROM orders WHERE date(placed_time) = date('now')", fetch=True)[0]
    
    msg = (
        f"📊 <b>ADMIN ANALYTICS DASHBOARD</b> 📊\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"💵 <b>Total Profit Today:</b> <code>₹{profit_today:.2f}</code>\n"
        f"👥 <b>Total Active Users:</b> <code>{active_users}</code>\n"
        f"💰 <b>Funds Sitting in Wallets:</b> <code>₹{wallet_funds:.2f}</code>\n"
        f"📦 <b>Orders Placed Today:</b> <code>{orders_today}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━"
    )
    bot.send_message(ADMIN_ID, msg, parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text == "👥 Admin: Manage Users" and m.from_user.id == ADMIN_ID)
def h_admin_manage_users(m):
    user_states[ADMIN_ID] = {"state": "wait_manage_uid"}
    bot.send_message(ADMIN_ID, "🔍 Enter the <b>User ID</b>:", parse_mode="HTML", reply_markup=back_cancel_kb())

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get("state") == "wait_manage_uid" and m.from_user.id == ADMIN_ID)
def h_admin_manage_uid(m):
    try: target_uid = int(m.text.strip())
    except: return bot.send_message(ADMIN_ID, "❌ User ID must be numbers.", reply_markup=back_cancel_kb())
    user = execute_db("SELECT username, first_name, balance, total_spent, is_banned FROM users WHERE user_id=?", (target_uid,), fetch=True)
    if not user: return bot.send_message(ADMIN_ID, "❌ User not found.")
    
    status = "🔴 BANNED" if user[4] else "🟢 ACTIVE"
    msg = f"👤 <b>USER</b> <code>{target_uid}</code>\n💰 <b>Wallet:</b> ₹{user[2]:.2f}\n🛡️ <b>Status:</b> {status}\n\n👇 <i>Select action:</i>"
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(InlineKeyboardButton("➕ Add Balance", callback_data=f"adm_add_{target_uid}"), InlineKeyboardButton("➖ Deduct Balance", callback_data=f"adm_sub_{target_uid}"))
    if user[4]: kb.add(InlineKeyboardButton("✅ Unban User", callback_data=f"adm_unban_{target_uid}"))
    else: kb.add(InlineKeyboardButton("🚫 Ban User", callback_data=f"adm_ban_{target_uid}"))
    
    user_states.pop(ADMIN_ID, None)
    bot.send_message(ADMIN_ID, msg, parse_mode="HTML", reply_markup=main_kb(ADMIN_ID))
    bot.send_message(ADMIN_ID, "⚙️ <b>Actions:</b>", parse_mode="HTML", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("adm_"))
def h_admin_user_actions(c):
    if c.from_user.id != ADMIN_ID: return
    bot.answer_callback_query(c.id)
    parts = c.data.split("_")
    action, target_uid = parts[1], int(parts[2])
    
    if action == "add":
        user_states[ADMIN_ID] = {"state": "wait_adm_add", "uid": target_uid}
        bot.send_message(ADMIN_ID, f"➕ Enter amount to <b>ADD</b> to User <code>{target_uid}</code>:", parse_mode="HTML", reply_markup=back_cancel_kb())
    elif action == "sub":
        user_states[ADMIN_ID] = {"state": "wait_adm_sub", "uid": target_uid}
        bot.send_message(ADMIN_ID, f"➖ Enter amount to <b>DEDUCT</b> from User <code>{target_uid}</code>:", parse_mode="HTML", reply_markup=back_cancel_kb())
    elif action == "ban":
        execute_db("UPDATE users SET is_banned=1 WHERE user_id=?", (target_uid,))
        bot.edit_message_text(f"🚫 <b>User {target_uid} BANNED.</b>", c.message.chat.id, c.message.message_id, parse_mode="HTML")
    elif action == "unban":
        execute_db("UPDATE users SET is_banned=0 WHERE user_id=?", (target_uid,))
        bot.edit_message_text(f"✅ <b>User {target_uid} UNBANNED.</b>", c.message.chat.id, c.message.message_id, parse_mode="HTML")

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get("state") in ["wait_adm_add", "wait_adm_sub"] and m.from_user.id == ADMIN_ID)
def h_admin_bal_adjust(m):
    state_data = user_states[ADMIN_ID]
    action, target_uid = state_data["state"], state_data["uid"]
    try: amt = float(m.text.strip())
    except: return bot.send_message(ADMIN_ID, "❌ Numbers only.", reply_markup=back_cancel_kb())
    
    if action == "wait_adm_add":
        execute_db("UPDATE users SET balance=balance+? WHERE user_id=?", (amt, target_uid))
        bot.send_message(ADMIN_ID, f"✅ <b>Added ₹{amt:.2f}</b> to <code>{target_uid}</code>.", parse_mode="HTML", reply_markup=main_kb(ADMIN_ID))
        try: bot.send_message(target_uid, f"🎁 ₹{amt:.2f} added to your balance!", parse_mode="HTML")
        except: pass
    else:
        user = execute_db("SELECT balance FROM users WHERE user_id=?", (target_uid,), fetch=True)
        new_bal = max(0.0, user[0] - amt)
        execute_db("UPDATE users SET balance=? WHERE user_id=?", (new_bal, target_uid))
        bot.send_message(ADMIN_ID, f"✅ <b>Deducted ₹{amt:.2f}</b> from <code>{target_uid}</code>.", parse_mode="HTML", reply_markup=main_kb(ADMIN_ID))
    user_states.pop(ADMIN_ID, None)

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

@bot.message_handler(func=lambda m: m.text == "📈 Admin: Margin" and m.from_user.id == ADMIN_ID)
def h_admin_margin(m):
    user_states[ADMIN_ID] = {"state": "wait_margin"}
    bot.send_message(ADMIN_ID, "📈 <b>Enter profit % (e.g. 50):</b>", parse_mode="HTML", reply_markup=back_cancel_kb())

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get("state") == "wait_margin" and m.from_user.id == ADMIN_ID)
def h_process_margin(m):
    try:
        pct = float(m.text.strip())
        multiplier = 1.0 + (pct / 100.0)
        execute_db("UPDATE settings SET value=? WHERE key='global_margin'", (str(multiplier),))
        execute_db("UPDATE managed_services SET margin=?", (multiplier,))
        bot.send_message(ADMIN_ID, f"✅ Margin updated to {pct}% markup.", parse_mode="HTML", reply_markup=main_kb(ADMIN_ID))
    except: bot.send_message(ADMIN_ID, "❌ Numbers only.")
    user_states.pop(ADMIN_ID, None)

@bot.message_handler(func=lambda m: m.text == "📢 Admin: Broadcast" and m.from_user.id == ADMIN_ID)
def h_admin_broadcast(m):
    user_states[ADMIN_ID] = {"state": "wait_broadcast"}
    bot.send_message(ADMIN_ID, "📢 <b>Enter broadcast message:</b>", parse_mode="HTML", reply_markup=back_cancel_kb())

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get("state") == "wait_broadcast" and m.from_user.id == ADMIN_ID)
def h_process_broadcast(m):
    users = execute_db("SELECT user_id FROM users WHERE is_banned=0", fetch_all=True)
    sent = 0
    for u in users:
        try: bot.send_message(u[0], f"📢 <b>ANNOUNCEMENT:</b>\n\n{m.text}", parse_mode="HTML"); sent += 1
        except: pass
    bot.send_message(ADMIN_ID, f"✅ Broadcast sent to {sent} users.", parse_mode="HTML", reply_markup=main_kb(ADMIN_ID))
    user_states.pop(ADMIN_ID, None)

@bot.message_handler(func=lambda m: m.text == "🎫 Admin: Tickets" and m.from_user.id == ADMIN_ID)
def h_admin_view_tickets(m):
    tickets = execute_db("SELECT ticket_id, user_id, message FROM tickets WHERE status='OPEN' LIMIT 5", fetch_all=True)
    if not tickets: return bot.send_message(ADMIN_ID, "✅ No open tickets.")
    for t in tickets: bot.send_message(ADMIN_ID, f"🎫 <b>Ticket #{t[0]}</b>\nUser: <code>{t[1]}</code>\n💬 {t[2]}", parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text == "💾 Admin: Backup DB" and m.from_user.id == ADMIN_ID)
def handle_admin_backup(m):
    uid = m.from_user.id
    bot.send_message(uid, "⏳ <i>Generating snapshot...</i>", parse_mode="HTML")
    backup_file = f"backup_{int(time.time())}.db"
    try:
        with db_lock:
            with sqlite3.connect('panel_v17.db') as src, sqlite3.connect(backup_file) as dst: src.backup(dst)
        with open(backup_file, 'rb') as doc:
            bot.send_document(uid, doc, caption="💾 <b>Database Backup</b> ✅", parse_mode="HTML")
    except Exception as e: bot.send_message(uid, f"❌ Backup Failed: <code>{e}</code>", parse_mode="HTML")
    finally:
        if os.path.exists(backup_file): os.remove(backup_file)

@bot.message_handler(func=lambda m: m.text == "🔄 Admin: Restore DB" and m.from_user.id == ADMIN_ID)
def handle_admin_restore_prompt(m):
    user_states[ADMIN_ID] = {"state": "wait_for_db_upload"}
    bot.send_message(ADMIN_ID, "⚠️ Upload <code>.db</code> file below:", parse_mode="HTML", reply_markup=back_cancel_kb())

@bot.message_handler(content_types=['document'])
def handle_document_upload(m):
    uid = m.from_user.id
    if uid == ADMIN_ID and user_states.get(uid, {}).get("state") == "wait_for_db_upload":
        if not m.document.file_name.endswith('.db'): return bot.send_message(uid, "❌ .db file only.", reply_markup=main_kb(uid))
        temp_file = f"restore_{int(time.time())}.db"
        try:
            bot.send_message(uid, "⏳ <i>Restoring...</i>", parse_mode="HTML")
            downloaded = bot.download_file(bot.get_file(m.document.file_id).file_path)
            with open(temp_file, 'wb') as f: f.write(downloaded)
            with db_lock:
                with sqlite3.connect(temp_file) as src, sqlite3.connect('panel_v17.db') as dst: src.backup(dst)
            bot.send_message(uid, "✅ <b>RESTORED SUCCESSFULLY!</b>", parse_mode="HTML", reply_markup=main_kb(uid))
        except Exception as e: bot.send_message(uid, f"❌ Failed: {e}", reply_markup=main_kb(uid))
        finally:
            user_states.pop(uid, None)
            if os.path.exists(temp_file): os.remove(temp_file)

# =======================================================================================
# 9. PLATFORM BROWSING & BUYING
# =======================================================================================
@bot.message_handler(func=lambda m: m.text == "🛒 Browse Services 🚀")
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
    if p_idx >= len(platforms): return
    platform_name = platforms[p_idx][0]
    cats = execute_db("SELECT DISTINCT category FROM managed_services WHERE platform=? AND disabled=0", (platform_name,), fetch_all=True)
    if c_idx >= len(cats): return
    category_name = cats[c_idx][0]
    svcs = execute_db("SELECT service_id, name, rate, margin FROM managed_services WHERE platform=? AND category=? AND disabled=0", (platform_name, category_name), fetch_all=True)
    kb = InlineKeyboardMarkup(row_width=1)
    for s in svcs: kb.add(InlineKeyboardButton(f"⭐ {s[1]} - ₹{(s[2]*s[3]):.2f}/1K", callback_data=f"card_{s[0]}_{p_idx}_{c_idx}"))
    kb.add(InlineKeyboardButton(f"🔙 Back to {platform_name}", callback_data=f"plt_{p_idx}"))
    bot.edit_message_text(f"📂 <b>{html.escape(category_name.upper())}</b> 📊\n━━━━━━━━━━━━━━━━━━━\n👇 <i>Tap a service:</i>", c.message.chat.id, c.message.message_id, parse_mode="HTML", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("card_"))
def h_card_view(c):
    bot.answer_callback_query(c.id)
    _, sid, p_idx, c_idx = c.data.split("_")
    svc = execute_db("SELECT service_id, platform, name, rate, min_qty, max_qty, avg_time, margin FROM managed_services WHERE service_id=?", (int(sid),), fetch=True)
    if not svc: return
    final_price = svc[3] * svc[7]
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("🚀 Order This Service Now", callback_data=f"buy_{svc[0]}"))
    kb.add(InlineKeyboardButton("🔙 Back to Services", callback_data=f"cat_{p_idx}_{c_idx}"))
    msg = (f"🏷️ <b>SERVICE DETAILS</b> 📋\n━━━━━━━━━━━━━━━━━━━\n📌 <b>Service:</b> {html.escape(svc[2])}\n"
           f"💰 <b>Price:</b> <code>₹{final_price:.2f}</code> per 1,000\n📊 <b>Limits:</b> Min <code>{svc[4]:,}</code> — Max <code>{svc[5]:,}</code>\n"
           f"⏱️ <b>Avg Speed:</b> <code>{svc[6]}</code>\n♻️ <b>Auto-Refill:</b> <code>Active</code> 🛡️")
    bot.edit_message_text(msg, c.message.chat.id, c.message.message_id, parse_mode="HTML", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("buy_"))
def h_buy_service(c):
    bot.answer_callback_query(c.id)
    if is_banned(c.from_user.id): return bot.send_message(c.message.chat.id, "🚫 You are banned.")
    sid = int(c.data.split("_")[1])
    user_states[c.from_user.id] = {"state": "get_link", "sid": sid}
    bot.send_message(c.message.chat.id, "🔗 <b>STEP 1: Send the Target Link</b> 📌\n<i>Paste the public URL:</i>", parse_mode="HTML", reply_markup=back_cancel_kb())

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get("state") == "get_link")
def h_link_input(m):
    user_states[m.from_user.id].update({"state": "get_qty", "link": m.text.strip()})
    bot.send_message(m.chat.id, "✅ <b>Link Received!</b> 🔗\n\n🔢 <b>STEP 2: Enter Quantity</b> 📊\n<i>Type numbers only:</i>", parse_mode="HTML", reply_markup=back_cancel_kb())

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get("state") == "get_qty")
def h_qty_input(m):
    uid = m.from_user.id
    state = user_states[uid]
    try: qty = int(m.text.strip())
    except: return bot.send_message(m.chat.id, "❌ Numbers only.", reply_markup=back_cancel_kb())

    svc = execute_db("SELECT provider, provider_service_id, rate, margin, min_qty, max_qty FROM managed_services WHERE service_id=?", (state["sid"],), fetch=True)
    if not svc: return
    if qty < svc[4] or qty > svc[5]:
        return bot.send_message(m.chat.id, f"🚫 <b>Out of Range!</b> Min: <code>{svc[4]}</code> | Max: <code>{svc[5]}</code>", parse_mode="HTML", reply_markup=back_cancel_kb())

    cost = (qty / 1000.0) * (svc[2] * svc[3])
    base_cost = (qty / 1000.0) * svc[2]
    profit = cost - base_cost
    
    u_bal = execute_db("SELECT balance FROM users WHERE user_id=?", (uid,), fetch=True)[0]
    
    if u_bal < cost: 
        user_states.pop(uid, None)
        return bot.send_message(m.chat.id, f"❌ <b>INSUFFICIENT BALANCE!</b>\nNeed: ₹{cost:.2f} | Wallet: ₹{u_bal:.2f}", parse_mode="HTML", reply_markup=main_kb(uid))

    bot.send_message(m.chat.id, "⏳ <i>Processing order...</i>", parse_mode="HTML")
    api_res, prov_used = call_provider_api(svc[0], 'add', {'service': svc[1], 'link': state['link'], 'quantity': qty})
    
    if api_res and 'order' in api_res:
        execute_db("UPDATE users SET balance=balance-?, total_spent=total_spent+? WHERE user_id=?", (cost, cost, uid))
        execute_db("INSERT INTO orders (user_id, provider, api_order_id, service_id, quantity, cost, profit, auto_refill) VALUES (?,?,?,?,?,?,?,1)",
                   (uid, prov_used, api_res['order'], state["sid"], qty, cost, profit))
        bot.send_message(m.chat.id, f"✅ <b>ORDER DISPATCHED!</b> 🎉\n🧾 <b>ID:</b> <code>{api_res['order']}</code>\n💰 <b>Cost:</b> ₹{cost:.2f}", parse_mode="HTML", reply_markup=main_kb(uid))
    else: bot.send_message(m.chat.id, "❌ <b>Provider Error!</b>", parse_mode="HTML", reply_markup=main_kb(uid))
    user_states.pop(uid, None)

# =======================================================================================
# 10. BACKGROUND TASKS & LIVE ORDER NOTIFICATIONS
# =======================================================================================
def auto_refill_and_status_monitor():
    while True:
        try:
            orders = execute_db("SELECT db_id, provider, api_order_id, status, user_id, quantity, service_id FROM orders WHERE status IN ('pending', 'In progress', 'Processing', 'Pending')", fetch_all=True)
            if orders:
                for o in orders:
                    res, _ = call_provider_api(o[1], 'status', {'order': o[2]})
                    if res and 'status' in res:
                        new_status = res['status'].capitalize()
                        if new_status != o[3]:
                            execute_db("UPDATE orders SET status=? WHERE db_id=?", (new_status, o[0]))
                            
                            # Live DM Notification for Users
                            if new_status in ['Completed', 'Partial', 'Canceled']:
                                svc = execute_db("SELECT name FROM managed_services WHERE service_id=?", (o[6],), fetch=True)
                                svc_name = svc[0] if svc else "Service"
                                emoji = "✅" if new_status == "Completed" else "⚠️"
                                msg = (
                                    f"{emoji} <b>Hey! Order Update!</b> 🎉\n\n"
                                    f"Your order of <b>{o[5]:,} {html.escape(svc_name)}</b> is now <b>{new_status.upper()}</b>!"
                                )
                                try: bot.send_message(o[4], msg, parse_mode="HTML")
                                except: pass
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
