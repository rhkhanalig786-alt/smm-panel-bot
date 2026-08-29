"""
=========================================================================================
🔥 SMM PANEL BOT - ENTERPRISE V13 ULTIMATE 🔥
(SMART SYNC + PROFIT MARGINS + GUIDANCE + MULTI-API + AUTO-REFILL + BACKUP)
=========================================================================================
"""

import telebot, requests, sqlite3, logging, time, os, urllib.parse, threading, html
from io import BytesIO
from flask import Flask
from telebot.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton

# =======================================================================================
# 1. CONFIGURATION & SERVER
# =======================================================================================
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

BOT_TOKEN = os.environ.get('BOT_TOKEN', '8228287584:AAEmRoy0ady5zOSkdN-AGpDch7cOLYYde64')
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
MIN_DEPOSIT = 10.0

user_states = {}
db_lock = threading.Lock()

app = Flask(__name__)
@app.route('/')
def home(): return "🔥 SMM V13 ENTERPRISE ONLINE 🔥"

# =======================================================================================
# 2. DATABASE ENGINE
# =======================================================================================
def execute_db(query, params=(), fetch=False, fetch_all=False, return_id=False):
    with db_lock:
        try:
            with sqlite3.connect('panel_v13.db', check_same_thread=False, timeout=20) as conn:
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
            service_id INTEGER, quantity INTEGER, cost REAL, status TEXT DEFAULT 'pending',
            auto_refill INTEGER DEFAULT 1, last_refill_check TIMESTAMP DEFAULT CURRENT_TIMESTAMP, placed_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS managed_services (
            service_id INTEGER PRIMARY KEY, category TEXT, name TEXT, provider TEXT DEFAULT 'provider_primary',
            provider_service_id INTEGER, rate REAL, min_qty INTEGER DEFAULT 10, max_qty INTEGER DEFAULT 100000,
            margin REAL DEFAULT 1.50, disabled INTEGER DEFAULT 0
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
# 3. API UTILITIES
# =======================================================================================
def call_provider_api(provider_name, action, extra=None):
    prov = PROVIDERS.get(provider_name, PROVIDERS["provider_primary"])
    payload = {'key': prov['key'], 'action': action}
    if extra: payload.update(extra)
    try: return requests.post(prov['url'], data=payload, timeout=15).json(), provider_name
    except: return None, provider_name

def get_best_provider_for_service(service_id):
    svc = execute_db("SELECT provider, provider_service_id, rate, margin FROM managed_services WHERE service_id=?", (service_id,), fetch=True)
    if svc: return svc[0], svc[1], svc[2], svc[3]
    return "provider_primary", service_id, 10.0, 1.50

# =======================================================================================
# 4. KEYBOARDS
# =======================================================================================
def main_kb(uid):
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add("🛒 Browse Services", "🎁 Claim Free 1K Views")
    kb.add("💰 My Profile", "💳 Add Funds")
    kb.add("📦 Order History", "👥 Referral Program")
    kb.add("📞 Support")
    if uid == ADMIN_ID:
        kb.add("🧠 Admin: Smart Sync", "📈 Admin: Margin")
        kb.add("🎟️ Admin: Tickets", "📢 Admin: Broadcast")
        kb.add("💾 Admin: Backup DB", "🔄 Admin: Restore DB")
    return kb

def cancel_kb(): return ReplyKeyboardMarkup(resize_keyboard=True).add("❌ Cancel")

# =======================================================================================
# 5. USER INTERFACE & GUIDANCE HANDLERS
# =======================================================================================
@bot.message_handler(commands=['start'])
def h_start(m):
    uid = m.from_user.id
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
            try: bot.send_message(referrer_id, "🎉 <b>A friend joined!</b>\n🎁 <b>You received +1 Free 1K Views Credit!</b>", parse_mode="HTML")
            except: pass

    safe_name = html.escape(m.from_user.first_name or "User")
    msg = (
        f"👋 Welcome to the Ultimate SMM Panel, <b>{safe_name}</b>! 🚀\n\n"
        f"I am your automated growth assistant. I help you safely and quickly boost your social media presence! 📈\n\n"
        f"👇 <b>HOW TO USE ME:</b>\n"
        f"1️⃣ Tap <b>'💳 Add Funds'</b> to top up your wallet.\n"
        f"2️⃣ Tap <b>'🛒 Browse Services'</b> to select what you want to grow.\n"
        f"3️⃣ Paste your post link, type the quantity, and watch the magic happen!\n\n"
        f"<i>Start exploring using the buttons below!</i>"
    )
    bot.send_message(m.chat.id, msg, parse_mode="HTML", reply_markup=main_kb(uid))

@bot.message_handler(func=lambda m: m.text == "❌ Cancel")
def h_cancel(m):
    user_states.pop(m.from_user.id, None)
    bot.send_message(m.chat.id, "🚫 <b>Action Cancelled!</b>\n\n🏠 <i>You are back at the main menu.</i>", parse_mode="HTML", reply_markup=main_kb(m.from_user.id))

@bot.message_handler(func=lambda m: m.text == "💰 My Profile")
def h_profile(m):
    u = execute_db("SELECT balance, total_spent, free_views_credits, referral_code FROM users WHERE user_id=?", (m.from_user.id,), fetch=True)
    if not u: return
    ref_count = execute_db("SELECT COUNT(*) FROM referrals WHERE referrer_id=?", (m.from_user.id,), fetch=True)[0]
    msg = (
        f"👤 <b>YOUR PROFILE & STATS</b> 📊\n━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 <b>Account ID:</b> <code>{m.from_user.id}</code>\n"
        f"💰 <b>Wallet Balance:</b> <code>₹{u[0]:.2f}</code>\n"
        f"📈 <b>Total Spent:</b> <code>₹{u[1]:.2f}</code>\n"
        f"🎁 <b>Free Views Credits:</b> <code>{u[2]}</code>\n"
        f"👥 <b>Total Referrals:</b> <code>{ref_count}</code>\n\n"
        f"💡 <i>Tip: Need more balance? Tap '💳 Add Funds' below!</i>"
    )
    bot.send_message(m.chat.id, msg, parse_mode="HTML")

# =======================================================================================
# 6. ADMIN: SMART SYNC & MARGIN ADJUSTMENT
# =======================================================================================
@bot.message_handler(func=lambda m: m.text == "🧠 Admin: Smart Sync" and m.from_user.id == ADMIN_ID)
def h_admin_smart_sync(m):
    bot.send_message(ADMIN_ID, "🧠 <i>Initializing Smart Sync... Scanning provider for best prices and high-quality services...</i>", parse_mode="HTML")
    res, _ = call_provider_api("provider_primary", "services")
    if not res or not isinstance(res, list): return bot.send_message(ADMIN_ID, "❌ Failed to fetch services from API.")
    
    execute_db("DELETE FROM managed_services") # Clear old clutter
    margin = float(execute_db("SELECT value FROM settings WHERE key='global_margin'", fetch=True)[0])
    
    # Group services by broad categories
    categories = {}
    for s in res:
        cat_name = s.get('category', 'Other')
        if cat_name not in categories: categories[cat_name] = []
        categories[cat_name].append(s)
        
    added_count = 0
    for cat_name, svcs in categories.items():
        cat_lower = cat_name.lower()
        
        # Scenario A: Likes, Views, Shares, Reposts -> Find the absolute CHEAPEST
        if any(x in cat_lower for x in ['like', 'view', 'share', 'repost', 'story']):
            svcs.sort(key=lambda x: float(x.get('rate', 9999)))
            best_svcs = svcs[:2] # Pick top 2 cheapest
            
        # Scenario B: Followers, Subscribers -> Find QUALITY (Refill/Guaranteed)
        elif any(x in cat_lower for x in ['follower', 'subscriber', 'member']):
            quality_svcs = [x for x in svcs if 'refill' in x.get('name', '').lower() or 'guarantee' in x.get('name', '').lower() or 'hq' in x.get('name', '').lower()]
            if not quality_svcs: quality_svcs = svcs # Fallback
            quality_svcs.sort(key=lambda x: float(x.get('rate', 0)), reverse=True) # Sort highest to lowest to weed out cheap drop services
            best_svcs = quality_svcs[-3:] # Take the 3 most reasonable high-quality ones
            
        else:
            # For everything else, grab the cheapest one
            svcs.sort(key=lambda x: float(x.get('rate', 9999)))
            best_svcs = svcs[:1]
            
        for s in best_svcs:
            try:
                execute_db("""INSERT OR REPLACE INTO managed_services 
                    (service_id, category, name, provider, provider_service_id, rate, min_qty, max_qty, margin, disabled) 
                    VALUES (?, ?, ?, 'provider_primary', ?, ?, ?, ?, ?, 0)""",
                    (int(s['service']), cat_name, s['name'], int(s['service']), float(s['rate']), int(s['min']), int(s['max']), margin))
                added_count += 1
            except: continue

    bot.send_message(ADMIN_ID, f"✅ <b>SMART SYNC COMPLETE!</b>\nCleaned up clutter. Added <b>{added_count}</b> highly curated services (Cheapest for views/likes, High Quality for Followers).", parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text == "📈 Admin: Margin" and m.from_user.id == ADMIN_ID)
def h_admin_margin(m):
    user_states[ADMIN_ID] = {"state": "wait_margin"}
    bot.send_message(ADMIN_ID, "📈 <b>ADJUST PROFIT MARGIN</b>\n\nEnter the profit percentage you want to make on all services.\n<i>Example: Type <b>50</b> to add 50% profit to provider base prices.</i>", parse_mode="HTML", reply_markup=cancel_kb())

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get("state") == "wait_margin" and m.from_user.id == ADMIN_ID)
def h_process_margin(m):
    try:
        profit_percent = float(m.text)
        multiplier = 1.0 + (profit_percent / 100.0)
        execute_db("UPDATE settings SET value=? WHERE key='global_margin'", (str(multiplier),))
        execute_db("UPDATE managed_services SET margin=?", (multiplier,))
        bot.send_message(ADMIN_ID, f"✅ <b>MARGIN UPDATED!</b>\nAll service prices have been marked up by {profit_percent}%.", parse_mode="HTML", reply_markup=main_kb(ADMIN_ID))
    except: bot.send_message(ADMIN_ID, "❌ Invalid number. Please enter a simple number like 20, 50, or 100.")
    user_states.pop(ADMIN_ID, None)

