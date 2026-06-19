"""
=========================================================================================
🔥 CHEAP SMM PANEL BOT - ENTERPRISE V12 ULTIMATE (ALL FEATURES) 🔥
=========================================================================================
"""

import telebot, requests, sqlite3, logging, time, os, urllib.parse, threading
from io import BytesIO
from flask import Flask
from datetime import datetime, timedelta, date
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import random, math, json

# =======================================================================================
# 1. SERVER, CONFIG & PUBLIC IDS
# =======================================================================================
logging.basicConfig(level=logging.INFO)
app = Flask(__name__)
@app.route('/')
def home(): return "🔥 V12 ULTIMATE ONLINE 🔥"

BOT_TOKEN = os.environ.get('BOT_TOKEN', '8228287584:AAFRRCZNS8E1B3YrNe99mJHX_00bvsgPZh8')
API_KEY = os.environ.get('API_KEY', '8228287584:AAEl3udbq2GC3LK__TwpPYxhrFWa91-1hBo')

bot = telebot.TeleBot(BOT_TOKEN, threaded=True, num_threads=10)

API_URL = "https://indiansmmprovider.in/api/v2"
ADMIN_ID = 6034840006
UPI_ID = "rahikhann@fam"

CHANNEL_ID = "@cspnotice"
CHANNEL_LINK = "https://t.me/cspnotice"
LOG_GROUP_ID = "@csplogs"

MIN_DEPOSIT = 10.0
user_states = {}

# =======================================================================================
# 2. DATABASE ENGINE (UPDATED FOR ALL FEATURES)
# =======================================================================================
def execute_db(query, params=(), fetch=False, fetch_all=False, return_id=False):
    try:
        with sqlite3.connect('panel_v12.db', check_same_thread=False, timeout=20) as conn:
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
        logging.error(f"DB Error: {e}")
        return False

