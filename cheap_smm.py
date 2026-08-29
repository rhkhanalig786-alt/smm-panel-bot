"""
=========================================================================================
🔥 SMM PANEL BOT - ENTERPRISE V12 ULTIMATE 🔥
(INLINE GUIDANCE + MULTI-API + AUTO-REFILL + BACKUP + FREE REWARDS)
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

BOT_TOKEN = os.environ.get('BOT_TOKEN', '8228287584:AAGyG3Gv7uA6CLr2w62uf2yWlCMHgfTAwXY')
bot = telebot.TeleBot(BOT_TOKEN, threaded=True, num_threads=10)

PROVIDERS = {
    "provider_primary": {
        "url": os.environ.get("API_URL_1", "https://iggrowbot.com/api/v2"),
        "key": os.environ.get("API_KEY_1", "c1ff6a119106be59dab2829144bc413a")
    },
    "provider_secondary": {
        "url": os.environ.get("API_URL_2", "https://indiansmmprovider.in/api/v2"), 
        "key": os.environ.get("API_KEY_2", "SECONDARY_API_KEY_HERE")
    }
}

FREE_VIEWS_SERVICE_ID = int(os.environ.get('FREE_VIEWS_SERVICE_ID', 101))
FREE_VIEWS_PROVIDER = "provider_primary"

ADMIN_ID = 6034840006
UPI_ID = "rahikhann@fam"
SUPPORT_USERNAME = "@itzdevrahi"
CHANNEL_ID = "@cspnotice"
MIN_DEPOSIT = 10.0

user_states = {}
db_lock = threading.Lock()

app = Flask(__name__)
@app.route('/')
def home():
    return "🔥 SMM V12 ENTERPRISE ONLINE 🔥"

# =======================================================================================
# 2. DATABASE ENGINE
# =======================================================================================
def execute_db(query, params=(), fetch=False, fetch_all=False, return_id=False):
    with db_lock:
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
            margin REAL DEFAULT 1.45, disabled INTEGER DEFAULT 0
        )""",
        "CREATE TABLE IF NOT EXISTS transactions (tx_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount REAL, status TEXT, date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
        "CREATE TABLE IF NOT EXISTS tickets (ticket_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, message TEXT, status TEXT DEFAULT 'OPEN', reply TEXT)",
        "CREATE TABLE IF NOT EXISTS referrals (referrer_id INTEGER, referred_id INTEGER, reward_claimed INTEGER DEFAULT 1, PRIMARY KEY(referrer_id, referred_id))",
        "CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)"
    ]
    for table in tables: execute_db(table)
    if not execute_db("SELECT value FROM settings WHERE key='global_margin'", fetch=True):
        execute_db("INSERT INTO settings (key, value) VALUES ('global_margin', '1.45')")

# =======================================================================================
# 3. API & HELPER UTILITIES
# =======================================================================================
def call_provider_api(provider_name, action, extra=None):
    prov = PROVIDERS.get(provider_name)
    if not prov or not prov.get("key") or "HERE" in prov.get("key"):
        prov = PROVIDERS["provider_primary"]
        provider_name = "provider_primary"
    payload = {'key': prov['key'], 'action': action}
    if extra: payload.update(extra)
    try: return requests.post(prov['url'], data=payload, timeout=15).json(), provider_name
    except Exception as e:
        logging.error(f"API Error ({provider_name}): {e}")
        return None, provider_name

def get_best_provider_for_service(service_id):
    svc = execute_db("SELECT provider, provider_service_id, rate, margin FROM managed_services WHERE service_id=?", (service_id,), fetch=True)
    if svc and svc[0] in PROVIDERS: return svc[0], svc[1], svc[2], svc[3]
    return "provider_primary", service_id, 10.0, 1.45

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
        kb.add("👑 Admin: Sync Services", "📢 Admin: Broadcast")
        kb.add("🎟️ Admin: Tickets")
        kb.add("💾 Admin: Backup DB", "🔄 Admin: Restore DB")
    return kb

def cancel_kb(): return ReplyKeyboardMarkup(resize_keyboard=True).add("❌ Cancel")