# =======================================================================================
# 7. BROWSING & ORDERING
# =======================================================================================
@bot.message_handler(func=lambda m: m.text == "🛒 Browse Services")
def h_browse(m):
    cats = execute_db("SELECT DISTINCT category FROM managed_services WHERE disabled=0", fetch_all=True)
    if not cats: return bot.send_message(m.chat.id, "⚠️ <b>No services available yet.</b> Check back soon!", parse_mode="HTML")
    kb = InlineKeyboardMarkup(row_width=2)
    for c in cats: kb.add(InlineKeyboardButton(f"📁 {c[0]}", callback_data=f"cat_{c[0]}"))
    msg = f"🛒 <b>LET'S FIND WHAT YOU NEED!</b>\n\n👇 <i>Tap on any category folder below to explore our curated services.</i>"
    bot.send_message(m.chat.id, msg, parse_mode="HTML", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("cat_"))
def h_cat_view(c):
    cat = c.data.split("_")[1]
    svcs = execute_db("SELECT service_id, name, rate, margin FROM managed_services WHERE category=? AND disabled=0", (cat,), fetch_all=True)
    kb = InlineKeyboardMarkup(row_width=1)
    for s in svcs: kb.add(InlineKeyboardButton(f"⭐ {s[1]} - ₹{s[2]*s[3]:.2f}/1k", callback_data=f"buyinit_{s[0]}"))
    msg = f"📂 <b>{html.escape(cat.upper())}</b>\n\nPrices shown are per 1,000 quantity.\n👇 <i>Tap a service to place your order!</i>"
    bot.edit_message_text(msg, c.message.chat.id, c.message.message_id, parse_mode="HTML", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("buyinit_"))
