"""
=========================================================================================
🔥 SMM PANEL BOT - ENTERPRISE V15 ULTIMATE 🔥
(PLATFORM CATEGORIZATION + SERVICE CARDS + 1-STEP BACK SYSTEM + ALL ADMIN CONTROLS)
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

BOT_TOKEN = os.environ.get('BOT_TOKEN', '8228287584:AAGWsCeTG5MgMwpshno7elpXbkQXvToDz1Y')
bot = telebot.TeleBot(BOT_TOKEN, threaded=True, num_threads=10)

PROVIDERS = {
    "provider_primary": {
        "url": os.environ.get("API_URL_1", "https://iggrowbot.com/api/v2"),
        "key": os.environ.get("API_KEY_1", "c1ff6a119106be59dab2829144bc413a")
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
    return "🔥 SMM V15 ENTERPRISE ONLINE & ACTIVE 🔥"

# =======================================================================================
# 2. DATABASE ENGINE (THREAD-SAFE)
# =======================================================================================
def execute_db(query, params=(), fetch=False, fetch_all=False, return_id=False):
    with db_lock:
        try:
            with sqlite3.connect('panel_v15.db', check_same_thread=False, timeout=20) as conn:
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

# =======================================================================================
# 3. API & HELPER UTILITIES
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
    if any(k in combined for k in ['instagram', 'ig ', 'reels', 'insta']):
        return "📸 Instagram"
    elif any(k in combined for k in ['telegram', 'tg ', 'tele ']):
        return "✈️ Telegram"
    elif any(k in combined for k in ['youtube', 'yt ', 'shorts']):
        return "🔴 YouTube"
    elif any(k in combined for k in ['facebook', 'fb ']):
        return "📘 Facebook"
    elif any(k in combined for k in ['tiktok', 'tik tok']):
        return "🎵 TikTok"
    elif any(k in combined for k in ['twitter', 'x ', 'tweet']):
        return "🐦 Twitter / X"
    elif any(k in combined for k in ['spotify', 'discord', 'threads', 'snapchat', 'linkedin']):
        return "🌐 Other Socials"
    return "⚡ General Boost"

# =======================================================================================
# 4. KEYBOARDS & NAVIGATION
# =======================================================================================
def main_kb(uid):
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add("🛒 Browse Services 🚀", "🎁 Claim Free 1K Views 🌟")
    kb.add("💰 My Profile 👤", "💳 Add Funds 💸")
    kb.add("📦 Order History 📜", "🤝 Referral Program 👥")
    kb.add("📞 Support 🎫")
    if uid == ADMIN_ID:
        kb.add("🧠 Admin: Smart Sync", "📈 Admin: Margin")
        kb.add("🎫 Admin: Tickets", "📢 Admin: Broadcast")
        kb.add("💾 Admin: Backup DB", "🔄 Admin: Restore DB")
    return kb

def back_cancel_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add("🔙 Step Back", "❌ Cancel to Menu")
    return kb

# =======================================================================================
# 5. CORE USER & ONBOARDING HANDLERS
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
            try: bot.send_message(referrer_id, "🎊 <b>BOOM! A friend just joined using your link!</b> 🎊\n🎁 <b>You received +1 Free 1K Views Credit!</b> 🌟", parse_mode="HTML")
            except: pass

    safe_name = html.escape(m.from_user.first_name or "User")
    msg = (
        f"👋 <b>Welcome to Enterprise SMM Panel, {safe_name}!</b> 🚀🔥\n\n"
        f"Boost your social media growth instantly across all major platforms with lightning fast speeds! 📈⚡️\n\n"
        f"👇 <b>HOW TO GET STARTED:</b>\n"
        f"1️⃣ <b>Add Balance:</b> Tap <b>'💳 Add Funds 💸'</b> to load your wallet safely.\n"
        f"2️⃣ <b>Browse Services:</b> Tap <b>'🛒 Browse Services 🚀'</b> to choose Instagram, Telegram, YouTube, etc.\n"
        f"3️⃣ <b>Place Order:</b> Check prices, average delivery times, and limits before placing orders with ease!\n\n"
        f"<i>Select any button below to start:</i> 👇✨"
    )
    bot.send_message(m.chat.id, msg, parse_mode="HTML", reply_markup=main_kb(uid))

@bot.message_handler(func=lambda m: m.text == "❌ Cancel to Menu")
def h_cancel(m):
    user_states.pop(m.from_user.id, None)
    bot.send_message(m.chat.id, "🚫 <b>Action Cancelled!</b> 🛑\n\n🏠 <i>You are back at the main menu.</i> ✨", parse_mode="HTML", reply_markup=main_kb(m.from_user.id))

@bot.message_handler(func=lambda m: m.text == "🔙 Step Back")
def h_step_back(m):
    uid = m.from_user.id
    state_data = user_states.get(uid, {})
    current_state = state_data.get("state")

    if current_state == "get_qty":
        user_states[uid]["state"] = "get_link"
        bot.send_message(m.chat.id, "🔙 <b>Went 1 step back!</b>\n\n🔗 <b>STEP 1: Send the Target Link</b> 📌\n<i>Paste your public link below:</i>", parse_mode="HTML", reply_markup=back_cancel_kb())
    elif current_state == "get_link":
        sid = state_data.get("sid")
        user_states.pop(uid, None)
        bot.send_message(m.chat.id, "🔙 <b>Returned to Service Details:</b>", parse_mode="HTML", reply_markup=main_kb(uid))
        if sid:
            show_service_card(m.chat.id, sid)
        else:
            h_browse(m)
    elif current_state == "fund_ss":
        user_states[uid]["state"] = "fund_amt"
        bot.send_message(m.chat.id, f"🔙 <b>Went 1 step back!</b>\n\n💸 <b>Enter deposit amount in INR (₹):</b>\n(Minimum: <code>₹{MIN_DEPOSIT}</code>)", parse_mode="HTML", reply_markup=back_cancel_kb())
    elif current_state in ["fund_amt", "claim_free_link", "waiting_ticket_text", "wait_margin", "wait_broadcast", "wait_for_db_upload"]:
        user_states.pop(uid, None)
        bot.send_message(m.chat.id, "🏠 <b>Returned to Main Menu:</b>", parse_mode="HTML", reply_markup=main_kb(uid))
    else:
        user_states.pop(uid, None)
        bot.send_message(m.chat.id, "🏠 <b>Main Menu:</b>", parse_mode="HTML", reply_markup=main_kb(uid))

@bot.message_handler(func=lambda m: m.text == "💰 My Profile 👤")
def h_profile(m):
    u = execute_db("SELECT balance, total_spent, free_views_credits, referral_code FROM users WHERE user_id=?", (m.from_user.id,), fetch=True)
    if not u: return
    ref_count = execute_db("SELECT COUNT(*) FROM referrals WHERE referrer_id=?", (m.from_user.id,), fetch=True)[0]
    msg = (
        f"👤 <b>YOUR VIP PROFILE & STATS</b> 📊👑\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 <b>User ID:</b> <code>{m.from_user.id}</code> 🔐\n"
        f"💳 <b>Wallet Balance:</b> <code>₹{u[0]:.2f}</code> 💵\n"
        f"📈 <b>Total Spent:</b> <code>₹{u[1]:.2f}</code> 🚀\n"
        f"🎁 <b>Free Views Credits:</b> <code>{u[2]}</code> 🌟\n"
        f"👥 <b>Total Friends Referred:</b> <code>{ref_count}</code> 🤝\n\n"
        f"💡 <i>Need more balance? Tap '💳 Add Funds 💸' below to top up!</i> ⚡️"
    )
    bot.send_message(m.chat.id, msg, parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text == "📦 Order History 📜")
def h_order_history(m):
    orders = execute_db("SELECT api_order_id, service_id, quantity, cost, status FROM orders WHERE user_id=? ORDER BY placed_time DESC LIMIT 5", (m.from_user.id,), fetch_all=True)
    if not orders: return bot.send_message(m.chat.id, "📦 <b>No orders placed yet!</b> 🛑\n\n🛒 <i>Tap 'Browse Services' to start growing your accounts!</i> 🚀", parse_mode="HTML")
    msg = "📦 <b>YOUR RECENT ORDERS:</b> 📜✨\n━━━━━━━━━━━━━━━━━━━\n"
    for o in orders:
        status_emoji = "✅" if o[4].lower() == "completed" else ("⏳" if o[4].lower() in ["pending", "processing", "in progress"] else "⚠️")
        msg += f"🧾 <b>Order ID:</b> <code>{o[0]}</code> 🆔\n🔢 <b>Quantity:</b> {o[2]} 📊 | 💰 <b>Cost:</b> ₹{o[3]:.2f} 💵\n{status_emoji} <b>Status:</b> <code>{o[4]}</code>\n───────────────────\n"
    bot.send_message(m.chat.id, msg, parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text == "📞 Support 🎫")
def h_support(m):
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("💬 Direct Chat with Owner 👨‍💻", url=f"https://t.me/{SUPPORT_USERNAME.replace('@','')}"),
        InlineKeyboardButton("🎫 Open Support Ticket 📝", callback_data="make_ticket")
    )
    bot.send_message(m.chat.id, "📞 <b>24/7 CUSTOMER SUPPORT DESK</b> 🛠️🆘\n\nNeed assistance with an order, balance deposit, or general inquiries? We are here to help!\n\n👇 <i>Choose an option below:</i>", parse_mode="HTML", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data == "make_ticket")
def h_ticket_init(c):
    bot.answer_callback_query(c.id)
    user_states[c.from_user.id] = {"state": "waiting_ticket_text"}
    bot.send_message(c.message.chat.id, "📝 <b>CREATE SUPPORT TICKET</b> 🎫\n\n👇 <i>Please write your message, transaction ID, or question below and hit send:</i>", parse_mode="HTML", reply_markup=back_cancel_kb())

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get("state") == "waiting_ticket_text")
def h_ticket_save(m):
    uid = m.from_user.id
    tid = execute_db("INSERT INTO tickets (user_id, message) VALUES (?,?)", (uid, m.text), return_id=True)
    user_states.pop(uid, None)
    bot.send_message(m.chat.id, f"✅ <b>Ticket #{tid} successfully logged!</b> 📨✨\n\n⏳ <i>Our admin team has received your ticket and will reply shortly.</i>", parse_mode="HTML", reply_markup=main_kb(uid))
    try: bot.send_message(ADMIN_ID, f"🚨 <b>NEW SUPPORT TICKET #{tid}</b> 🚨\nFrom: <code>{uid}</code>\n\n💬 {m.text}", parse_mode="HTML")
    except: pass

@bot.message_handler(func=lambda m: m.text == "🤝 Referral Program 👥")
def h_referral(m):
    uid = m.from_user.id
    u = execute_db("SELECT free_views_credits FROM users WHERE user_id=?", (uid,), fetch=True)
    ref_count = execute_db("SELECT COUNT(*) FROM referrals WHERE referrer_id=?", (uid,), fetch=True)[0]
    link = f"https://t.me/{bot.get_me().username}?start=ref_{uid}"
    msg = (
        f"🤝 <b>VIP REFERRAL REWARDS PROGRAM</b> 🎁💸\n━━━━━━━━━━━━━━━━━━━\n"
        f"Grow for completely FREE! Share your referral link with friends:\n\n"
        f"🔗 <b>Your Unique Invite Link:</b> 👇\n<code>{link}</code>\n\n"
        f"👥 <b>Friends Joined:</b> <code>{ref_count}</code> 🥳\n"
        f"🎁 <b>Free 1K Views Credits Available:</b> <code>{u[0]}</code> 🌟\n\n"
        f"🚀 <b>REWARD RULE:</b>\n"
        f"<i>Every person who starts this bot through your invite link gives you +1 Free Credit (1,000 Views)! Claim them anytime under 'Claim Free 1K Views'!</i> 🔥"
    )
    bot.send_message(m.chat.id, msg, parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text == "🎁 Claim Free 1K Views 🌟")
def h_claim_free(m):
    uid = m.from_user.id
    credits = execute_db("SELECT free_views_credits FROM users WHERE user_id=?", (uid,), fetch=True)[0]
    if credits <= 0: 
        return bot.send_message(m.chat.id, "❌ <b>You currently have 0 Free Credits!</b> 😔💔\n\n👥 <i>Invite friends using your Referral link to earn unlimited free views!</i> 🚀", parse_mode="HTML")
    user_states[uid] = {"state": "claim_free_link"}
    bot.send_message(m.chat.id, f"🎁 <b>You have {credits} free reward credit(s) available!</b> 🎉✨\n\n🔗 <b>STEP 1:</b> <i>Send the public post/video link where you want your 1,000 free views delivered:</i> 👇\n\n⚠️ <i>(Make sure the target profile is strictly PUBLIC!)</i> 🌍", parse_mode="HTML", reply_markup=back_cancel_kb())

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get("state") == "claim_free_link")
def h_process_free_claim(m):
    uid = m.from_user.id
    credits = execute_db("SELECT free_views_credits FROM users WHERE user_id=?", (uid,), fetch=True)[0]
    if credits <= 0: 
        user_states.pop(uid, None)
        return bot.send_message(m.chat.id, "❌ <b>No credits remaining.</b> 🛑", reply_markup=main_kb(uid), parse_mode="HTML")
    
    bot.send_message(m.chat.id, "⏳ <i>Processing your free 1,000 views order...</i> ⚙️🚀", parse_mode="HTML")
    api_res, prov_used = call_provider_api(FREE_VIEWS_PROVIDER, 'add', {'service': FREE_VIEWS_SERVICE_ID, 'link': m.text.strip(), 'quantity': 1000})
    if api_res and 'order' in api_res:
        execute_db("UPDATE users SET free_views_credits = free_views_credits - 1 WHERE user_id=?", (uid,))
        execute_db("INSERT INTO orders (user_id, provider, api_order_id, service_id, quantity, cost, auto_refill) VALUES (?,?,?,?,?,?,0)",
                   (uid, prov_used, api_res['order'], FREE_VIEWS_SERVICE_ID, 1000, 0.0))
        bot.send_message(m.chat.id, f"✅ <b>SUCCESS! 1,000 FREE VIEWS DISPATCHED!</b> 🎉🔥\n\n🧾 <b>Order ID:</b> <code>{api_res['order']}</code> 🆔\n🎁 <b>Remaining Credits:</b> <code>{credits - 1}</code> 🌟\n\n<i>Your views will begin delivering shortly!</i> 🚀", parse_mode="HTML", reply_markup=main_kb(uid))
    else: 
        bot.send_message(m.chat.id, "❌ <b>Order Submission Failed!</b> 💔\n<i>Please check that your target link is valid and public. No credit was deducted.</i> 🔄", parse_mode="HTML", reply_markup=main_kb(uid))
    user_states.pop(uid, None)

# =======================================================================================
# 6. BROWSING & COMPLETE SERVICE CARDS FLOW (ARRANGED BY PLATFORM)
# =======================================================================================
@bot.message_handler(func=lambda m: m.text == "🛒 Browse Services 🚀")
def h_browse(m):
    user_states.pop(m.from_user.id, None)
    platforms = execute_db("SELECT DISTINCT platform FROM managed_services WHERE disabled=0 ORDER BY platform ASC", fetch_all=True)
    if not platforms: 
        return bot.send_message(m.chat.id, "⚠️ <b>No services loaded yet!</b> ⏳\n<i>(Admin needs to tap '🧠 Admin: Smart Sync' first to load services.)</i> 🛠️", parse_mode="HTML")
    
    kb = InlineKeyboardMarkup(row_width=2)
    for idx, p in enumerate(platforms):
        kb.add(InlineKeyboardButton(f"{p[0]}", callback_data=f"plt_{idx}"))
    
    msg = (
        f"🛒 <b>CHOOSE YOUR PLATFORM:</b> 🌐✨\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"👇 <i>Select which platform you want to grow today:</i>"
    )
    bot.send_message(m.chat.id, msg, parse_mode="HTML", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("plt_"))
def h_platform_view(c):
    bot.answer_callback_query(c.id)
    idx = int(c.data.split("_")[1])
    platforms = execute_db("SELECT DISTINCT platform FROM managed_services WHERE disabled=0 ORDER BY platform ASC", fetch_all=True)
    if idx >= len(platforms): return
    platform_name = platforms[idx][0]
    
    cats = execute_db("SELECT DISTINCT category FROM managed_services WHERE platform=? AND disabled=0", (platform_name,), fetch_all=True)
    kb = InlineKeyboardMarkup(row_width=1)
    for c_idx, cat in enumerate(cats):
        kb.add(InlineKeyboardButton(f"📁 {cat[0]}", callback_data=f"cat_{idx}_{c_idx}"))
    kb.add(InlineKeyboardButton("🔙 Back to Platforms 🌐", callback_data="back_platforms"))
    
    msg = (
        f"📂 <b>{platform_name.upper()} CATEGORIES</b> 🚀\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"👇 <i>Select a category below to explore available packages:</i>"
    )
    bot.edit_message_text(msg, c.message.chat.id, c.message.message_id, parse_mode="HTML", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data == "back_platforms")
def h_back_platforms(c):
    bot.answer_callback_query(c.id)
    platforms = execute_db("SELECT DISTINCT platform FROM managed_services WHERE disabled=0 ORDER BY platform ASC", fetch_all=True)
    kb = InlineKeyboardMarkup(row_width=2)
    for idx, p in enumerate(platforms):
        kb.add(InlineKeyboardButton(f"{p[0]}", callback_data=f"plt_{idx}"))
    bot.edit_message_text("🛒 <b>CHOOSE YOUR PLATFORM:</b> 🌐✨\n━━━━━━━━━━━━━━━━━━━\n👇 <i>Select which platform you want to grow today:</i>", c.message.chat.id, c.message.message_id, parse_mode="HTML", reply_markup=kb)

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
    for s in svcs:
        final_rate = s[2] * s[3]
        kb.add(InlineKeyboardButton(f"⭐ {s[1]} - ₹{final_rate:.2f}/1K", callback_data=f"card_{s[0]}_{p_idx}_{c_idx}"))
    kb.add(InlineKeyboardButton(f"🔙 Back to {platform_name} Categories", callback_data=f"plt_{p_idx}"))
    
    msg = (
        f"📂 <b>{html.escape(category_name.upper())}</b> 📊\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"👇 <i>Tap on any service below to view full details (Speed, Limits, Pricing):</i>"
    )
    bot.edit_message_text(msg, c.message.chat.id, c.message.message_id, parse_mode="HTML", reply_markup=kb)

def show_service_card(chat_id, service_id, message_id=None, p_idx=None, c_idx=None):
    svc = execute_db("SELECT service_id, platform, category, name, rate, min_qty, max_qty, avg_time, margin FROM managed_services WHERE service_id=?", (service_id,), fetch=True)
    if not svc: return
    
    sid, platform, category, name, rate, min_q, max_q, avg_time, margin = svc
    final_price_per_1k = rate * margin
    
    card_text = (
        f"🏷️ <b>SERVICE DETAILS & SPECIFICATIONS</b> 📋\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"📌 <b>Service:</b> {html.escape(name)}\n"
        f"🆔 <b>Service ID:</b> <code>{sid}</code>\n"
        f"🌐 <b>Platform:</b> {platform}\n\n"
        f"💰 <b>Price:</b> <code>₹{final_price_per_1k:.2f}</code> per 1,000\n"
        f"📊 <b>Order Limits:</b> Min <code>{min_q:,}</code> — Max <code>{max_q:,}</code>\n"
        f"⏱️ <b>Avg Speed / Delivery:</b> <code>{avg_time}</code>\n"
        f"♻️ <b>Refill Guarantee:</b> <code>Auto-Refill Active</code> 🛡️\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"<i>Ready to place this order? Tap the button below!</i> 👇🚀"
    )
    
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("🚀 Order This Service Now", callback_data=f"buy_{sid}"))
    if p_idx is not None and c_idx is not None:
        kb.add(InlineKeyboardButton("🔙 Back to Services List", callback_data=f"cat_{p_idx}_{c_idx}"))
    else:
        kb.add(InlineKeyboardButton("🔙 Browse All Services", callback_data="back_platforms"))
    
    if message_id:
        bot.edit_message_text(card_text, chat_id, message_id, parse_mode="HTML", reply_markup=kb)
    else:
        bot.send_message(chat_id, card_text, parse_mode="HTML", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("card_"))
def h_card_view(c):
    bot.answer_callback_query(c.id)
    _, sid, p_idx, c_idx = c.data.split("_")
    show_service_card(c.message.chat.id, int(sid), c.message.message_id, int(p_idx), int(c_idx))

@bot.callback_query_handler(func=lambda c: c.data.startswith("buy_"))
def h_buy_service(c):
    bot.answer_callback_query(c.id)
    sid = int(c.data.split("_")[1])
    svc = execute_db("SELECT name, min_qty, max_qty, rate, margin FROM managed_services WHERE service_id=?", (sid,), fetch=True)
    if not svc: return
    
    user_states[c.from_user.id] = {"state": "get_link", "sid": sid}
    
    msg = (
        f"🚀 <b>ORDERING: {html.escape(svc[0])}</b>\n\n"
        f"🔗 <b>STEP 1: Send the Target Link</b> 📌\n\n"
        f"💡 <i>Paste the exact post/profile URL below and press send:</i>\n"
        f"⚠️ <i>(Target account must be strictly PUBLIC!)</i> 🌍"
    )
    bot.send_message(c.message.chat.id, msg, parse_mode="HTML", reply_markup=back_cancel_kb())

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get("state") == "get_link")
def h_link_input(m):
    uid = m.from_user.id
    target_link = m.text.strip()
    sid = user_states[uid]["sid"]
    svc = execute_db("SELECT min_qty, max_qty, rate, margin FROM managed_services WHERE service_id=?", (sid,), fetch=True)
    
    user_states[uid].update({"state": "get_qty", "link": target_link})
    
    msg = (
        f"✅ <b>Link Received Successfully!</b> 🔗\n\n"
        f"🔢 <b>STEP 2: Enter Quantity</b> 📊\n"
        f"Allowed range: <code>{svc[0]:,}</code> to <code>{svc[1]:,}</code>\n\n"
        f"💡 <i>Type the exact number (e.g. 1000) and press send:</i> 👇"
    )
    bot.send_message(m.chat.id, msg, parse_mode="HTML", reply_markup=back_cancel_kb())

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get("state") == "get_qty")
def h_qty_input(m):
    uid = m.from_user.id
    state = user_states[uid]
    try: 
        qty = int(m.text.replace(',', '').strip())
    except: 
        return bot.send_message(m.chat.id, "❌ <b>Invalid Input!</b> Please type numbers only (e.g. 1000). 🛑", parse_mode="HTML", reply_markup=back_cancel_kb())

    svc = execute_db("SELECT service_id, provider, provider_service_id, rate, margin, min_qty, max_qty FROM managed_services WHERE service_id=?", (state["sid"],), fetch=True)
    if not svc: return
    
    _, prov_name, prov_sid, rate, margin, min_q, max_q = svc
    
    if qty < min_q or qty > max_q:
        return bot.send_message(m.chat.id, f"🚫 <b>Quantity Out of Range!</b>\nMin allowed: <code>{min_q:,}</code> | Max: <code>{max_q:,}</code>\n\n<i>Please enter a valid amount:</i>", parse_mode="HTML", reply_markup=back_cancel_kb())

    cost = (qty / 1000.0) * (rate * margin)
    u_bal = execute_db("SELECT balance FROM users WHERE user_id=?", (uid,), fetch=True)[0]
    
    if u_bal < cost: 
        user_states.pop(uid, None)
        return bot.send_message(m.chat.id, f"❌ <b>INSUFFICIENT BALANCE!</b> 😔💔\n\n💰 <b>Order Cost:</b> <code>₹{cost:.2f}</code>\n💵 <b>Your Wallet:</b> <code>₹{u_bal:.2f}</code>\n\n👇 <i>Tap '💳 Add Funds 💸' to top up and retry!</i> ⚡️", parse_mode="HTML", reply_markup=main_kb(uid))

    bot.send_message(m.chat.id, "⏳ <i>Transmitting order securely to provider... Please wait...</i> ⚙️🚀", parse_mode="HTML")
    api_res, prov_used = call_provider_api(prov_name, 'add', {'service': prov_sid, 'link': state['link'], 'quantity': qty})
    
    if api_res and 'order' in api_res:
        execute_db("UPDATE users SET balance=balance-?, total_spent=total_spent+? WHERE user_id=?", (cost, cost, uid))
        execute_db("INSERT INTO orders (user_id, provider, api_order_id, service_id, quantity, cost, auto_refill) VALUES (?,?,?,?,?,?,1)",
                   (uid, prov_used, api_res['order'], state["sid"], qty, cost))
        msg = (
            f"✅ <b>ORDER DISPATCHED SUCCESSFULLY!</b> 🎉🔥\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"🧾 <b>Order ID:</b> <code>{api_res['order']}</code> 🆔\n"
            f"🔢 <b>Quantity:</b> <code>{qty:,}</code> 📊\n"
            f"💰 <b>Total Deducted:</b> ₹{cost:.2f} 💵\n"
            f"♻️ <b>Auto-Refill:</b> Enabled & Active 🛡️\n\n"
            f"<i>Track live delivery progress in '📦 Order History 📜'!</i> 🚀"
        )
        bot.send_message(m.chat.id, msg, parse_mode="HTML", reply_markup=main_kb(uid))
    else: 
        bot.send_message(m.chat.id, "❌ <b>Provider Dispatch Error!</b> 🛑\nThe service is temporarily busy. Your balance was NOT deducted. Please try an alternative service package.", parse_mode="HTML", reply_markup=main_kb(uid))
    
    user_states.pop(uid, None)

# =======================================================================================
# 7. ADD FUNDS & MANUAL ESCROW APPROVAL (MIN: ₹15)
# =======================================================================================
@bot.message_handler(func=lambda m: m.text == "💳 Add Funds 💸")
def h_add_funds(m):
    user_states[m.from_user.id] = {"state": "fund_amt"}
    msg = (
        f"💸 <b>TOP UP YOUR WALLET BALANCE</b> 🏦✨\n\n"
        f"🔢 <b>STEP 1:</b> <i>Type the exact amount in INR (₹) you wish to deposit and send:</i> 👇\n\n"
        f"⚠️ <i>(Minimum Deposit:</i> <code>₹{MIN_DEPOSIT}</code><i>)</i>\n"
        f"💡 <i>Example: Type <b>50</b> to deposit ₹50.</i> 💵"
    )
    bot.send_message(m.chat.id, msg, parse_mode="HTML", reply_markup=back_cancel_kb())

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get("state") == "fund_amt")
def h_fund_qr(m):
    try:
        amt = float(m.text.strip())
        if amt < MIN_DEPOSIT: 
            return bot.send_message(m.chat.id, f"🚫 <b>Minimum deposit is <code>₹{MIN_DEPOSIT}</code>!</b> Please enter ₹{MIN_DEPOSIT} or more: 🛑", parse_mode="HTML", reply_markup=back_cancel_kb())
        
        user_states[m.from_user.id] = {"state": "fund_ss", "amt": amt}
        qr = f"https://api.qrserver.com/v1/create-qr-code/?size=400x400&data={urllib.parse.quote(f'upi://pay?pa={UPI_ID}&am={amt}&cu=INR')}"
        res = requests.get(qr, timeout=10)
        
        msg = (
            f"💳 <b>PAYMENT DETAILS & QR CODE</b> 💳🔒\n\n"
            f"📱 <b>STEP 2:</b> <i>Pay EXACTLY</i> <code>₹{amt}</code> <i>using the QR Code above OR copy this UPI ID:</i>\n"
            f"👉 <code>{UPI_ID}</code> 📋\n\n"
            f"📸 <b>STEP 3: Upload Payment Screenshot!</b> 🖼️\n"
            f"<i>After completing payment in Paytm/PhonePe/GPay, send the screenshot photo here:</i> 👇"
        )
        bot.send_photo(m.chat.id, BytesIO(res.content), caption=msg, parse_mode="HTML", reply_markup=back_cancel_kb())
    except: 
        bot.send_message(m.chat.id, "❌ <b>Please type a valid numerical amount (e.g. 50, 100).</b> 🔢🛑", parse_mode="HTML", reply_markup=back_cancel_kb())

@bot.message_handler(content_types=['photo'])
def h_payment_ss(m):
    uid = m.from_user.id
    if user_states.get(uid, {}).get("state") == "fund_ss":
        amt = user_states[uid]["amt"]
        tx = execute_db("INSERT INTO transactions (user_id, amount, status) VALUES (?, ?, 'PENDING')", (uid, amt), return_id=True)
        kb = InlineKeyboardMarkup().add(
            InlineKeyboardButton("✅ Approve Deposit", callback_data=f"ap_{tx}_{uid}_{amt}"),
            InlineKeyboardButton("❌ Reject Deposit", callback_data=f"rj_{tx}_{uid}")
        )
        bot.send_photo(ADMIN_ID, m.photo[-1].file_id, caption=f"🚨 <b>NEW DEPOSIT REQUEST!</b> 🚨\n\n👤 <b>User ID:</b> <code>{uid}</code>\n💵 <b>Amount:</b> <code>₹{amt}</code>\n🧾 <b>TXN ID:</b> <code>{tx}</code>", parse_mode="HTML", reply_markup=kb)
        
        msg = (
            f"✅ <b>SCREENSHOT RECEIVED!</b> 📸🎉\n\n"
            f"⏳ <i>Our admin team is verifying your payment. Your balance will be credited automatically within minutes!</i> 🏦✨"
        )
        bot.send_message(m.chat.id, msg, parse_mode="HTML", reply_markup=main_kb(uid))
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
        bot.edit_message_caption(f"✅ <b>APPROVED TXN-{tx}</b> | Added ₹{amt} successfully! 💸", c.message.chat.id, c.message.message_id, parse_mode="HTML")
        try: bot.send_message(uid, f"🎉 <b>PAYMENT APPROVED!</b> 💳🔥\n\n<code>₹{amt}</code> <i>has been added to your wallet! You can now place orders!</i> 🚀", parse_mode="HTML")
        except: pass
    else:
        execute_db("UPDATE transactions SET status='REJECTED' WHERE tx_id=?", (tx,))
        bot.edit_message_caption(f"❌ <b>REJECTED TXN-{tx}</b> 🛑", c.message.chat.id, c.message.message_id, parse_mode="HTML")
        try: bot.send_message(uid, f"❌ <b>DEPOSIT VERIFICATION FAILED!</b> 🛑\n\n<i>Your payment screenshot was rejected. Contact Support if this is an error.</i> 📞", parse_mode="HTML")
        except: pass

# =======================================================================================
# 8. ADMIN MANAGEMENT (SMART SYNC + MARGINS + BACKUP/RESTORE)
# =======================================================================================
@bot.message_handler(func=lambda m: m.text == "🧠 Admin: Smart Sync" and m.from_user.id == ADMIN_ID)
def h_admin_smart_sync(m):
    bot.send_message(ADMIN_ID, "🧠 <i>Smart Sync in progress... Categorizing by Platform and selecting best prices/speeds...</i> ⚙️🔎", parse_mode="HTML")
    res, _ = call_provider_api("provider_primary", "services")
    if not res or not isinstance(res, list): return bot.send_message(ADMIN_ID, "❌ <b>API Connection Failed.</b> 🛑", parse_mode="HTML")
    
    execute_db("DELETE FROM managed_services")
    margin = float(execute_db("SELECT value FROM settings WHERE key='global_margin'", fetch=True)[0])
    
    categories = {}
    for s in res:
        cat_name = s.get('category', 'General')
        if cat_name not in categories: categories[cat_name] = []
        categories[cat_name].append(s)
        
    added_count = 0
    for cat_name, svcs in categories.items():
        cat_lower = cat_name.lower()
        if any(x in cat_lower for x in ['like', 'view', 'share', 'repost', 'story', 'comment']):
            svcs.sort(key=lambda x: float(x.get('rate', 9999)))
            best_svcs = svcs[:2]
        elif any(x in cat_lower for x in ['follower', 'subscriber', 'member']):
            hq_svcs = [x for x in svcs if any(k in x.get('name', '').lower() for k in ['refill', 'guarantee', 'hq', 'real', 'non drop'])]
            if not hq_svcs: hq_svcs = svcs
            hq_svcs.sort(key=lambda x: float(x.get('rate', 0)), reverse=True)
            best_svcs = hq_svcs[-3:]
        else:
            svcs.sort(key=lambda x: float(x.get('rate', 9999)))
            best_svcs = svcs[:1]
            
        for s in best_svcs:
            try:
                platform = detect_platform(cat_name, s.get('name', ''))
                avg_time = "10 - 60 Mins" if "instant" in s.get('name', '').lower() or "fast" in s.get('name', '').lower() else "1 - 24 Hours"
                execute_db("""INSERT OR REPLACE INTO managed_services 
                    (service_id, platform, category, name, provider, provider_service_id, rate, min_qty, max_qty, avg_time, margin, disabled) 
                    VALUES (?, ?, ?, ?, 'provider_primary', ?, ?, ?, ?, ?, ?, 0)""",
                    (int(s['service']), platform, cat_name, s['name'], int(s['service']), float(s['rate']), int(s.get('min', 10)), int(s.get('max', 100000)), avg_time, margin))
                added_count += 1
            except: continue

    bot.send_message(ADMIN_ID, f"✅ <b>SMART SYNC COMPLETE!</b> 🚀🎉\nCategorized and organized <b>{added_count}</b> top-tier services across platforms (Instagram, Telegram, YouTube, FB, etc.). 📊", parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text == "📈 Admin: Margin" and m.from_user.id == ADMIN_ID)
def h_admin_margin(m):
    user_states[ADMIN_ID] = {"state": "wait_margin"}
    bot.send_message(ADMIN_ID, "📈 <b>SET PROFIT MARGIN</b> 💰\n\nEnter desired profit % (e.g. type <b>50</b> for 50% markup): 👇", parse_mode="HTML", reply_markup=back_cancel_kb())

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get("state") == "wait_margin" and m.from_user.id == ADMIN_ID)
def h_process_margin(m):
    try:
        pct = float(m.text.strip())
        multiplier = 1.0 + (pct / 100.0)
        execute_db("UPDATE settings SET value=? WHERE key='global_margin'", (str(multiplier),))
        execute_db("UPDATE managed_services SET margin=?", (multiplier,))
        bot.send_message(ADMIN_ID, f"✅ <b>Margin Updated!</b> All prices marked up by {pct}%. 💸", parse_mode="HTML", reply_markup=main_kb(ADMIN_ID))
    except: 
        bot.send_message(ADMIN_ID, "❌ <b>Type numbers only.</b> 🛑", parse_mode="HTML")
    user_states.pop(ADMIN_ID, None)

@bot.message_handler(func=lambda m: m.text == "📢 Admin: Broadcast" and m.from_user.id == ADMIN_ID)
def h_admin_broadcast(m):
    user_states[ADMIN_ID] = {"state": "wait_broadcast"}
    bot.send_message(ADMIN_ID, "📢 <b>MASS BROADCAST</b>\n\nType the message to send to all users:", parse_mode="HTML", reply_markup=back_cancel_kb())

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get("state") == "wait_broadcast" and m.from_user.id == ADMIN_ID)
def h_process_broadcast(m):
    users = execute_db("SELECT user_id FROM users WHERE is_banned=0", fetch_all=True)
    sent, failed = 0, 0
    for u in users:
        try: bot.send_message(u[0], f"📢 <b>ANNOUNCEMENT:</b> 🔔\n\n{m.text}", parse_mode="HTML"); sent += 1
        except: failed += 1
    user_states.pop(ADMIN_ID, None)
    bot.send_message(ADMIN_ID, f"✅ Broadcast sent to {sent} users. ({failed} failed).", parse_mode="HTML", reply_markup=main_kb(ADMIN_ID))

@bot.message_handler(func=lambda m: m.text == "🎫 Admin: Tickets" and m.from_user.id == ADMIN_ID)
def h_admin_view_tickets(m):
    tickets = execute_db("SELECT ticket_id, user_id, message FROM tickets WHERE status='OPEN' LIMIT 5", fetch_all=True)
    if not tickets: return bot.send_message(ADMIN_ID, "✅ <b>No open tickets right now.</b> 🎉", parse_mode="HTML")
    for t in tickets: bot.send_message(ADMIN_ID, f"🎫 <b>Ticket #{t[0]}</b>\nUser: <code>{t[1]}</code>\n\n💬 {t[2]}", parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text == "💾 Admin: Backup DB" and m.from_user.id == ADMIN_ID)
def handle_admin_backup(m):
    uid = m.from_user.id
    bot.send_message(uid, "⏳ <i>Generating snapshot...</i> 🔐📁", parse_mode="HTML")
    backup_file = f"backup_{int(time.time())}.db"
    try:
        with db_lock:
            with sqlite3.connect('panel_v15.db') as src, sqlite3.connect(backup_file) as dst: src.backup(dst)
        with open(backup_file, 'rb') as doc:
            bot.send_document(uid, doc, caption="💾 <b>Database Backup</b> 🔐✅", parse_mode="HTML")
    except Exception as e: bot.send_message(uid, f"❌ Backup Failed: <code>{e}</code>", parse_mode="HTML")
    finally:
        if os.path.exists(backup_file): os.remove(backup_file)

@bot.message_handler(func=lambda m: m.text == "🔄 Admin: Restore DB" and m.from_user.id == ADMIN_ID)
def handle_admin_restore_prompt(m):
    user_states[ADMIN_ID] = {"state": "wait_for_db_upload"}
    bot.send_message(ADMIN_ID, "⚠️ Upload your valid <code>.db</code> file as a document below: 👇", parse_mode="HTML", reply_markup=back_cancel_kb())

@bot.message_handler(content_types=['document'])
def handle_document_upload(m):
    uid = m.from_user.id
    if uid == ADMIN_ID and user_states.get(uid, {}).get("state") == "wait_for_db_upload":
        if not m.document.file_name.endswith('.db'): return bot.send_message(uid, "❌ Upload a .db file only.", parse_mode="HTML", reply_markup=main_kb(uid))
        temp_file = f"restore_{int(time.time())}.db"
        bot.send_message(uid, "⏳ <i>Restoring database...</i> ⚙️🔄", parse_mode="HTML")
        try:
            downloaded = bot.download_file(bot.get_file(m.document.file_id).file_path)
            with open(temp_file, 'wb') as f: f.write(downloaded)
            with db_lock:
                with sqlite3.connect(temp_file) as src, sqlite3.connect('panel_v15.db') as dst: src.backup(dst)
            bot.send_message(uid, "✅ <b>DATABASE RESTORED SUCCESSFULLY!</b> 🚀🎉", parse_mode="HTML", reply_markup=main_kb(uid))
        except Exception as e: bot.send_message(uid, f"❌ Restore Failed: {e}", parse_mode="HTML", reply_markup=main_kb(uid))
        finally:
            user_states.pop(uid, None)
            if os.path.exists(temp_file): os.remove(temp_file)

# =======================================================================================
# 9. BACKGROUND TASKS
# =======================================================================================
def auto_refill_and_status_monitor():
    while True:
        try:
            orders = execute_db("SELECT db_id, provider, api_order_id, user_id FROM orders WHERE status IN ('pending', 'In progress', 'Processing')", fetch_all=True)
            if orders:
                for o in orders:
                    res, _ = call_provider_api(o[1], 'status', {'order': o[2]})
                    if res and 'status' in res: execute_db("UPDATE orders SET status=? WHERE db_id=?", (res['status'].capitalize(), o[0]))
            
            refillable = execute_db("SELECT db_id, provider, api_order_id, user_id FROM orders WHERE auto_refill=1 AND status IN ('Completed', 'Partial')", fetch_all=True)
            if refillable:
                for ro in refillable:
                    res, _ = call_provider_api(ro[1], 'refill', {'order': ro[2]})
                    if res and 'refill' in res: execute_db("UPDATE orders SET last_refill_check=CURRENT_TIMESTAMP WHERE db_id=?", (ro[0],))
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