def init_database():
    # Original tables
    execute_db("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT, balance REAL DEFAULT 0.0, total_spent REAL DEFAULT 0.0, verified INTEGER DEFAULT 0, is_banned INTEGER DEFAULT 0, referral_code TEXT UNIQUE, referrer_id INTEGER, segment TEXT DEFAULT 'new', joined_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    execute_db("CREATE TABLE IF NOT EXISTS transactions (tx_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount REAL, status TEXT, date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    execute_db("CREATE TABLE IF NOT EXISTS orders (db_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, api_order_id TEXT, service_id INTEGER, quantity INTEGER, cost REAL, status TEXT DEFAULT 'pending', placed_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP, completed_time TIMESTAMP)")
    execute_db("CREATE TABLE IF NOT EXISTS managed_services (service_id INTEGER PRIMARY KEY, category TEXT, name TEXT, rate REAL, margin REAL DEFAULT 1.45, orders_count INTEGER DEFAULT 0, success_rate REAL DEFAULT 95.0, avg_delivery_minutes INTEGER DEFAULT 120, disabled INTEGER DEFAULT 0)")
    execute_db("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
    execute_db("CREATE TABLE IF NOT EXISTS promos (code TEXT PRIMARY KEY, amount REAL, max_uses INTEGER, current_uses INTEGER DEFAULT 0)")
    execute_db("CREATE TABLE IF NOT EXISTS promo_redeems (user_id INTEGER, code TEXT, PRIMARY KEY(user_id, code))")
    execute_db("CREATE TABLE IF NOT EXISTS tickets (ticket_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, message TEXT, status TEXT DEFAULT 'OPEN', reply TEXT, replied_at TIMESTAMP)")

    # New tables for features
    execute_db("CREATE TABLE IF NOT EXISTS favorites (user_id INTEGER, service_id INTEGER, PRIMARY KEY(user_id, service_id))")
    execute_db("CREATE TABLE IF NOT EXISTS referrals (referrer_id INTEGER, referred_id INTEGER, total_earned REAL DEFAULT 0, PRIMARY KEY(referrer_id, referred_id))")
    execute_db("CREATE TABLE IF NOT EXISTS order_templates (template_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, name TEXT, service_id INTEGER, quantity INTEGER, link_format TEXT)")
    execute_db("CREATE TABLE IF NOT EXISTS activity_feed (id INTEGER PRIMARY KEY AUTOINCREMENT, message TEXT, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    execute_db("CREATE TABLE IF NOT EXISTS user_notify_settings (user_id INTEGER PRIMARY KEY, order_updates INTEGER DEFAULT 1, promotions INTEGER DEFAULT 0, tips INTEGER DEFAULT 0, quiet_start TEXT, quiet_end TEXT)")
    execute_db("CREATE TABLE IF NOT EXISTS knowledge_base (article_id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, content TEXT, category TEXT, views INTEGER DEFAULT 0)")
    execute_db("CREATE TABLE IF NOT EXISTS delivery_stats (service_id INTEGER, delivery_seconds INTEGER, order_date DATE)")

    # Default settings
    if not execute_db("SELECT value FROM settings WHERE key='global_margin'", fetch=True):
        execute_db("INSERT INTO settings (key, value) VALUES ('global_margin', '1.45')")
    if not execute_db("SELECT value FROM settings WHERE key='flash_sale_active'", fetch=True):
        execute_db("INSERT INTO settings (key, value) VALUES ('flash_sale_active', '0')")
    if not execute_db("SELECT value FROM settings WHERE key='flash_sale_multiplier'", fetch=True):
        execute_db("INSERT INTO settings (key, value) VALUES ('flash_sale_multiplier', '0.8')")

    # Seed knowledge base if empty
    if not execute_db("SELECT COUNT(*) FROM knowledge_base", fetch=True)[0]:
        articles = [
            ("Getting Started", "To place your first order, tap 'Browse Services', choose a category, select a service, and follow the prompts.", "basics"),
            ("Link Formats", "Instagram: post link. YouTube: video URL. Telegram: channel link. Always use the exact target link.", "basics"),
            ("Refill vs New Order", "Use 'Refill' on partial orders to top up. New order if you need a different quantity.", "troubleshooting"),
            ("Why Followers Drop?", "Some services have a natural drop rate. Premium services have better retention. Check our comparison tool.", "tips"),
            ("Payment Issues", "If your deposit isn't credited, make sure you sent the screenshot and the UPI transaction ID is visible.", "troubleshooting")
        ]
        for title, content, cat in articles:
            execute_db("INSERT INTO knowledge_base (title, content, category) VALUES (?,?,?)", (title, content, cat))

# =======================================================================================
# 3. MIDDLEWARE & CHECKS
# =======================================================================================
def check_sub(uid):
    if uid == ADMIN_ID: return True
    try:
        status = bot.get_chat_member(CHANNEL_ID, uid).status
        return status in ['member', 'administrator', 'creator']
    except: return True

def log_order(user, sname, qty):
    try: bot.send_message(LOG_GROUP_ID, f"🎉 NEW ORDER\n👤 @{user}\n📦 {qty}x {sname}\n✅ Status: Processing", parse_mode="Markdown")
    except: pass

def get_margin():
    r = execute_db("SELECT value FROM settings WHERE key='global_margin'", fetch=True)
    return float(r[0]) if r else 1.45

def call_api(action, extra=None):
    payload = {'key': API_KEY, 'action': action}
    if extra: payload.update(extra)
    try: return requests.post(API_URL, data=payload, timeout=15).json()
    except: return None

def generate_referral_code(user_id):
    code = f"REF{user_id}{random.randint(100,999)}"
    execute_db("UPDATE users SET referral_code=? WHERE user_id=?", (code, user_id))
    return code

# =======================================================================================
# 4. KEYBOARDS (UPDATED WITH NEW BUTTONS)
# =======================================================================================
def main_kb(uid):
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add("🛒 Browse Services 🚀", "⭐ My Favorites")
    kb.add("💰 My Profile", "💳 Add Funds")
    kb.add("📦 Order History", "📋 My Templates")
    kb.add("🎟️ Redeem Promo", "📞 Support")
    kb.add("⚖️ Compare Services", "📚 Knowledge Base")
    kb.add("👥 Referral Program", "🔥 Live Activity")
    if uid == ADMIN_ID:
        kb.add("👑 --- ADMIN ZONE --- 👑")
        kb.add("⚙️ Manage Services", "📈 Adjust Margins")
        kb.add("📢 Broadcast", "🎟️ Create Promo")
        kb.add("🏦 API Ledger", "🎟️ Open Tickets")
        kb.add("🧪 Flash Sale Toggle", "📊 Smart Pricing")
    return kb

def cancel_kb(): return ReplyKeyboardMarkup(resize_keyboard=True, row_width=2).add("🔙 Back", "❌ Cancel")

# =======================================================================================
# 5. CORE HANDLERS (UPDATED)
# =======================================================================================
@bot.message_handler(commands=['start'])
def h_start(m):
    uid = m.from_user.id
    if not check_sub(uid):
        kb = InlineKeyboardMarkup().add(InlineKeyboardButton("Join Channel", url=CHANNEL_LINK))
        return bot.send_message(m.chat.id, "🛑 You must join our channel to use the bot!", reply_markup=kb)

    u = execute_db("SELECT * FROM users WHERE user_id=?", (uid,), fetch=True)
    if not u:
        # New user: check referral
        referrer = None
        if len(m.text.split()) > 1 and m.text.split()[1].startswith('ref_'):
            try: referrer = int(m.text.split()[1].replace('ref_', ''))
            except: pass
        execute_db("INSERT INTO users (user_id, username, first_name, referrer_id) VALUES (?,?,?,?)",
                   (uid, m.from_user.username, m.from_user.first_name, referrer))
        code = generate_referral_code(uid)
        if referrer:
            execute_db("INSERT OR IGNORE INTO referrals (referrer_id, referred_id) VALUES (?,?)", (referrer, uid))
        u = execute_db("SELECT * FROM users WHERE user_id=?", (uid,), fetch=True)
    elif u[6] == 1:
        return bot.send_message(m.chat.id, "🚫 You have been banned.")

    # Show live activity and tips on start
    activity_msg = get_live_activity()
    bot.send_message(m.chat.id, activity_msg, parse_mode="Markdown")
    tip = get_tip_of_the_day()
    bot.send_message(m.chat.id, f"💡 *Tip of the Day:* {tip}", parse_mode="Markdown", reply_markup=main_kb(uid))

@bot.message_handler(func=lambda m: m.text == "❌ Cancel")
def h_cancel(m):
    user_states.pop(m.from_user.id, None)
    bot.send_message(m.chat.id, "🚫 Action Cancelled.", reply_markup=main_kb(m.from_user.id))

@bot.message_handler(func=lambda m: m.text == "🔙 Back")
def h_back(m):
    uid = m.from_user.id
    state = user_states.get(uid, {}).get("state")
    if state == "get_qty":
        user_states[uid]["state"] = "get_link"
        bot.send_message(m.chat.id, "🔗 *STEP 1: Send Target Link*", parse_mode="Markdown", reply_markup=cancel_kb())
    elif state == "get_link":
        user_states.pop(uid, None)
        bot.send_message(m.chat.id, "🏠 Returned to Menu.", reply_markup=main_kb(uid))
        h_browse(m)
    elif state == "fund_ss":
        user_states[uid]["state"] = "fund_amt"
        bot.send_message(m.chat.id, f"💸 *Enter deposit amount (₹):*\n(Minimum `₹{MIN_DEPOSIT}`)", parse_mode="Markdown", reply_markup=cancel_kb())
    elif state == "svc_ids":
        user_states[uid]["state"] = "svc_cat"
        bot.send_message(m.chat.id, "📁 Category Name (e.g. Instagram):", reply_markup=cancel_kb())
    else:
        user_states.pop(uid, None)
        bot.send_message(m.chat.id, "🏠 Returned to Main Menu.", reply_markup=main_kb(uid))

@bot.message_handler(func=lambda m: m.text == "💰 My Profile")
def h_profile(m):
    uid = m.from_user.id
    u = execute_db("SELECT * FROM users WHERE user_id=?", (uid,), fetch=True)
    ref_earnings = execute_db("SELECT COALESCE(SUM(total_earned),0) FROM referrals WHERE referrer_id=?", (uid,), fetch=True)[0]
    ref_count = execute_db("SELECT COUNT(*) FROM referrals WHERE referrer_id=?", (uid,), fetch=True)[0]
    badge = "💎 Diamond" if u[4]>=20000 else ("👑 VIP" if u[4]>=5000 else ("⭐ Active" if u[4]>=1000 else "🌱 New"))
    msg = f"💧 *USER PROFILE* 💧\n━━━━━━━━━━━━━━━━━━━\n🆔 *ID:* `{u[0]}`\n🎖️ *Status:* {badge}\n💰 *Balance:* `₹{u[3]:.2f}`\n📈 *Total Spent:* `₹{u[4]:.2f}`\n👥 *Referrals:* {ref_count} (₹{ref_earnings:.2f})\n🔗 *Your Ref Code:* `{u[7]}`"
    bot.send_message(m.chat.id, msg, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "📚 Knowledge Base")
def h_kb(m):
    cats = execute_db("SELECT DISTINCT category FROM knowledge_base", fetch_all=True)
    kb = InlineKeyboardMarkup(row_width=2)
    for c in cats: kb.add(InlineKeyboardButton(f"📁 {c[0]}", callback_data=f"kbcat_{c[0]}"))
    bot.send_message(m.chat.id, "📚 *Knowledge Base*", parse_mode="Markdown", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("kbcat_"))
def kb_cat(c):
    cat = c.data.split("_")[1]
    articles = execute_db("SELECT article_id, title FROM knowledge_base WHERE category=?", (cat,), fetch_all=True)
    kb = InlineKeyboardMarkup()
    for a in articles: kb.add(InlineKeyboardButton(a[1], callback_data=f"kbart_{a[0]}"))
    bot.edit_message_text(f"📚 {cat.capitalize()}", c.message.chat.id, c.message.message_id, reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("kbart_"))
def kb_article(c):
    aid = int(c.data.split("_")[1])
    art = execute_db("SELECT title, content FROM knowledge_base WHERE article_id=?", (aid,), fetch=True)
    execute_db("UPDATE knowledge_base SET views=views+1 WHERE article_id=?", (aid,))
    bot.send_message(c.message.chat.id, f"*{art[0]}*\n\n{art[1]}", parse_mode="Markdown")

# =======================================================================================
# 6. FEATURE: SERVICE FAVORITES (5)
# =======================================================================================
@bot.message_handler(func=lambda m: m.text == "⭐ My Favorites")
def h_favs(m):
    uid = m.from_user.id
    favs = execute_db("SELECT service_id FROM favorites WHERE user_id=?", (uid,), fetch_all=True)
    if not favs: return bot.send_message(m.chat.id, "No favorites yet. Browse services and tap the ⭐ button.")
    kb = InlineKeyboardMarkup(row_width=1)
    for f in favs:
        svc = execute_db("SELECT name, rate, margin FROM managed_services WHERE service_id=?", (f[0],), fetch=True)
        if svc:
            kb.add(InlineKeyboardButton(f"🔥 {svc[0]} - ₹{svc[1]*svc[2]:.2f}/1k", callback_data=f"stats_{f[0]}"))
    bot.send_message(m.chat.id, "⭐ *Your Favorites*", parse_mode="Markdown", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("fav_"))
def toggle_fav(c):
    uid = c.from_user.id
    sid = int(c.data.split("_")[1])
    existing = execute_db("SELECT * FROM favorites WHERE user_id=? AND service_id=?", (uid, sid), fetch=True)
    if existing:
        execute_db("DELETE FROM favorites WHERE user_id=? AND service_id=?", (uid, sid))
        bot.answer_callback_query(c.id, "Removed from favorites.")
    else:
        execute_db("INSERT OR IGNORE INTO favorites (user_id, service_id) VALUES (?,?)", (uid, sid))
        bot.answer_callback_query(c.id, "Added to favorites!")

# =======================================================================================
# 7. BROWSING & ORDERING FLOW (WITH STATS PREVIEW + DELIVERY ESTIMATES)
# =======================================================================================
@bot.message_handler(func=lambda m: m.text == "🛒 Browse Services 🚀")
def h_browse(m):
    cats = execute_db("SELECT DISTINCT category FROM managed_services WHERE disabled=0", fetch_all=True)
    if not cats: return bot.send_message(m.chat.id, "⚠️ Store is empty.")
    kb = InlineKeyboardMarkup(row_width=2)
    for c in cats: kb.add(InlineKeyboardButton(f"📁 {c[0]}", callback_data=f"cat_{c[0]}"))
    bot.send_message(m.chat.id, "🛒 *Select Category:*", parse_mode="Markdown", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("cat_"))
def h_cat(c):
    cat = c.data.split("_")[1]
    svcs = execute_db("SELECT service_id, name, rate, margin FROM managed_services WHERE category=? AND disabled=0", (cat,), fetch_all=True)
    kb = InlineKeyboardMarkup(row_width=1)
    for s in svcs:
        fav = execute_db("SELECT * FROM favorites WHERE user_id=? AND service_id=?", (c.from_user.id, s[0]), fetch=True)
        star = "⭐" if fav else "☆"
        kb.add(InlineKeyboardButton(f"{star} {s[1]} - ₹{s[2]*s[3]:.2f}/1k", callback_data=f"stats_{s[0]}"))
    kb.add(InlineKeyboardButton("🔙 Back to Categories", callback_data="back_browse"))
    bot.edit_message_text(f"📁 *{cat.upper()} SERVICES*", c.message.chat.id, c.message.message_id, parse_mode="Markdown", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("stats_"))
def h_stats(c):
    sid = int(c.data.split("_")[1])
    uid = c.from_user.id
    res = call_api('services')
    try:
        s = next(i for i in res if int(i['service']) == sid)
        db_res = execute_db("SELECT margin, category, success_rate, avg_delivery_minutes FROM managed_services WHERE service_id=?", (sid,), fetch=True)
        m, cat, succ, avg_del = db_res
        # Calculate estimated delivery
        est = f"{avg_del} mins" if avg_del else "N/A"
        msg = f"📊 *SERVICE STATS*\n━━━━━━━━━━━━━━━━━━━\n🏷️ {s['name']}\n🆔 `{sid}`\n💰 Price: `₹{float(s['rate'])*m:.2f}/1k`\n📉 Limits: {s['min']}-{s['max']}\n⭐ Success Rate: {succ}%\n🚚 Avg Delivery: {est}"
        kb = InlineKeyboardMarkup(row_width=2)
        kb.add(InlineKeyboardButton("✅ Order", callback_data=f"buy_{sid}"), InlineKeyboardButton("⭐ Fav", callback_data=f"fav_{sid}"))
        kb.add(InlineKeyboardButton("📋 Add to Template", callback_data=f"tmpl_{sid}"))
        kb.add(InlineKeyboardButton("🔙 Back", callback_data=f"cat_{cat}"), InlineKeyboardButton("❌ Cancel", callback_data="cancel_order"))
        bot.edit_message_text(msg, c.message.chat.id, c.message.message_id, parse_mode="Markdown", reply_markup=kb)
    except: bot.answer_callback_query(c.id, "Error fetching stats.")

# Order flow remains same
@bot.callback_query_handler(func=lambda c: c.data.startswith("buy_"))
def h_buy(c):
    sid = int(c.data.split("_")[1])
    user_states[c.from_user.id] = {"state": "get_link", "sid": sid}
    try: bot.delete_message(c.message.chat.id, c.message.message_id)
    except: pass
    bot.send_message(c.message.chat.id, "🔗 *STEP 1: Send Target Link*", parse_mode="Markdown", reply_markup=cancel_kb())

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get("state") == "get_link")
def h_link(m):
    user_states[m.from_user.id].update({"state": "get_qty", "link": m.text})
    bot.send_message(m.chat.id, "🔢 *STEP 2: Enter Quantity*", parse_mode="Markdown")

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get("state") == "get_qty")
def h_qty(m):
    uid = m.from_user.id
    state = user_states[uid]
    try: qty = int(m.text)
    except: return bot.send_message(m.chat.id, "🤨 Numbers only please.")
    res = call_api('services')
    s_data = next(i for i in res if int(i['service']) == state['sid'])
    if qty < int(s_data['min']) or qty > int(s_data['max']):
        return bot.send_message(m.chat.id, f"🚫 Limits: {s_data['min']} - {s_data['max']}")
    s_db = execute_db("SELECT rate, margin FROM managed_services WHERE service_id=?", (state["sid"],), fetch=True)
    # Smart pricing: check flash sale
    flash_active = execute_db("SELECT value FROM settings WHERE key='flash_sale_active'", fetch=True)[0] == '1'
    flash_mult = float(execute_db("SELECT value FROM settings WHERE key='flash_sale_multiplier'", fetch=True)[0])
    margin = s_db[1] * flash_mult if flash_active else s_db[1]
    cost = (qty / 1000.0) * (s_db[0] * margin)
    u = execute_db("SELECT balance FROM users WHERE user_id=?", (uid,), fetch=True)
    if u[0] < cost: return bot.send_message(m.chat.id, f"❌ You need ₹{cost:.2f}", parse_mode="Markdown", reply_markup=main_kb(uid))
    wait = bot.send_message(m.chat.id, "⏳ Processing...", reply_markup=main_kb(uid))
    api_res = call_api('add', {'service': state["sid"], 'link': state["link"], 'quantity': qty})
    try: bot.delete_message(m.chat.id, wait.message_id)
    except: pass
    if api_res and 'order' in api_res:
        execute_db("UPDATE users SET balance=balance-?, total_spent=total_spent+? WHERE user_id=?", (cost, cost, uid))
        execute_db("INSERT INTO orders (user_id, api_order_id, service_id, quantity, cost) VALUES (?,?,?,?,?)",
                   (uid, api_res['order'], state["sid"], qty, cost))
        # Update service orders count
        execute_db("UPDATE managed_services SET orders_count=orders_count+1 WHERE service_id=?", (state["sid"],))
        bot.send_message(m.chat.id, f"✅ *ORDER PLACED*\n🧾 ID: `{api_res['order']}`\n💰 Cost: ₹{cost:.2f}", parse_mode="Markdown")
        threading.Thread(target=log_order, args=(m.from_user.username, s_data['name'], qty)).start()
    else: bot.send_message(m.chat.id, "❌ Provider Error. Check Link.", parse_mode="Markdown")
    user_states.pop(uid, None)

# =======================================================================================
# 8. FEATURE: ENHANCED COMPARISON (13)
# =======================================================================================
@bot.message_handler(func=lambda m: m.text == "⚖️ Compare Services")
def h_compare_new(m):
    cats = execute_db("SELECT DISTINCT category FROM managed_services WHERE disabled=0", fetch_all=True)
    if not cats: return bot.send_message(m.chat.id, "Store empty.")
    kb = InlineKeyboardMarkup(row_width=2)
    for c in cats: kb.add(InlineKeyboardButton(f"⚖️ {c[0]}", callback_data=f"compcat_{c[0]}"))
    bot.send_message(m.chat.id, "⚖️ *Select category to compare services:*", parse_mode="Markdown", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("compcat_"))
def comp_cat(c):
    cat = c.data.split("_")[1]
    svcs = execute_db("SELECT service_id, name, rate, margin, success_rate, avg_delivery_minutes FROM managed_services WHERE category=? AND disabled=0", (cat,), fetch_all=True)
    if len(svcs) < 2: return bot.answer_callback_query(c.id, "Need at least 2 services to compare.")
    # Show comparison table
    msg = f"⚖️ *{cat.upper()} COMPARISON*\n\n"
    msg += "`{:<25} {:>8} {:>8} {:>8}`\n".format("Service", "Price", "Success", "Speed")
    msg += "`" + "-"*50 + "`\n"
    for s in svcs:
        name = s[1][:20]
        price = f"₹{s[2]*s[3]:.2f}"
        succ = f"{s[4]}%"
        speed = f"{s[5]}m" if s[5] else "N/A"
        msg += f"`{name:<25} {price:>8} {succ:>8} {speed:>8}`\n"
    # Add best value indicator
    best = min(svcs, key=lambda x: x[2]*x[3] / (x[4]*0.01 + 0.1))
    msg += f"\n💡 *Best Value:* {best[1]}"
    kb = InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 Back", callback_data="back_compare"))
    bot.edit_message_text(msg, c.message.chat.id, c.message.message_id, parse_mode="Markdown", reply_markup=kb)

# =======================================================================================
# 9. FEATURE: ORDER TEMPLATES (15)
# =======================================================================================
@bot.message_handler(func=lambda m: m.text == "📋 My Templates")
def h_templates(m):
    uid = m.from_user.id
    temps = execute_db("SELECT template_id, name, service_id, quantity FROM order_templates WHERE user_id=?", (uid,), fetch_all=True)
    if not temps: return bot.send_message(m.chat.id, "You have no saved templates. When viewing a service, use 'Add to Template'.")
    kb = InlineKeyboardMarkup(row_width=1)
    for t in temps:
        svc = execute_db("SELECT name FROM managed_services WHERE service_id=?", (t[2],), fetch=True)
        kb.add(InlineKeyboardButton(f"{t[1]} ({svc[0]}, {t[3]}x)", callback_data=f"usetmpl_{t[0]}"))
    bot.send_message(m.chat.id, "📋 *Your Templates*", parse_mode="Markdown", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("tmpl_"))
def add_template(c):
    uid = c.from_user.id
    sid = int(c.data.split("_")[1])
    user_states[uid] = {"state": "tmpl_name", "sid": sid}
    bot.send_message(c.message.chat.id, "✏️ Enter a name for this template:", reply_markup=cancel_kb())

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get("state") == "tmpl_name")
def tmpl_name(m):
    uid = m.from_user.id
    name = m.text
    sid = user_states[uid]["sid"]
    user_states[uid]["state"] = "tmpl_qty"
    user_states[uid]["name"] = name
    bot.send_message(m.chat.id, "🔢 Enter default quantity:")

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get("state") == "tmpl_qty")
def tmpl_qty(m):
    uid = m.from_user.id
    try: qty = int(m.text)
    except: return bot.send_message(m.chat.id, "Numbers only.")
    name = user_states[uid]["name"]
    sid = user_states[uid]["sid"]
    execute_db("INSERT INTO order_templates (user_id, name, service_id, quantity) VALUES (?,?,?,?)",
               (uid, name, sid, qty))
    bot.send_message(m.chat.id, f"✅ Template '{name}' saved!", reply_markup=main_kb(uid))
    user_states.pop(uid, None)

