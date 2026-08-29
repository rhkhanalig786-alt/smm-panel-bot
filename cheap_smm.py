"""
=========================================================================================
🔥 SMM PANEL BOT - ENTERPRISE V12 ULTIMATE (BACKUP/RESTORE + MULTI-API + AUTO-REFILL) 🔥
=========================================================================================
"""

import telebot, requests, sqlite3, logging, time, os, urllib.parse, threading
from io import BytesIO
from flask import Flask
from telebot.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton

# =======================================================================================
# 1. CONFIGURATION & SERVER
# =======================================================================================
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

BOT_TOKEN = os.environ.get('BOT_TOKEN', '8228287584:AAEA0krC0NCsdkoCpJO3ZfYTdzmkpqXpvYI')
bot = telebot.TeleBot(BOT_TOKEN, threaded=True, num_threads=10)

# Multi-API Configuration
PROVIDERS = {
    "provider_primary": {
        "url": os.environ.get("API_URL_1", "https://iggrowbot.com/api/v2"),
        "key": os.environ.get("API_KEY_1", "3eca5b223793d916cb69c18c5229e4d2")
    },
    "provider_secondary": {
        "url": os.environ.get("API_URL_2", "https://indiansmmprovider.in/api/v2"), 
        "key": os.environ.get("API_KEY_2", "SECONDARY_API_KEY_HERE")
    }
}

# Free Reward Service Config (1k Views per Refer)
FREE_VIEWS_SERVICE_ID = int(os.environ.get('FREE_VIEWS_SERVICE_ID', 101))
FREE_VIEWS_PROVIDER = "provider_primary"