# =======================================================================================
# 5. CORE USER & NAVIGATION HANDLERS (GUIDED RESPONSES)
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
                potential_ref = int(args[1].replace('ref_', ''))
                if potential_ref != uid: referrer_id = potential_ref
            except: pass
        ref_code = f"REF{uid}"
        execute_db("INSERT INTO users (user_id, username, first_name, referrer_id, referral_code) VALUES (?,?,?,?,?)",
                   (uid, m.from_user.username, m.from_user.first_name, referrer_id, ref_code))
        if referrer_id:
            execute_db("INSERT OR IGNORE INTO referrals (referrer_id, referred_id) VALUES (?,?)", (referrer_id, uid))
            execute_db("UPDATE users SET free_views_credits = free_views_credits + 1 WHERE user_id=?", (referrer_id,))
            try: bot.send_message(referrer_id, f"🎉 <b>Amazing! A friend joined using your link!</b>\n🎁 <b>You received +1 Free 1K Views Credit!</b>", parse_mode="HTML")
            except: pass

    safe_name = html.escape(m.from_user.first_name or "User")
    msg = (
        f"👋 Welcome to the Panel, <b>{safe_name}</b>! 🚀\n\n"
        f"I am your automated Social Media Growth Assistant. I can help you boost your followers, likes, and views instantly! 📈\n\n"
        f"👇 <b>HOW TO START:</b>\n"
        f"Use the menu buttons below to navigate. Try tapping <b>'🛒 Browse Services'</b> to see what we offer!"
    )
    bot.send_message(m.chat.id, msg, parse_mode="HTML", reply_markup=main_kb(uid))

@bot.message_handler(func=lambda m: m.text == "❌ Cancel")
def h_cancel(m):
    user_states.pop(m.from_user.id, None)
    bot.send_message(m.chat.id, "🚫 <b>Action Cancelled!</b>\n\n🏠 <i>You are back at the main menu. What would you like to do next?</i>", parse_mode="HTML", reply_markup=main_kb(m.from_user.id))

@bot.message_handler(func=lambda m: m.text == "💰 My Profile")
def h_profile(m):
    uid = m.from_user.id
    u = execute_db("SELECT balance, total_spent, free_views_credits, referral_code FROM users WHERE user_id=?", (uid,), fetch=True)
    if not u: return
    ref_count = execute_db("SELECT COUNT(*) FROM referrals WHERE referrer_id=?", (uid,), fetch=True)[0]
    
    msg = (
        f"👤 <b>YOUR PROFILE & STATS</b> 📊\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 <b>Account ID:</b> <code>{uid}</code>\n"
        f"💰 <b>Wallet Balance:</b> <code>₹{u[0]:.2f}</code>\n"
        f"📈 <b>Total Spent:</b> <code>₹{u[1]:.2f}</code>\n"
        f"🎁 <b>Free 1K Views Credits:</b> <code>{u[2]}</code>\n"
        f"👥 <b>Friends Referred:</b> <code>{ref_count}</code>\n\n"
        f"💡 <b>Tip:</b> <i>Need more balance? Tap <b>'💳 Add Funds'</b> in the menu below!</i>"
    )
    bot.send_message(m.chat.id, msg, parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text == "📦 Order History")
def h_order_history(m):
    uid = m.from_user.id
    orders = execute_db("SELECT api_order_id, service_id, quantity, cost, status FROM orders WHERE user_id=? ORDER BY placed_time DESC LIMIT 5", (uid,), fetch_all=True)
    if not orders:
        return bot.send_message(m.chat.id, "📦 <b>No Orders Yet!</b>\n\n🛒 <i>Tap 'Browse Services' to place your first order.</i>", parse_mode="HTML")
    
    msg = "📦 <b>YOUR RECENT ORDERS:</b>\n━━━━━━━━━━━━━━━━━━━\n"
    for o in orders:
        msg += f"🧾 <b>Order ID:</b> <code>{o[0]}</code>\n🔢 <b>Qty:</b> {o[2]} | 💰 <b>Cost:</b> ₹{o[3]:.2f}\n📊 <b>Status:</b> <code>{o[4]}</code>\n───────────────────\n"
    msg += "\n💡 <b>Tip:</b> <i>Order status updates automatically. 'Pending' means it's in queue!</i>"
    bot.send_message(m.chat.id, msg, parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text == "📞 Support")
def h_support(m):
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("💬 Message Owner Directly", url=f"https://t.me/{SUPPORT_USERNAME.replace('@','')}"),
        InlineKeyboardButton("🎟️ Create Support Ticket", callback_data="make_ticket")
    )
    bot.send_message(m.chat.id, "📞 <b>CUSTOMER SUPPORT</b> 🛠️\n\nGot a question or an issue with an order? We are here to help!\n\n👇 <i>Choose an option below to contact us:</i>", parse_mode="HTML", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data == "make_ticket")