@bot.callback_query_handler(func=lambda c: c.data.startswith("usetmpl_"))
def use_template(c):
    uid = c.from_user.id
    tid = int(c.data.split("_")[1])
    t = execute_db("SELECT service_id, quantity FROM order_templates WHERE template_id=?", (tid,), fetch=True)
    if not t: return bot.answer_callback_query(c.id, "Template not found.")
    user_states[uid] = {"state": "get_link", "sid": t[0], "qty_preset": t[1]}
    bot.send_message(c.message.chat.id, "🔗 *Send target link (template will use pre-set quantity)*", parse_mode="Markdown", reply_markup=cancel_kb())

# Override link handler to use preset quantity
@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get("state") == "get_link" and 'qty_preset' in user_states.get(m.from_user.id, {}))
def h_link_template(m):
    uid = m.from_user.id
    state = user_states[uid]
    state["link"] = m.text
    state["state"] = "get_qty"
    # Skip asking quantity, use preset
    m.text = str(state["qty_preset"])
    h_qty(m)  # call existing qty handler

# =======================================================================================
# 10. FEATURE: REFERRAL SYSTEM (7)
# =======================================================================================
@bot.message_handler(func=lambda m: m.text == "👥 Referral Program")
def h_referral(m):
    uid = m.from_user.id
    code = execute_db("SELECT referral_code FROM users WHERE user_id=?", (uid,), fetch=True)[0]
    ref_count = execute_db("SELECT COUNT(*) FROM referrals WHERE referrer_id=?", (uid,), fetch=True)[0]
    earnings = execute_db("SELECT COALESCE(SUM(total_earned),0) FROM referrals WHERE referrer_id=?", (uid,), fetch=True)[0]
    link = f"https://t.me/{bot.get_me().username}?start=ref_{code}"
    msg = f"👥 *REFERRAL PROGRAM*\n━━━━━━━━━━━━━━━━━━━\n🔗 Your Link: `{link}`\n👤 Referrals: {ref_count}\n💰 Earned: ₹{earnings:.2f}\n\n💎 *Earn 5% of every deposit your referrals make!*"
    bot.send_message(m.chat.id, msg, parse_mode="Markdown")

