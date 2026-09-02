"""
=========================================================================================
🔥 SMM PANEL BOT - ENTERPRISE V16 ULTIMATE 🔥
(INTERACTIVE ADMIN DASHBOARD + ADD/DEDUCT BAL + BAN SYSTEM + PLATFORM CATEGORIES)
=========================================================================================
"""

import telebot, requests, sqlite3, logging, time, os, urllib.parse, threading, html
from io import BytesIO
from flask import Flask
from telebot.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton

# =======================================================================================
# 1. CONFIGURATION & SERVER SETUP
# =======================================================================================
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

BOT_TOKEN = os.environ.get('BOT_TOKEN', '8228287584:AAESLgZbAzrdLqODmc7_dWIy6oMKc00LwVg')
bot = telebot.TeleBot(BOT_TOKEN, threaded=True, num_threads=10)

PROVIDERS = {
    "provider_primary": {
        "url": os.environ.get("API_URL_1", "https://iggrowbot.com/api/v2"),
        "key": os.environ.get("API_KEY_1", "c71040b041afb45b2bd008bfde82fa08")
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
def home(): 
    return "🔥 SMM V16 ENTERPRISE ONLINE & ACTIVE 🔥"

# =======================================================================================
# 2. DATABASE ENGINE
# =======================================================================================
def execute_db(query, params=(), fetch=False, fetch_all=False, return_id=False):
    with db_lock:
        try:
            with sqlite3.connect('panel_v16.db', check_same_thread=False, timeout=20) as conn:
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
            logging.error(f"Database Error [{query}]: {e}")
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
            service_id INTEGER, quantity INTEGER, cost REAL, status TEXT DEFAULT 'pending',
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

def is_banned(uid):
    u = execute_db("SELECT is_banned FROM users WHERE user_id=?", (uid,), fetch=True)
    return u and u[0] == 1

# =======================================================================================
# 3. API & UTILITIES
# =======================================================================================
def call_provider_api(provider_name, action, extra=None):
    prov = PROVIDERS.get(provider_name, PROVIDERS["provider_primary"])
    payload = {'key': prov['key'], 'action': action}
    if extra: payload.update(extra)
    try:
        res = requests.post(prov['url'], data=payload, timeout=15)
        return res.json(), provider_name
    except Exception as e:
        logging.error(f"API Call Failed: {e}")
        return None, provider_name

def detect_platform(category_str, name_str):
    combined = f"{category_str} {name_str}".lower()
    if any(k in combined for k in ['instagram', 'ig ', 'reels', 'insta']): return "📸 Instagram"
    elif any(k in combined for k in ['telegram', 'tg ', 'tele ']): return "✈️ Telegram"
    elif any(k in combined for k in ['youtube', 'yt ', 'shorts']): return "🔴 YouTube"
    elif any(k in combined for k in ['facebook', 'fb ']): return "📘 Facebook"
    elif any(k in combined for k in ['tiktok', 'tik tok']): return "🎵 TikTok"
    elif any(k in combined for k in ['twitter', 'x ', 'tweet']): return "🐦 Twitter / X"
    return "⚡ General Boost"

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
        kb.add("🧠 Admin: Smart Sync", "📈 Admin: Margin")
        kb.add("👥 Admin: Manage Users", "🎫 Admin: Tickets")
        kb.add("📢 Admin: Broadcast", "💾 Admin: Backup DB")
        kb.add("🔄 Admin: Restore DB")
    return kb

def back_cancel_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add("🔙 Step Back", "❌ Cancel to Menu")
    return kb

# =======================================================================================
# 5. USER FLOW (START & NAVIGATION)
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
                potential = int(args[1].replace('ref_', ''))
                if potential != uid: referrer_id = potential
            except: pass
        execute_db("INSERT INTO users (user_id, username, first_name, referrer_id, referral_code) VALUES (?,?,?,?,?)",
                   (uid, m.from_user.username, m.from_user.first_name, referrer_id, f"REF{uid}"))
        if referrer_id:
            execute_db("INSERT OR IGNORE INTO referrals (referrer_id, referred_id) VALUES (?,?)", (referrer_id, uid))
            execute_db("UPDATE users SET free_views_credits = free_views_credits + 1 WHERE user_id=?", (referrer_id,))
            try: bot.send_message(referrer_id, "🎊 <b>A friend joined!</b>\n🎁 <b>You received +1 Free 1K Views Credit!</b>", parse_mode="HTML")
            except: pass

    if is_banned(uid):
        return bot.send_message(m.chat.id, "🚫 <b>YOUR ACCOUNT HAS BEEN BANNED.</b>\nContact support if you think this is a mistake.", parse_mode="HTML")

    safe_name = html.escape(m.from_user.first_name or "User")
    msg = (
        f"👋 <b>Welcome to Cheap SMM Panel, {safe_name}!</b> 🚀🔥\n\n"
        f"Boost your social media growth instantly across all major platforms with lightning fast speeds! 📈⚡️\n\n"
        f"👇 <b>HOW TO GET STARTED:</b>\n"
        f"1️⃣ <b>Add Balance:</b> Tap <b>'💳 Add Funds'</b> to load your wallet.\n"
        f"2️⃣ <b>Browse Services:</b> Tap <b>'🛒 Browse Services'</b> to choose your platform.\n"
        f"3️⃣ <b>Place Order:</b> Paste your link and grow!\n\n"
        f"<i>Select any button below to start:</i> 👇✨"
    )
    bot.send_message(m.chat.id, msg, parse_mode="HTML", reply_markup=main_kb(uid))

@bot.message_handler(func=lambda m: m.text == "❌ Cancel to Menu")
def h_cancel(m):
    user_states.pop(m.from_user.id, None)
    bot.send_message(m.chat.id, "🚫 <b>Action Cancelled!</b>\n🏠 <i>You are back at the main menu.</i>", parse_mode="HTML", reply_markup=main_kb(m.from_user.id))

@bot.message_handler(func=lambda m: m.text == "🔙 Step Back")
def h_step_back(m):
    uid = m.from_user.id
    state_data = user_states.get(uid, {})
    current_state = state_data.get("state")

    if current_state == "get_qty":
        user_states[uid]["state"] = "get_link"
        bot.send_message(m.chat.id, "🔙 <b>Went 1 step back!</b>\n🔗 <b>STEP 1: Send the Target Link</b> 📌", parse_mode="HTML", reply_markup=back_cancel_kb())
    elif current_state == "get_link":
        user_states.pop(uid, None)
        h_browse(m)
    elif current_state == "fund_ss":
        user_states[uid]["state"] = "fund_amt"
        bot.send_message(m.chat.id, f"🔙 <b>Went 1 step back!</b>\n💸 <b>Enter deposit amount (₹):</b>", parse_mode="HTML", reply_markup=back_cancel_kb())
    elif current_state in ["fund_amt", "wait_manage_uid", "wait_adm_add", "wait_adm_sub"]:
        user_states.pop(uid, None)
        bot.send_message(m.chat.id, "🏠 <b>Returned to Main Menu:</b>", parse_mode="HTML", reply_markup=main_kb(uid))
    else:
        user_states.pop(uid, None)
        bot.send_message(m.chat.id, "🏠 <b>Main Menu:</b>", parse_mode="HTML", reply_markup=main_kb(uid))

# =======================================================================================
# 6. ADMIN MANAGER (MANUAL ADD / DEDUCT / BAN)
# =======================================================================================
@bot.message_handler(func=lambda m: m.text == "👥 Admin: Manage Users" and m.from_user.id == ADMIN_ID)
def h_admin_manage_users(m):
    user_states[ADMIN_ID] = {"state": "wait_manage_uid"}
    bot.send_message(ADMIN_ID, "👥 <b>USER DASHBOARD</b>\n\n🔍 Enter the <b>User ID</b> you want to inspect or modify:", parse_mode="HTML", reply_markup=back_cancel_kb())

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get("state") == "wait_manage_uid" and m.from_user.id == ADMIN_ID)
def h_admin_manage_uid(m):
    try: target_uid = int(m.text.strip())
    except: return bot.send_message(ADMIN_ID, "❌ User ID must be numbers only.", reply_markup=back_cancel_kb())
    
    user = execute_db("SELECT username, first_name, balance, total_spent, is_banned FROM users WHERE user_id=?", (target_uid,), fetch=True)
    if not user: return bot.send_message(ADMIN_ID, "❌ User not found in database.", reply_markup=back_cancel_kb())
    
    status = "🔴 BANNED" if user[4] else "🟢 ACTIVE"
    msg = (
        f"👤 <b>USER PROFILE CARDS</b>\n━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 <b>ID:</b> <code>{target_uid}</code>\n"
        f"👤 <b>Name:</b> {html.escape(user[1] or 'N/A')} (@{user[0] or 'N/A'})\n"
        f"💰 <b>Wallet:</b> ₹{user[2]:.2f}\n"
        f"📈 <b>Spent:</b> ₹{user[3]:.2f}\n"
        f"🛡️ <b>Status:</b> {status}\n━━━━━━━━━━━━━━━━━━━\n"
        f"👇 <i>Select an action below:</i>"
    )
    
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("➕ Add Balance", callback_data=f"adm_add_{target_uid}"),
        InlineKeyboardButton("➖ Deduct Balance", callback_data=f"adm_sub_{target_uid}")
    )
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
        bot.edit_message_text(f"🚫 <b>User {target_uid} is now BANNED.</b>", c.message.chat.id, c.message.message_id, parse_mode="HTML")
    elif action == "unban":
        execute_db("UPDATE users SET is_banned=0 WHERE user_id=?", (target_uid,))
        bot.edit_message_text(f"✅ <b>User {target_uid} is now UNBANNED.</b>", c.message.chat.id, c.message.message_id, parse_mode="HTML")

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get("state") in ["wait_adm_add", "wait_adm_sub"] and m.from_user.id == ADMIN_ID)
def h_admin_bal_adjust(m):
    state_data = user_states[ADMIN_ID]
    action, target_uid = state_data["state"], state_data["uid"]
    
    try: amt = float(m.text.strip())
    except: return bot.send_message(ADMIN_ID, "❌ Amount must be numbers only.", reply_markup=back_cancel_kb())
    
    if action == "wait_adm_add":
        execute_db("UPDATE users SET balance=balance+? WHERE user_id=?", (amt, target_uid))
        execute_db("INSERT INTO transactions (user_id, amount, status) VALUES (?, ?, 'ADMIN_ADD')", (target_uid, amt))
        bot.send_message(ADMIN_ID, f"✅ <b>Added ₹{amt:.2f}</b> to user <code>{target_uid}</code>.", parse_mode="HTML", reply_markup=main_kb(ADMIN_ID))
        try: bot.send_message(target_uid, f"🎁 <b>System Wallet Update:</b>\n₹{amt:.2f} has been added to your balance!", parse_mode="HTML")
        except: pass
    else:
        user = execute_db("SELECT balance FROM users WHERE user_id=?", (target_uid,), fetch=True)
        new_bal = max(0.0, user[0] - amt)
        execute_db("UPDATE users SET balance=? WHERE user_id=?", (new_bal, target_uid))
        execute_db("INSERT INTO transactions (user_id, amount, status) VALUES (?, ?, 'ADMIN_DEDUCT')", (target_uid, -amt))
        bot.send_message(ADMIN_ID, f"✅ <b>Deducted ₹{amt:.2f}</b> from user <code>{target_uid}</code>.\nNew Balance: ₹{new_bal:.2f}", parse_mode="HTML", reply_markup=main_kb(ADMIN_ID))
        try: bot.send_message(target_uid, f"⚠️ <b>System Wallet Update:</b>\n₹{amt:.2f} has been deducted from your balance.", parse_mode="HTML")
        except: pass
    user_states.pop(ADMIN_ID, None)