def h_ticket_init(c):
    user_states[c.from_user.id] = {"state": "waiting_ticket_text"}
    bot.send_message(c.message.chat.id, "📝 <b>CREATE TICKET</b>\n\n👇 <i>Please type your issue or question below and press send. Be as detailed as possible!</i>", parse_mode="HTML", reply_markup=cancel_kb())

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get("state") == "waiting_ticket_text")
def h_ticket_save(m):
    uid = m.from_user.id
    tid = execute_db("INSERT INTO tickets (user_id, message) VALUES (?,?)", (uid, m.text), return_id=True)
    user_states.pop(uid, None)
    bot.send_message(m.chat.id, f"✅ <b>Ticket #{tid} Submitted successfully!</b> 📨\n\n⏳ <i>Our admin team will review this and get back to you soon.</i>", parse_mode="HTML", reply_markup=main_kb(uid))
    try: bot.send_message(ADMIN_ID, f"🚨 <b>NEW TICKET #{tid}</b>\nFrom <code>{uid}</code>:\n\n{m.text}", parse_mode="HTML")
    except: pass

@bot.message_handler(func=lambda m: m.text == "👥 Referral Program")
def h_referral(m):
    uid = m.from_user.id
    u = execute_db("SELECT free_views_credits FROM users WHERE user_id=?", (uid,), fetch=True)
    ref_count = execute_db("SELECT COUNT(*) FROM referrals WHERE referrer_id=?", (uid,), fetch=True)[0]
    link = f"https://t.me/{bot.get_me().username}?start=ref_{uid}"
    
    msg = (
        f"👥 <b>REFERRAL REWARDS PROGRAM</b> 🎁\n━━━━━━━━━━━━━━━━━━━\n"
        f"Want free services? Invite your friends!\n\n"
        f"🔗 <b>Copy & Share Your Link:</b>\n<code>{link}</code>\n\n"
        f"👤 <b>Friends Joined:</b> <code>{ref_count}</code>\n"
        f"🎁 <b>Free 1K Views Credits Earned:</b> <code>{u[0]}</code>\n\n"
        f"🚀 <b>HOW IT WORKS:</b>\n"
        f"<i>Every time someone starts the bot using your link, you instantly get a credit for 1,000 Free Views! Tap 'Claim Free 1K Views' in the menu to use them!</i>"
    )
    bot.send_message(m.chat.id, msg, parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text == "🎁 Claim Free 1K Views")
def h_claim_free(m):
    uid = m.from_user.id
    credits = execute_db("SELECT free_views_credits FROM users WHERE user_id=?", (uid,), fetch=True)[0]
    if credits <= 0:
        return bot.send_message(m.chat.id, "❌ <b>You have 0 Free Credits!</b> 😔\n\n👥 <i>Share your link from the 'Referral Program' menu with your friends to earn free views!</i>", parse_mode="HTML")
    user_states[uid] = {"state": "claim_free_link"}
    bot.send_message(m.chat.id, f"🎁 <b>Awesome! You have {credits} free credit(s)!</b>\n\n🔗 <b>STEP 1:</b> <i>Send the link to the post/video where you want to send your 1,000 free views!</i>\n\n⚠️ (Make sure the account is public!)", parse_mode="HTML", reply_markup=cancel_kb())

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get("state") == "claim_free_link")
def h_process_free_claim(m):
    uid = m.from_user.id
    credits = execute_db("SELECT free_views_credits FROM users WHERE user_id=?", (uid,), fetch=True)[0]
    if credits <= 0: return bot.send_message(m.chat.id, "❌ No credits remaining.", reply_markup=main_kb(uid))
    bot.send_message(m.chat.id, "⏳ <i>Processing your free reward...</i>", parse_mode="HTML")
    api_res, prov_used = call_provider_api(FREE_VIEWS_PROVIDER, 'add', {'service': FREE_VIEWS_SERVICE_ID, 'link': m.text.strip(), 'quantity': 1000})
    if api_res and 'order' in api_res:
        execute_db("UPDATE users SET free_views_credits = free_views_credits - 1 WHERE user_id=?", (uid,))
        execute_db("INSERT INTO orders (user_id, provider, api_order_id, service_id, quantity, cost, auto_refill) VALUES (?,?,?,?,?,?,?)",
                   (uid, prov_used, api_res['order'], FREE_VIEWS_SERVICE_ID, 1000, 0.0, 0))
        bot.send_message(m.chat.id, f"✅ <b>SUCCESS! 1,000 FREE VIEWS ORDERED!</b> 🎉\n\n🧾 Order ID: <code>{api_res['order']}</code>\n🎁 Credits left: <code>{credits-1}</code>\n\n<i>Your views will start delivering shortly!</i>", parse_mode="HTML", reply_markup=main_kb(uid))
    else: bot.send_message(m.chat.id, "❌ <b>Oops! Something went wrong.</b>\n<i>Please check if your link is correct and public, then try again.</i>", parse_mode="HTML", reply_markup=main_kb(uid))
    user_states.pop(uid, None)