# Referral bonus added during deposit approval (see escrow)

# =======================================================================================
# 11. FEATURE: SMART NOTIFICATIONS (17)
# =======================================================================================
def can_notify(uid, notif_type):
    settings = execute_db("SELECT * FROM user_notify_settings WHERE user_id=?", (uid,), fetch=True)
    if not settings: return True  # default allow all
    col = {'order': 1, 'promo': 2, 'tip': 3}
    if notif_type in col and settings[col[notif_type]] == 0: return False
    if settings[4] and settings[5]:
        now = datetime.now().time()
        quiet_start = datetime.strptime(settings[4], "%H:%M").time()
        quiet_end = datetime.strptime(settings[5], "%H:%M").time()
        if quiet_start <= now <= quiet_end: return False
    return True

def send_notification(uid, msg, notif_type='order'):
    if can_notify(uid, notif_type):
        try: bot.send_message(uid, msg, parse_mode="Markdown")
        except: pass

@bot.message_handler(commands=['notify'])
def notify_settings(m):
    uid = m.from_user.id
    settings = execute_db("SELECT * FROM user_notify_settings WHERE user_id=?", (uid,), fetch=True)
    if not settings: execute_db("INSERT INTO user_notify_settings (user_id) VALUES (?)", (uid,))
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("Order Updates: ON" if (not settings or settings[1]) else "Order Updates: OFF", callback_data="tog_order"))
    kb.add(InlineKeyboardButton("Promotions: ON" if (settings and settings[2]) else "Promotions: OFF", callback_data="tog_promo"))
    kb.add(InlineKeyboardButton("Tips: ON" if (settings and settings[3]) else "Tips: OFF", callback_data="tog_tip"))
    kb.add(InlineKeyboardButton("Quiet Hours: Set", callback_data="quiet_set"))
    bot.send_message(m.chat.id, "🔔 *Notification Settings*", parse_mode="Markdown", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("tog_"))