# =======================================================================================
# 7. PLATFORM BROWSING & BUYING
# =======================================================================================
@bot.message_handler(func=lambda m: m.text == "🛒 Browse Services 🚀")
def h_browse(m):
    if is_banned(m.from_user.id): return bot.send_message(m.chat.id, "🚫 You are banned from using this bot.")
    user_states.pop(m.from_user.id, None)
    platforms = execute_db("SELECT DISTINCT platform FROM managed_services WHERE disabled=0 ORDER BY platform ASC", fetch_all=True)
    if not platforms: return bot.send_message(m.chat.id, "⚠️ No services loaded! Admin needs to run Smart Sync.")
    
    kb = InlineKeyboardMarkup(row_width=2)
    for idx, p in enumerate(platforms): kb.add(InlineKeyboardButton(f"{p[0]}", callback_data=f"plt_{idx}"))
    bot.send_message(m.chat.id, "🛒 <b>CHOOSE YOUR PLATFORM:</b> 🌐✨\n━━━━━━━━━━━━━━━━━━━\n👇 <i>Select which platform you want to grow:</i>", parse_mode="HTML", reply_markup=kb)

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
    bot.edit_message_text("🛒 <b>CHOOSE YOUR PLATFORM:</b> 🌐✨\n━━━━━━━━━━━━━━━━━━━\n👇 <i>Select which platform you want to grow:</i>", c.message.chat.id, c.message.message_id, parse_mode="HTML", reply_markup=kb)

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
    bot.edit_message_text(f"📂 <b>{html.escape(category_name.upper())}</b> 📊\n━━━━━━━━━━━━━━━━━━━\n👇 <i>Tap a service to view details:</i>", c.message.chat.id, c.message.message_id, parse_mode="HTML", reply_markup=kb)

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
    if is_banned(c.from_user.id): return bot.send_message(c.message.chat.id, "🚫 You are banned from placing orders.")
    sid = int(c.data.split("_")[1])
    user_states[c.from_user.id] = {"state": "get_link", "sid": sid}
    bot.send_message(c.message.chat.id, "🔗 <b>STEP 1: Send the Target Link</b> 📌\n<i>Paste the public profile/post URL:</i>", parse_mode="HTML", reply_markup=back_cancel_kb())

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get("state") == "get_link")
def h_link_input(m):
    user_states[m.from_user.id].update({"state": "get_qty", "link": m.text.strip()})
    bot.send_message(m.chat.id, "✅ <b>Link Received!</b> 🔗\n\n🔢 <b>STEP 2: Enter Quantity</b> 📊\n<i>Type numbers only (e.g. 1000):</i>", parse_mode="HTML", reply_markup=back_cancel_kb())

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get("state") == "get_qty")
def h_qty_input(m):
    uid = m.from_user.id
    state = user_states[uid]
    try: qty = int(m.text.strip())
    except: return bot.send_message(m.chat.id, "❌ Numbers only.", reply_markup=back_cancel_kb())

    svc = execute_db("SELECT provider, provider_service_id, rate, margin, min_qty, max_qty FROM managed_services WHERE service_id=?", (state["sid"],), fetch=True)
    if not svc: return
    
    if qty < svc[4] or qty > svc[5]:
        return bot.send_message(m.chat.id, f"🚫 <b>Quantity Out of Range!</b>\nMin: <code>{svc[4]}</code> | Max: <code>{svc[5]}</code>", parse_mode="HTML", reply_markup=back_cancel_kb())

    cost = (qty / 1000.0) * (svc[2] * svc[3])
    u_bal = execute_db("SELECT balance FROM users WHERE user_id=?", (uid,), fetch=True)[0]
    
    if u_bal < cost: 
        user_states.pop(uid, None)
        return bot.send_message(m.chat.id, f"❌ <b>INSUFFICIENT BALANCE!</b>\nNeed: ₹{cost:.2f} | Wallet: ₹{u_bal:.2f}", parse_mode="HTML", reply_markup=main_kb(uid))

    bot.send_message(m.chat.id, "⏳ <i>Processing order...</i>", parse_mode="HTML")
    api_res, prov_used = call_provider_api(svc[0], 'add', {'service': svc[1], 'link': state['link'], 'quantity': qty})
    
    if api_res and 'order' in api_res:
        execute_db("UPDATE users SET balance=balance-?, total_spent=total_spent+? WHERE user_id=?", (cost, cost, uid))
        execute_db("INSERT INTO orders (user_id, provider, api_order_id, service_id, quantity, cost, auto_refill) VALUES (?,?,?,?,?,?,1)",
                   (uid, prov_used, api_res['order'], state["sid"], qty, cost))
        bot.send_message(m.chat.id, f"✅ <b>ORDER DISPATCHED!</b> 🎉\n🧾 <b>ID:</b> <code>{api_res['order']}</code>\n💰 <b>Cost:</b> ₹{cost:.2f}", parse_mode="HTML", reply_markup=main_kb(uid))
    else: bot.send_message(m.chat.id, "❌ <b>Provider Error!</b> Please try a different service.", parse_mode="HTML", reply_markup=main_kb(uid))
    user_states.pop(uid, None)

# =======================================================================================
# 8. BACKGROUND TASKS
# =======================================================================================
def auto_refill_and_status_monitor():
    while True:
        try:
            orders = execute_db("SELECT db_id, provider, api_order_id FROM orders WHERE status IN ('pending', 'In progress', 'Processing')", fetch_all=True)
            if orders:
                for o in orders:
                    res, _ = call_provider_api(o[1], 'status', {'order': o[2]})
                    if res and 'status' in res: execute_db("UPDATE orders SET status=? WHERE db_id=?", (res['status'].capitalize(), o[0]))
        except: pass
        time.sleep(300)

if __name__ == '__main__':
    init_database()
    try: bot.remove_webhook(); time.sleep(1)
    except: pass
    threading.Thread(target=lambda: bot.infinity_polling(skip_pending=True, timeout=60), daemon=True).start()
    threading.Thread(target=auto_refill_and_status_monitor, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