# =======================================================================================
# 6. ADMIN OPERATIONS
# =======================================================================================
@bot.message_handler(func=lambda m: m.text == "👑 Admin: Sync Services" and m.from_user.id == ADMIN_ID)
def h_admin_sync(m):
    bot.send_message(ADMIN_ID, "⏳ Fetching and syncing services from Provider API...")
    res, _ = call_provider_api("provider_primary", "services")
    if not res or not isinstance(res, list): return bot.send_message(ADMIN_ID, "❌ Failed to fetch services from API.")
    count = 0
    margin = float(execute_db("SELECT value FROM settings WHERE key='global_margin'", fetch=True)[0])
    for s in res:
        try:
            sid, cat, name, rate, min_q, max_q = int(s['service']), s.get('category', 'General'), s.get('name', 'Service'), float(s.get('rate', 10.0)), int(s.get('min', 10)), int(s.get('max', 100000))
            execute_db("""INSERT OR REPLACE INTO managed_services 
                (service_id, category, name, provider, provider_service_id, rate, min_qty, max_qty, margin, disabled) 
                VALUES (?, ?, ?, 'provider_primary', ?, ?, ?, ?, ?, 0)""",
                (sid, cat, name, sid, rate, min_q, max_q, margin))
            count += 1
        except: continue
    bot.send_message(ADMIN_ID, f"✅ Successfully synced <b>{count}</b> services!", parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text == "📢 Admin: Broadcast" and m.from_user.id == ADMIN_ID)
def h_admin_broadcast(m):
    user_states[ADMIN_ID] = {"state": "wait_broadcast"}
    bot.send_message(ADMIN_ID, "📢 Send the message you want to broadcast to all users:", reply_markup=cancel_kb())

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get("state") == "wait_broadcast" and m.from_user.id == ADMIN_ID)
def h_process_broadcast(m):
    users = execute_db("SELECT user_id FROM users WHERE is_banned=0", fetch_all=True)
    sent, failed = 0, 0
    for u in users:
        try: bot.send_message(u[0], f"📢 <b>ANNOUNCEMENT:</b>\n\n{m.text}", parse_mode="HTML"); sent += 1
        except: failed += 1
    user_states.pop(ADMIN_ID, None)
    bot.send_message(ADMIN_ID, f"✅ Broadcast sent to {sent} users ({failed} failed).", reply_markup=main_kb(ADMIN_ID))

@bot.message_handler(func=lambda m: m.text == "🎟️ Admin: Tickets" and m.from_user.id == ADMIN_ID)
def h_admin_view_tickets(m):
    tickets = execute_db("SELECT ticket_id, user_id, message FROM tickets WHERE status='OPEN' LIMIT 5", fetch_all=True)
    if not tickets: return bot.send_message(ADMIN_ID, "✅ No open tickets.")
    for t in tickets: bot.send_message(ADMIN_ID, f"🎟️ <b>Ticket #{t[0]}</b> from <code>{t[1]}</code>:\n{t[2]}", parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text == "💾 Admin: Backup DB" and m.from_user.id == ADMIN_ID)
def handle_admin_backup(m):
    uid = m.from_user.id
    bot.send_message(uid, "⏳ <i>Generating live database snapshot...</i>", parse_mode="HTML")
    backup_file = f"backup_{int(time.time())}.db"
    try:
        with db_lock:
            with sqlite3.connect('panel_v12.db') as src, sqlite3.connect(backup_file) as dst: src.backup(dst)
        with open(backup_file, 'rb') as doc:
            bot.send_document(uid, doc, caption=f"💾 <b>Database Backup</b>\n📅 <code>{time.strftime('%Y-%m-%d %H:%M:%S')}</code>", parse_mode="HTML")
    except Exception as e: bot.send_message(uid, f"❌ Backup Failed: <code>{e}</code>", parse_mode="HTML")
    finally:
        if os.path.exists(backup_file): os.remove(backup_file)