def toggle_notify(c):
    uid = c.from_user.id
    field = c.data.split("_")[1]
    col = {'order':1, 'promo':2, 'tip':3}[field]
    execute_db(f"UPDATE user_notify_settings SET {field}_updates = 1 - {field}_updates WHERE user_id=?", (uid,))
    bot.answer_callback_query(c.id, "Toggled!")

# =======================================================================================
# 12. FEATURE: LIVE ACTIVITY FEED (16)
# =======================================================================================
def get_live_activity():
    # Aggregate recent orders, users online (approximation)
    recent_orders = execute_db("SELECT COUNT(*) FROM orders WHERE placed_time > datetime('now','-1 hour')", fetch=True)[0]
    users_today = execute_db("SELECT COUNT(DISTINCT user_id) FROM orders WHERE placed_time > datetime('now','-1 day')", fetch=True)[0]
    trending_cat = execute_db("""
        SELECT m.category, COUNT(*) as cnt FROM orders o
        JOIN managed_services m ON o.service_id = m.service_id
        WHERE o.placed_time > datetime('now','-1 day')
        GROUP BY m.category ORDER BY cnt DESC LIMIT 1
    """, fetch=True)
    msgs = [
        f"🔥 *Live Activity*",
        f"📦 Orders in last hour: {recent_orders}",
        f"👥 Active users today: {users_today}"
    ]
    if trending_cat: msgs.append(f"📈 Trending: {trending_cat[0]} ({trending_cat[1]} orders)")
    # Random success showcase message
    success = execute_db("SELECT api_order_id, service_id FROM orders WHERE status='Completed' ORDER BY RANDOM() LIMIT 1", fetch=True)
    if success:
        svc_name = execute_db("SELECT name FROM managed_services WHERE service_id=?", (success[1],), fetch=True)
        if svc_name: msgs.append(f"🎉 Delivered: {svc_name[0]} order #{success[0]}")
    return "\n".join(msgs)