ADMIN_ID = 6034840006
UPI_ID = "rahikhann@fam"
SUPPORT_USERNAME = "@itzdevrahi"
CHANNEL_ID = "@cspnotice"
CHANNEL_LINK = "https://t.me/cspnotice"
LOG_GROUP_ID = "@csplogs"
MIN_DEPOSIT = 15.0

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
            provider_service_id INTEGER, rate REAL, margin REAL DEFAULT 1.45, disabled INTEGER DEFAULT 0
        )""",
        "CREATE TABLE IF NOT EXISTS transactions (tx_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount REAL, status TEXT, date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
        "CREATE TABLE IF NOT EXISTS tickets (ticket_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, message TEXT, status TEXT DEFAULT 'OPEN', reply TEXT)",
        "CREATE TABLE IF NOT EXISTS referrals (referrer_id INTEGER, referred_id INTEGER, reward_claimed INTEGER DEFAULT 1, PRIMARY KEY(referrer_id, referred_id))",
        "CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)"
    ]
    for table in tables:
        execute_db(table)

    if not execute_db("SELECT value FROM settings WHERE key='global_margin'", fetch=True):
        execute_db("INSERT INTO settings (key, value) VALUES ('global_margin', '1.45')")

# =======================================================================================
# 3. MULTI-API ROUTING
# =======================================================================================
def call_provider_api(provider_name, action, extra=None):
    prov = PROVIDERS.get(provider_name)
    if not prov or not prov.get("key") or "HERE" in prov.get("key"):
        prov = PROVIDERS["provider_primary"]
        provider_name = "provider_primary"

    payload = {'key': prov['key'], 'action': action}
    if extra: payload.update(extra)
    try:
        r = requests.post(prov['url'], data=payload, timeout=15)
        return r.json(), provider_name
    except Exception as e:
        logging.error(f"API Error ({provider_name}): {e}")
        return None, provider_name

def get_best_provider_for_service(service_id):
    svc = execute_db("SELECT provider, provider_service_id, rate, margin FROM managed_services WHERE service_id=?", (service_id,), fetch=True)
    if svc and svc[0] in PROVIDERS:
        return svc[0], svc[1], svc[2], svc[3]
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
        kb.add("👑 Admin: Manage Services", "📢 Admin: Broadcast")
        kb.add("💾 Admin: Backup DB", "🔄 Admin: Restore DB")
    return kb

def cancel_kb():
    return ReplyKeyboardMarkup(resize_keyboard=True).add("❌ Cancel")

# =======================================================================================
# 5. CORE USER & REFERRAL LOGIC
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
            try: bot.send_message(referrer_id, f"🎉 *New Referral!*\nUser @{m.from_user.username or uid} joined.\n🎁 *You received +1 Free 1K Views Credit!*", parse_mode="Markdown")
            except: pass

    bot.send_message(m.chat.id, f"👋 Welcome, *{m.from_user.first_name}*!", parse_mode="Markdown", reply_markup=main_kb(uid))

@bot.message_handler(func=lambda m: m.text == "❌ Cancel")
def h_cancel(m):
    user_states.pop(m.from_user.id, None)
    bot.send_message(m.chat.id, "🚫 Action cancelled.", reply_markup=main_kb(m.from_user.id))

@bot.message_handler(func=lambda m: m.text == "👥 Referral Program")
def h_referral(m):
    uid = m.from_user.id
    u = execute_db("SELECT referral_code, free_views_credits FROM users WHERE user_id=?", (uid,), fetch=True)
    ref_count = execute_db("SELECT COUNT(*) FROM referrals WHERE referrer_id=?", (uid,), fetch=True)[0]
    link = f"https://t.me/{bot.get_me().username}?start=ref_{uid}"
    
    msg = f"👥 *REFERRAL PROGRAM*\n━━━━━━━━━━━━━━━━━━━\n🔗 *Your Link:* `{link}`\n👤 *Friends Referred:* `{ref_count}`\n🎁 *Free 1K Views Credits:* `{u[1]}`\n\n🚀 Get **1,000 Free Views** for every friend who joins!"
    bot.send_message(m.chat.id, msg, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🎁 Claim Free 1K Views")
def h_claim_free(m):
    uid = m.from_user.id
    credits = execute_db("SELECT free_views_credits FROM users WHERE user_id=?", (uid,), fetch=True)[0]
    if credits <= 0:
        return bot.send_message(m.chat.id, "❌ You have 0 credits. Invite friends to earn more!")
    user_states[uid] = {"state": "claim_free_link"}
    bot.send_message(m.chat.id, f"🎁 *You have {credits} credit(s)!*\n\n🔗 Send the target link to receive 1,000 free views:", parse_mode="Markdown", reply_markup=cancel_kb())

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get("state") == "claim_free_link")
def h_process_free_claim(m):
    uid = m.from_user.id
    credits = execute_db("SELECT free_views_credits FROM users WHERE user_id=?", (uid,), fetch=True)[0]
    if credits <= 0: return bot.send_message(m.chat.id, "❌ No credits remaining.", reply_markup=main_kb(uid))

    api_res, prov_used = call_provider_api(FREE_VIEWS_PROVIDER, 'add', {'service': FREE_VIEWS_SERVICE_ID, 'link': m.text.strip(), 'quantity': 1000})
    if api_res and 'order' in api_res:
        execute_db("UPDATE users SET free_views_credits = free_views_credits - 1 WHERE user_id=?", (uid,))
        execute_db("INSERT INTO orders (user_id, provider, api_order_id, service_id, quantity, cost, auto_refill) VALUES (?,?,?,?,?,?,?)",
                   (uid, prov_used, api_res['order'], FREE_VIEWS_SERVICE_ID, 1000, 0.0, 0))
        bot.send_message(m.chat.id, f"✅ *FREE 1,000 VIEWS PLACED!*\n🧾 ID: `{api_res['order']}`", parse_mode="Markdown", reply_markup=main_kb(uid))
    else: bot.send_message(m.chat.id, "❌ Failed to place order. Check your link.", reply_markup=main_kb(uid))
    user_states.pop(uid, None)

# =======================================================================================
# 6. ADMIN: DATABASE BACKUP & RESTORE
# =======================================================================================
@bot.message_handler(func=lambda m: m.text == "💾 Admin: Backup DB")
def handle_admin_backup(message):
    uid = message.from_user.id
    if uid != ADMIN_ID: return
        
    bot.send_message(uid, "⏳ *Generating live database snapshot...*", parse_mode="Markdown")
    backup_file = f"backup_{int(time.time())}.db"
    
    try:
        with db_lock:
            with sqlite3.connect('panel_v12.db') as src, sqlite3.connect(backup_file) as dst:
                src.backup(dst)
        
        with open(backup_file, 'rb') as doc:
            caption = f"💾 *Database Backup*\n📅 `{time.strftime('%Y-%m-%d %H:%M:%S')}`\n_Store this safely._"
            bot.send_document(uid, doc, caption=caption, parse_mode="Markdown")
    except Exception as e:
        bot.send_message(uid, f"❌ *Backup Failed:*\n`{e}`", parse_mode="Markdown")
    finally:
        if os.path.exists(backup_file): os.remove(backup_file)

@bot.message_handler(func=lambda m: m.text == "🔄 Admin: Restore DB")
def handle_admin_restore_prompt(message):
    uid = message.from_user.id
    if uid != ADMIN_ID: return
    
    user_states[uid] = {"state": "wait_for_db_upload"}
    bot.send_message(uid, "⚠️ *DATABASE RESTORE*\n\nPlease upload the `.db` backup file as a document.\n_Note: This will completely overwrite the current live database!_", parse_mode="Markdown", reply_markup=cancel_kb())

@bot.message_handler(content_types=['document'])
def handle_document_upload(message):
    uid = message.from_user.id
    if uid == ADMIN_ID and user_states.get(uid, {}).get("state") == "wait_for_db_upload":
        doc = message.document
        if not doc.file_name.endswith('.db'):
            return bot.send_message(uid, "❌ Please upload a valid `.db` file.", reply_markup=main_kb(uid))
        
        bot.send_message(uid, "⏳ *Restoring database... Please wait.*", parse_mode="Markdown")
        temp_file = f"restore_{int(time.time())}.db"
        
        try:
            # Download file from Telegram
            file_info = bot.get_file(doc.file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            
            with open(temp_file, 'wb') as f:
                f.write(downloaded_file)
                
            # Perform safe restore using sqlite3 backup API in reverse
            with db_lock:
                with sqlite3.connect(temp_file) as src, sqlite3.connect('panel_v12.db') as dst:
                    src.backup(dst)
                    
            bot.send_message(uid, "✅ *Database Restored Successfully!* All data has been overwritten safely.", parse_mode="Markdown", reply_markup=main_kb(uid))
        except Exception as e:
            bot.send_message(uid, f"❌ *Restore Failed:*\n`{e}`", parse_mode="Markdown", reply_markup=main_kb(uid))
            logging.error(f"Restore failed: {e}")
        finally:
            user_states.pop(uid, None)
            if os.path.exists(temp_file): os.remove(temp_file)

# =======================================================================================
# 7. BROWSING & ORDERING FLOW
# =======================================================================================
@bot.message_handler(func=lambda m: m.text == "🛒 Browse Services")
def h_browse(m):
    cats = execute_db("SELECT DISTINCT category FROM managed_services WHERE disabled=0", fetch_all=True)
    if not cats: return bot.send_message(m.chat.id, "⚠️ No services available.")
    kb = InlineKeyboardMarkup(row_width=2)
    for c in cats: kb.add(InlineKeyboardButton(f"📁 {c[0]}", callback_data=f"cat_{c[0]}"))
    bot.send_message(m.chat.id, "🛒 *Select Category:*", parse_mode="Markdown", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("cat_"))
def h_cat_view(c):
    cat = c.data.split("_")[1]
    svcs = execute_db("SELECT service_id, name, rate, margin FROM managed_services WHERE category=? AND disabled=0", (cat,), fetch_all=True)
    kb = InlineKeyboardMarkup(row_width=1)
    for s in svcs: kb.add(InlineKeyboardButton(f"{s[1]} - ₹{s[2]*s[3]:.2f}/1k", callback_data=f"buyinit_{s[0]}"))
    bot.edit_message_text(f"📁 *{cat.upper()} SERVICES*", c.message.chat.id, c.message.message_id, parse_mode="Markdown", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("buyinit_"))
def h_buyinit(c):
    sid = int(c.data.split("_")[1])
    user_states[c.from_user.id] = {"state": "get_link", "sid": sid}
    bot.send_message(c.message.chat.id, "🔗 *Send Target Link:*", parse_mode="Markdown", reply_markup=cancel_kb())

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get("state") == "get_link")
def h_link_input(m):
    user_states[m.from_user.id].update({"state": "get_qty", "link": m.text.strip()})
    bot.send_message(m.chat.id, "🔢 *Enter Quantity (Numbers only):*", parse_mode="Markdown")

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get("state") == "get_qty")
def h_qty_input(m):
    uid = m.from_user.id
    state = user_states[uid]
    try: qty = int(m.text)
    except: return bot.send_message(m.chat.id, "❌ Numbers only.")

    prov_name, prov_sid, rate, margin = get_best_provider_for_service(state["sid"])
    cost = (qty / 1000.0) * (rate * margin)

    u_bal = execute_db("SELECT balance FROM users WHERE user_id=?", (uid,), fetch=True)[0]
    if u_bal < cost: return bot.send_message(m.chat.id, f"❌ Insufficient balance. You need ₹{cost:.2f}", reply_markup=main_kb(uid))

    api_res, prov_used = call_provider_api(prov_name, 'add', {'service': prov_sid, 'link': state['link'], 'quantity': qty})
    if api_res and 'order' in api_res:
        execute_db("UPDATE users SET balance=balance-?, total_spent=total_spent+? WHERE user_id=?", (cost, cost, uid))
        execute_db("INSERT INTO orders (user_id, provider, api_order_id, service_id, quantity, cost, auto_refill) VALUES (?,?,?,?,?,?,1)",
                   (uid, prov_used, api_res['order'], state["sid"], qty, cost))
        bot.send_message(m.chat.id, f"✅ *ORDER PLACED!*\n🧾 ID: `{api_res['order']}`\n💰 Cost: ₹{cost:.2f}\n♻️ Auto-Refill: Enabled", parse_mode="Markdown", reply_markup=main_kb(uid))
    else: bot.send_message(m.chat.id, "❌ Provider Error.", reply_markup=main_kb(uid))
    user_states.pop(uid, None)

# =======================================================================================
# 8. ADD FUNDS (MANUAL APPROVAL)
# =======================================================================================
@bot.message_handler(func=lambda m: m.text == "💳 Add Funds")
def h_add_funds(m):
    user_states[m.from_user.id] = {"state": "fund_amt"}
    bot.send_message(m.chat.id, f"💸 *Enter deposit amount in INR (₹):*\n(Minimum: `₹{MIN_DEPOSIT}`)", parse_mode="Markdown", reply_markup=cancel_kb())

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get("state") == "fund_amt")
def h_fund_qr(m):
    try:
        amt = float(m.text)
        if amt < MIN_DEPOSIT: return bot.send_message(m.chat.id, f"🚫 Minimum `₹{MIN_DEPOSIT}`.")
        user_states[m.from_user.id] = {"state": "fund_ss", "amt": amt}
        qr = f"https://api.qrserver.com/v1/create-qr-code/?size=400x400&data={urllib.parse.quote(f'upi://pay?pa={UPI_ID}&am={amt}&cu=INR')}"
        res = requests.get(qr, timeout=10)
        bot.send_photo(m.chat.id, BytesIO(res.content), caption=f"💳 *PAYMENT*\nAmount: `₹{amt}`\nUPI: `{UPI_ID}`\n📸 Send screenshot here after paying.", parse_mode="Markdown", reply_markup=cancel_kb())
    except: bot.send_message(m.chat.id, "❌ Numbers only.")

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
        bot.send_photo(ADMIN_ID, m.photo[-1].file_id, caption=f"🚨 *DEPOSIT REQUEST*\nUser: `{uid}`\nAmt: `₹{amt}`\nTXN: `{tx}`", parse_mode="Markdown", reply_markup=kb)
        bot.send_message(m.chat.id, "⏳ Screenshot submitted. Balance will be added after confirmation.", reply_markup=main_kb(uid))
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
        try: bot.send_message(uid, f"🎉 *Deposit of ₹{amt} Approved!*", parse_mode="Markdown")
        except: pass
    else:
        execute_db("UPDATE transactions SET status='REJECTED' WHERE tx_id=?", (tx,))
        bot.edit_message_caption(f"❌ REJECTED TXN-{tx}", c.message.chat.id, c.message.message_id)

# =======================================================================================
# 9. AUTOMATED BACKGROUND TASKS 
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