@bot.message_handler(func=lambda m: m.text == "🔄 Admin: Restore DB" and m.from_user.id == ADMIN_ID)
def handle_admin_restore_prompt(m):
    user_states[ADMIN_ID] = {"state": "wait_for_db_upload"}
    bot.send_message(ADMIN_ID, "⚠️ <b>DATABASE RESTORE</b>\n\nUpload your <code>.db</code> file as a document.", parse_mode="HTML", reply_markup=cancel_kb())

@bot.message_handler(content_types=['document'])
def handle_document_upload(m):
    uid = m.from_user.id
    if uid == ADMIN_ID and user_states.get(uid, {}).get("state") == "wait_for_db_upload":
        if not m.document.file_name.endswith('.db'): return bot.send_message(uid, "❌ Please upload a valid .db file.", reply_markup=main_kb(uid))
        bot.send_message(uid, "⏳ Restoring database...")
        temp_file = f"restore_{int(time.time())}.db"
        try:
            downloaded_file = bot.download_file(bot.get_file(m.document.file_id).file_path)
            with open(temp_file, 'wb') as f: f.write(downloaded_file)
            with db_lock:
                with sqlite3.connect(temp_file) as src, sqlite3.connect('panel_v12.db') as dst: src.backup(dst)
            bot.send_message(uid, "✅ <b>Database Restored Successfully!</b>", parse_mode="HTML", reply_markup=main_kb(uid))
        except Exception as e: bot.send_message(uid, f"❌ Restore Failed: {e}", reply_markup=main_kb(uid))
        finally:
            user_states.pop(uid, None)
            if os.path.exists(temp_file): os.remove(temp_file)

# =======================================================================================
# 7. BROWSING & ORDERING FLOW (GUIDED INSTRUCTIONS)
# =======================================================================================
@bot.message_handler(func=lambda m: m.text == "🛒 Browse Services")
def h_browse(m):
    cats = execute_db("SELECT DISTINCT category FROM managed_services WHERE disabled=0", fetch_all=True)
    if not cats: return bot.send_message(m.chat.id, "⚠️ <b>No services available yet.</b> Check back soon!", parse_mode="HTML")
    kb = InlineKeyboardMarkup(row_width=2)
    for c in cats: kb.add(InlineKeyboardButton(f"📁 {c[0]}", callback_data=f"cat_{c[0]}"))
    
    msg = (
        f"🛒 <b>LET'S FIND WHAT YOU NEED!</b>\n\n"
        f"👇 <i>Tap on any category folder below to explore our available services.</i>"
    )
    bot.send_message(m.chat.id, msg, parse_mode="HTML", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("cat_"))
def h_cat_view(c):
    cat = c.data.split("_")[1]
    svcs = execute_db("SELECT service_id, name, rate, margin FROM managed_services WHERE category=? AND disabled=0", (cat,), fetch_all=True)
    kb = InlineKeyboardMarkup(row_width=1)
    for s in svcs: kb.add(InlineKeyboardButton(f"⭐ {s[1]} - ₹{s[2]*s[3]:.2f}/1k", callback_data=f"buyinit_{s[0]}"))
    
    msg = (
        f"📂 <b>{html.escape(cat.upper())} SERVICES</b>\n\n"
        f"Prices shown are per 1,000 quantity.\n"
        f"👇 <i>Tap on the service you want to place an order!</i>"
    )
    bot.edit_message_text(msg, c.message.chat.id, c.message.message_id, parse_mode="HTML", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("buyinit_"))