@bot.message_handler(func=lambda m: m.text == "🔥 Live Activity")
def h_activity(m):
    bot.send_message(m.chat.id, get_live_activity(), parse_mode="Markdown")

# =======================================================================================
# 13. FEATURE: SUCCESS SHOWCASE (8)
# =======================================================================================
def update_success_feed():
    while True:
        # Keep last 50 messages in activity_feed
        recent = execute_db("SELECT service_id, quantity FROM orders WHERE status='Completed' ORDER BY RANDOM() LIMIT 1", fetch=True)
        if recent:
            svc = execute_db("SELECT name FROM managed_services WHERE service_id=?", (recent[0],), fetch=True)
            if svc:
                msg = f"🎉 {svc[0]} order ({recent[1]}x) completed!"
                execute_db("INSERT INTO activity_feed (message) VALUES (?)", (msg,))
                # Limit feed
                execute_db("DELETE FROM activity_feed WHERE id NOT IN (SELECT id FROM activity_feed ORDER BY id DESC LIMIT 50)")
        time.sleep(random.randint(1800, 3600))  # every 30-60 min

# =======================================================================================
# 14. FEATURE: SMART PRICING ENGINE (10)
# =======================================================================================
def dynamic_pricing_worker():
    while True:
        # Adjust margins based on demand (simplified: if orders > 50 in 3 days, raise margin 5%)
        services = execute_db("SELECT service_id, margin, orders_count FROM managed_services WHERE disabled=0", fetch_all=True)
        for s in services:
            recent_orders = execute_db("SELECT COUNT(*) FROM orders WHERE service_id=? AND placed_time > datetime('now','-3 days')", (s[0],), fetch=True)[0]
            if recent_orders > 30:
                new_margin = min(s[1] + 0.05, 2.5)
                execute_db("UPDATE managed_services SET margin=? WHERE service_id=?", (new_margin, s[0]))
            elif recent_orders < 5:
                new_margin = max(s[1] - 0.03, 1.2)
                execute_db("UPDATE managed_services SET margin=? WHERE service_id=?", (new_margin, s[0]))
        # Flash sale random toggle (admin can manually override)
        time.sleep(3600)