def h_buyinit(c):
    sid = int(c.data.split("_")[1])
    user_states[c.from_user.id] = {"state": "get_link", "sid": sid}
    msg = f"🚀 <b>AWESOME CHOICE!</b>\n\n🔗 <b>STEP 1: Send the Target Link</b>\n\n💡 <i>Tip: Just paste the URL (link to the post/profile) below and hit send. Make sure the account is PUBLIC!</i>"
    bot.send_message(c.message.chat.id, msg, parse_mode="HTML", reply_markup=cancel_kb())

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get("state") == "get_link")
def h_link_input(m):
    user_states[m.from_user.id].update({"state": "get_qty", "link": m.text.strip()})
    msg = f"✅ <b>Link Received!</b>\n\n🔢 <b>STEP 2: Enter the Quantity</b>\n\n💡 <i>Tip: Type a simple number (e.g., 500, 1000) and press send!</i>"
    bot.send_message(m.chat.id, msg, parse_mode="HTML")

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get("state") == "get_qty")
def h_qty_input(m):
    uid = m.from_user.id
    state = user_states[uid]
    try: qty = int(m.text)
    except: return bot.send_message(m.chat.id, "❌ <b>Oops! Please type a valid NUMBER only.</b>", parse_mode="HTML")

    prov_name, prov_sid, rate, margin = get_best_provider_for_service(state["sid"])
    cost = (qty / 1000.0) * (rate * margin)

    u_bal = execute_db("SELECT balance FROM users WHERE user_id=?", (uid,), fetch=True)[0]
    if u_bal < cost: 
        return bot.send_message(m.chat.id, f"❌ <b>INSUFFICIENT BALANCE!</b>\nYou need <code>₹{cost:.2f}</code> but your balance is <code>₹{u_bal:.2f}</code>.\n\n👇 <i>Tap '💳 Add Funds' below to top up!</i>", parse_mode="HTML", reply_markup=main_kb(uid))

    bot.send_message(m.chat.id, "⏳ <i>Processing your order securely...</i>", parse_mode="HTML")
    api_res, prov_used = call_provider_api(prov_name, 'add', {'service': prov_sid, 'link': state['link'], 'quantity': qty})
    
    if api_res and 'order' in api_res:
        execute_db("UPDATE users SET balance=balance-?, total_spent=total_spent+? WHERE user_id=?", (cost, cost, uid))
        execute_db("INSERT INTO orders (user_id, provider, api_order_id, service_id, quantity, cost, auto_refill) VALUES (?,?,?,?,?,?,1)",
                   (uid, prov_used, api_res['order'], state["sid"], qty, cost))
        msg = f"✅ <b>ORDER SUCCESSFULLY PLACED!</b> 🎉\n━━━━━━━━━━━━━━━━━━━\n🧾 <b>Order ID:</b> <code>{api_res['order']}</code>\n💰 <b>Cost:</b> ₹{cost:.2f}\n♻️ <b>Auto-Refill:</b> Enabled\n\n<i>Track this in the '📦 Order History' tab!</i>"
        bot.send_message(m.chat.id, msg, parse_mode="HTML", reply_markup=main_kb(uid))
    else: bot.send_message(m.chat.id, "❌ <b>Provider Error!</b> The service might be busy. No money was deducted. Please try another service.", parse_mode="HTML", reply_markup=main_kb(uid))
    user_states.pop(uid, None)

# =======================================================================================
# 8. BACKGROUND TASKS
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
        except: pass
        time.sleep(300)

if __name__ == '__main__':
    init_database()
    try: bot.remove_webhook(); time.sleep(1)
    except: pass
    threading.Thread(target=lambda: bot.infinity_polling(skip_pending=True, timeout=60), daemon=True).start()
    threading.Thread(target=auto_refill_and_status_monitor, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