def h_buyinit(c):
    sid = int(c.data.split("_")[1])
    user_states[c.from_user.id] = {"state": "get_link", "sid": sid}
    
    msg = (
        f"🚀 <b>AWESOME CHOICE! LET'S DO THIS.</b>\n\n"
        f"🔗 <b>STEP 1: Send the Target Link</b>\n\n"
        f"💡 <i>Tip: Just paste the URL (link to the post/profile/video) below and hit send. Make sure the account is PUBLIC!</i>"
    )
    bot.send_message(c.message.chat.id, msg, parse_mode="HTML", reply_markup=cancel_kb())

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get("state") == "get_link")
def h_link_input(m):
    user_states[m.from_user.id].update({"state": "get_qty", "link": m.text.strip()})
    
    msg = (
        f"✅ <b>Link Received!</b>\n\n"
        f"🔢 <b>STEP 2: Enter the Quantity</b>\n\n"
        f"💡 <i>Tip: Type a simple number (e.g., 500, 1000) and press send. Do not use commas or text!</i>"
    )
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
        msg = f"❌ <b>INSUFFICIENT BALANCE!</b> 😔\n\nYou need <code>₹{cost:.2f}</code> but your balance is <code>₹{u_bal:.2f}</code>.\n\n👇 <i>Tap '💳 Add Funds' below to top up!</i>"
        return bot.send_message(m.chat.id, msg, parse_mode="HTML", reply_markup=main_kb(uid))

    bot.send_message(m.chat.id, "⏳ <i>Processing your order securely...</i>", parse_mode="HTML")
    api_res, prov_used = call_provider_api(prov_name, 'add', {'service': prov_sid, 'link': state['link'], 'quantity': qty})
    
    if api_res and 'order' in api_res:
        execute_db("UPDATE users SET balance=balance-?, total_spent=total_spent+? WHERE user_id=?", (cost, cost, uid))
        execute_db("INSERT INTO orders (user_id, provider, api_order_id, service_id, quantity, cost, auto_refill) VALUES (?,?,?,?,?,?,1)",
                   (uid, prov_used, api_res['order'], state["sid"], qty, cost))
        
        msg = (
            f"✅ <b>ORDER SUCCESSFULLY PLACED!</b> 🎉\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"🧾 <b>Order ID:</b> <code>{api_res['order']}</code>\n"
            f"💰 <b>Total Deducted:</b> ₹{cost:.2f}\n"
            f"♻️ <b>Auto-Refill:</b> Enabled\n\n"
            f"<i>Thank you for your order! You can track it in the '📦 Order History' section.</i>"
        )
        bot.send_message(m.chat.id, msg, parse_mode="HTML", reply_markup=main_kb(uid))
    else: 
        bot.send_message(m.chat.id, "❌ <b>Provider Error!</b> The service might be busy. No money was deducted. Please try another service.", parse_mode="HTML", reply_markup=main_kb(uid))
    user_states.pop(uid, None)

# =======================================================================================
# 8. ADD FUNDS (GUIDED ESCROW)
# =======================================================================================
@bot.message_handler(func=lambda m: m.text == "💳 Add Funds")
def h_add_funds(m):
    user_states[m.from_user.id] = {"state": "fund_amt"}
    msg = (
        f"💸 <b>LET'S TOP UP YOUR WALLET!</b>\n\n"
        f"🔢 <b>STEP 1:</b> <i>Type the amount in INR (₹) you want to deposit and press send.</i>\n\n"
        f"⚠️ (Minimum Deposit: <code>₹{MIN_DEPOSIT}</code>)\n"
        f"💡 <i>Example: Just type <b>50</b> to deposit ₹50.</i>"
    )
    bot.send_message(m.chat.id, msg, parse_mode="HTML", reply_markup=cancel_kb())

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get("state") == "fund_amt")
def h_fund_qr(m):
    try:
        amt = float(m.text)
        if amt < MIN_DEPOSIT: return bot.send_message(m.chat.id, f"🚫 <b>Minimum deposit is <code>₹{MIN_DEPOSIT}</code>. Try again!</b>", parse_mode="HTML")
        user_states[m.from_user.id] = {"state": "fund_ss", "amt": amt}
        qr = f"https://api.qrserver.com/v1/create-qr-code/?size=400x400&data={urllib.parse.quote(f'upi://pay?pa={UPI_ID}&am={amt}&cu=INR')}"
        res = requests.get(qr, timeout=10)
        
        msg = (
            f"💳 <b>PAYMENT INSTRUCTIONS</b> 💳\n\n"
            f"📱 <b>STEP 2:</b> <i>Pay EXACTLY</i> <code>₹{amt}</code> <i>using the QR Code above OR this UPI ID:</i>\n"
            f"👉 <code>{UPI_ID}</code>\n\n"
            f"📸 <b>STEP 3: Upload Screenshot!</b>\n"
            f"<i>After paying, take a screenshot of your successful transaction and send the photo right here in this chat!</i>\n\n"
            f"⏳ <i>I am waiting for your photo...</i>"
        )
        bot.send_photo(m.chat.id, BytesIO(res.content), caption=msg, parse_mode="HTML", reply_markup=cancel_kb())
    except: bot.send_message(m.chat.id, "❌ <b>Oops! Please enter a valid number only.</b>", parse_mode="HTML")