@bot.message_handler(func=lambda m: m.text == "🧪 Flash Sale Toggle" and m.from_user.id == ADMIN_ID)
def flash_toggle(m):
    current = execute_db("SELECT value FROM settings WHERE key='flash_sale_active'", fetch=True)[0]
    new = '1' if current == '0' else '0'
    execute_db("UPDATE settings SET value=? WHERE key='flash_sale_active'", (new,))
    bot.send_message(ADMIN_ID, f"Flash Sale {'ACTIVATED' if new=='1' else 'DEACTIVATED'}")

@bot.message_handler(func=lambda m: m.text == "📊 Smart Pricing" and m.from_user.id == ADMIN_ID)
def smart_pricing_info(m):
    bot.send_message(ADMIN_ID, "Smart pricing auto-adjusts margins based on demand. Use /setflash [multiplier] to set flash sale discount (e.g., 0.8 for 20% off).")

# =======================================================================================
# 15. FEATURE: USER SEGMENTATION (11)
# =======================================================================================
def update_user_segments():
    users = execute_db("SELECT user_id, total_spent, verified FROM users WHERE is_banned=0", fetch_all=True)
    for u in users:
        if u[1] >= 20000: seg = 'diamond'
        elif u[1] >= 5000: seg = 'vip'
        elif u[1] >= 1000: seg = 'active'
        else: seg = 'new'
        # Check dormant
        last_order = execute_db("SELECT MAX(placed_time) FROM orders WHERE user_id=?", (u[0],), fetch=True)[0]
        if last_order:
            last = datetime.strptime(last_order, "%Y-%m-%d %H:%M:%S")
            if (datetime.now() - last).days > 30: seg = 'dormant'
        execute_db("UPDATE users SET segment=? WHERE user_id=?", (seg, u[0]))

def dormant_reactivation():
    while True:
        update_user_segments()
        dormant = execute_db("SELECT user_id FROM users WHERE segment='dormant'", fetch_all=True)
        for d in dormant:
            send_notification(d[0], "💤 We miss you! Come back and get ₹20 bonus on your next deposit. Use code COMEBACK20", 'promo')
        time.sleep(86400)

# =======================================================================================
# 16. ADD FUNDS & REFERRAL BONUS
# =======================================================================================
@bot.message_handler(func=lambda m: m.text == "💳 Add Funds")
def h_add(m):
    user_states[m.from_user.id] = {"state": "fund_amt"}
    bot.send_message(m.chat.id, f"💸 *Enter deposit amount (₹):*\n(Minimum `₹{MIN_DEPOSIT}`)", parse_mode="Markdown", reply_markup=cancel_kb())

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get("state") == "fund_amt")
def h_qr(m):
    try:
        amt = float(m.text)
        if amt < MIN_DEPOSIT: return bot.send_message(m.chat.id, f"🚫 Min `₹{MIN_DEPOSIT}`.")
        user_states[m.from_user.id] = {"state": "fund_ss", "amt": amt}
        bot.send_message(m.chat.id, f"💳 *PAYMENT INSTRUCTIONS*\n1️⃣ Amount: `₹{amt}`\n2️⃣ UPI: `{UPI_ID}`\n📸 *Upload screenshot after payment.*", parse_mode="Markdown", reply_markup=cancel_kb())
        qr = f"https://api.qrserver.com/v1/create-qr-code/?size=400x400&data={urllib.parse.quote(f'upi://pay?pa={UPI_ID}&am={amt}&cu=INR')}"
        response = requests.get(qr, timeout=10)
        img_stream = BytesIO(response.content)
        img_stream.seek(0)
        bot.send_photo(m.chat.id, img_stream, caption="☝️ *Scan to auto-fill the exact amount.*", parse_mode="Markdown")
    except: bot.send_message(m.chat.id, "Numbers only.")

@bot.message_handler(content_types=['photo'])
def h_ss(m):
    uid = m.from_user.id
    if user_states.get(uid, {}).get("state") == "fund_ss":
        amt = user_states[uid]["amt"]
        tx = execute_db("INSERT INTO transactions (user_id, amount, status) VALUES (?, ?, 'PENDING')", (uid, amt), return_id=True)
        kb = InlineKeyboardMarkup().add(InlineKeyboardButton("✅ Apprv", callback_data=f"esc_ap_{tx}_{uid}_{amt}"), InlineKeyboardButton("❌ Rjt", callback_data=f"esc_rj_{tx}_{uid}"))
        bot.send_photo(ADMIN_ID, m.photo[-1].file_id, caption=f"🚨 *DEPOSIT*\n🆔 `{uid}`\n💰 `₹{amt}`\n🧾 `TXN-{tx}`", parse_mode="Markdown", reply_markup=kb)
        bot.send_message(m.chat.id, "⏳ Screenshot sent to Admin. Please wait for approval.", reply_markup=main_kb(uid))
        user_states.pop(uid, None)