@bot.message_handler(content_types=['photo'])
def h_payment_ss(m):
    uid = m.from_user.id
    if user_states.get(uid, {}).get("state") == "fund_ss":
        amt = user_states[uid]["amt"]
        tx = execute_db("INSERT INTO transactions (user_id, amount, status) VALUES (?, ?, 'PENDING')", (uid, amt), return_id=True)
        kb = InlineKeyboardMarkup().add(
            InlineKeyboardButton("✅ Approve", callback_data=f"ap_{tx}_{uid}_{amt}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"rj_{tx}_{uid}")
        )
        bot.send_photo(ADMIN_ID, m.photo[-1].file_id, caption=f"🚨 <b>DEPOSIT REQUEST</b>\nUser: <code>{uid}</code>\nAmount: <code>₹{amt}</code>\nTXN: <code>{tx}</code>", parse_mode="HTML", reply_markup=kb)
        
        msg = (
            f"✅ <b>SCREENSHOT RECEIVED!</b> 📸\n\n"
            f"⏳ <i>Please wait a few minutes while our admins verify the payment. Your wallet will be updated automatically!</i>"
        )
        bot.send_message(m.chat.id, msg, parse_mode="HTML", reply_markup=main_kb(uid))
        user_states.pop(uid, None)

@bot.callback_query_handler(func=lambda c: c.data.startswith(("ap_", "rj_")))
def h_admin_approval(c):
    if c.from_user.id != ADMIN_ID: return
    p = c.data.split("_")
    action, tx, uid = p[0], p[1], p[2]
    if action == "ap":
        amt = float(p[3])
        execute_db("UPDATE users SET balance=balance+? WHERE user_id=?", (amt, uid))
        execute_db("UPDATE transactions SET status='APPROVED' WHERE tx_id=?", (tx,))
        bot.edit_message_caption(f"✅ APPROVED TXN-{tx} | Added ₹{amt}", c.message.chat.id, c.message.message_id)
        try: bot.send_message(uid, f"🎉 <b>DEPOSIT APPROVED!</b> 💳\n\n<code>₹{amt}</code> <i>has been successfully added to your wallet. Happy ordering!</i>", parse_mode="HTML")
        except: pass
    else:
        execute_db("UPDATE transactions SET status='REJECTED' WHERE tx_id=?", (tx,))
        bot.edit_message_caption(f"❌ REJECTED TXN-{tx}", c.message.chat.id, c.message.message_id)
        try: bot.send_message(uid, f"❌ <b>DEPOSIT REJECTED!</b>\n\n<i>Your payment screenshot was rejected. If this is a mistake, please contact support.</i>", parse_mode="HTML")
        except: pass

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
                    if res and 'status' in res:
                        st = res['status'].capitalize()
                        execute_db("UPDATE orders SET status=? WHERE db_id=?", (st, o[0]))

            refillable_orders = execute_db("SELECT db_id, provider, api_order_id, user_id FROM orders WHERE auto_refill=1 AND status IN ('Completed', 'Partial')", fetch_all=True)
            if refillable_orders:
                for ro in refillable_orders:
                    refill_res, _ = call_provider_api(ro[1], 'refill', {'order': ro[2]})
                    if refill_res and 'refill' in refill_res:
                        execute_db("UPDATE orders SET last_refill_check=CURRENT_TIMESTAMP WHERE db_id=?", (ro[0],))
        except Exception as e:
            logging.error(f"Monitor Worker Error: {e}")
        time.sleep(300)

def self_ping():
    while True:
        try:
            host = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
            if host: requests.get(f"https://{host}/", timeout=10)
        except: pass
        time.sleep(600)

# =======================================================================================
# 10. STARTUP
# =======================================================================================
if __name__ == '__main__':
    init_database()
    try:
        bot.remove_webhook()
        time.sleep(1)
    except: pass

    threading.Thread(target=lambda: bot.infinity_polling(skip_pending=True, timeout=60), daemon=True).start()
    threading.Thread(target=auto_refill_and_status_monitor, daemon=True).start()
    threading.Thread(target=self_ping, daemon=True).start()

    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