@bot.callback_query_handler(func=lambda c: c.data.startswith("esc_"))
def h_escrow(c):
    if c.from_user.id != ADMIN_ID: return
    p = c.data.split("_")
    action, tx, uid = p[1], p[2], p[3]
    if action == "ap":
        amt = float(p[4])
        execute_db("UPDATE users SET balance=balance+? WHERE user_id=?", (amt, uid))
        execute_db("UPDATE transactions SET status='APPROVED' WHERE tx_id=?", (tx,))
        # Referral bonus: find referrer
        referrer = execute_db("SELECT referrer_id FROM users WHERE user_id=?", (uid,), fetch=True)
        if referrer and referrer[0]:
            bonus = amt * 0.05
            execute_db("UPDATE referrals SET total_earned = total_earned + ? WHERE referrer_id=? AND referred_id=?", (bonus, referrer[0], uid))
            execute_db("UPDATE users SET balance=balance+? WHERE user_id=?", (bonus, referrer[0]))
            send_notification(referrer[0], f"🎉 Referral bonus! {uid} deposited ₹{amt}, you earned ₹{bonus:.2f}", 'order')
        bot.edit_message_caption(f"✅ APPROVED TXN-{tx} | Added ₹{amt}", c.message.chat.id, c.message.message_id)
        try: bot.send_message(uid, f"🎉 *APPROVED!* `₹{amt}` added to your wallet.", parse_mode="Markdown")
        except: pass
        # Update user segment
        update_user_segments()
    else:
        execute_db("UPDATE transactions SET status='REJECTED' WHERE tx_id=?", (tx,))
        bot.edit_message_caption(f"❌ REJECTED TXN-{tx}", c.message.chat.id, c.message.message_id)

# =======================================================================================
# 17. AUTO-ORDER STATUS MONITOR (1)
# =======================================================================================
def order_status_monitor():
    while True:
        pending = execute_db("SELECT db_id, api_order_id, user_id, service_id FROM orders WHERE status='pending'", fetch_all=True)
        for o in pending:
            res = call_api('status', {'order': o[1]})
            if not res or 'status' not in res: continue
            new_status = res['status'].capitalize()
            if new_status != 'Pending':
                execute_db("UPDATE orders SET status=?, completed_time=CURRENT_TIMESTAMP WHERE db_id=?", (new_status, o[0]))
                # Update delivery stats
                if new_status == 'Completed':
                    execute_db("INSERT INTO delivery_stats (service_id, delivery_seconds, order_date) SELECT service_id, (julianday(CURRENT_TIMESTAMP) - julianday(placed_time))*86400, date(placed_time) FROM orders WHERE db_id=?", (o[0],))
                    # Update avg delivery time
                    avg = execute_db("SELECT AVG(delivery_seconds) FROM delivery_stats WHERE service_id=?", (o[2],), fetch=True)[0]
                    execute_db("UPDATE managed_services SET avg_delivery_minutes=? WHERE service_id=?", (int(avg/60) if avg else 120, o[2]))
                send_notification(o[2], f"📊 Order #{o[1]} status: *{new_status}*", 'order')
                # Auto-refund on cancel
                if new_status == 'Canceled':
                    cost = execute_db("SELECT cost FROM orders WHERE db_id=?", (o[0],), fetch=True)
                    if cost:
                        execute_db("UPDATE users SET balance=balance+? WHERE user_id=?", (cost[0], o[2]))
                        send_notification(o[2], f"❌ Order #{o[1]} canceled. ₹{cost[0]:.2f} refunded.", 'order')
        time.sleep(120)

# =======================================================================================
# 18. TIP OF THE DAY & KNOWLEDGE BASE
# =======================================================================================
def get_tip_of_the_day():
    tips = [
        "Use our comparison tool to find the best value services.",
        "High retention services cost more but keep followers longer.",
        "Never order more than the service limit.",
        "Save your frequent orders as templates for quick reordering.",
        "Refer friends and earn 5% of their deposits for life!",
        "Check 'Live Activity' to see what others are ordering.",
        "Premium services shown in stats have higher success rates.",
        "Schedule orders during off-peak hours for faster delivery.",
        "Partial orders? Request a refill from Order History.",
        "Keep your balance topped up to avoid missing flash sales."
    ]
    return random.choice(tips)

# =======================================================================================
# 19. STARTUP & THREADS
# =======================================================================================
if __name__ == '__main__':
    init_database()
    try:
        bot.remove_webhook()
        time.sleep(1)
    except: pass

    # Start background threads
    threading.Thread(target=lambda: bot.infinity_polling(skip_pending=True, timeout=60), daemon=True).start()
    threading.Thread(target=order_status_monitor, daemon=True).start()
    threading.Thread(target=dynamic_pricing_worker, daemon=True).start()
    threading.Thread(target=dormant_reactivation, daemon=True).start()
    threading.Thread(target=update_success_feed, daemon=True).start()

    # Self-ping
    def self_ping():
        while True:
            try:
                host = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
                if host: requests.get(f"https://{host}/")
            except: pass
            time.sleep(600)
    threading.Thread(target=self_ping, daemon=True).start()

    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
