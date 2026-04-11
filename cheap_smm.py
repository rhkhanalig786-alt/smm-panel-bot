"""
=========================================================================================
🔥 CHEAP SMM PANEL BOT - ENTERPRISE V11.5 (FULL UNCUT MASTER) 🔥
=========================================================================================
"""

import telebot, requests, sqlite3, logging, time, os, urllib.parse, threading
from io import BytesIO
from flask import Flask
from datetime import datetime
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# =======================================================================================
# 1. SERVER, CONFIG & PUBLIC IDS
# =======================================================================================
logging.basicConfig(level=logging.INFO)
app = Flask(__name__)
@app.route('/')
def home(): return "🔥 V11.5 ENTERPRISE MASTER ONLINE 🔥"

# Replace with os.environ.get in production if you hide keys on Render
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8228287584:AAFPTUYPFbP9Sb4pZzPDmeZe3ymSQl_DJUU')
API_KEY = os.environ.get('API_KEY', 'rB105ycZUiN4wLIV7BUuOpGGZgWdbrXVw1jg1RKQ0hRbU30OEhi2Dnefb1Vqq430')

bot = telebot.TeleBot(BOT_TOKEN, threaded=True, num_threads=10)

API_URL = "https://indiansmmprovider.in/api/v2"
ADMIN_ID = 6034840006  
UPI_ID = "rahikhann@fam"

# Your Public IDs
CHANNEL_ID = "@cspnotice" 
CHANNEL_LINK = "https://t.me/cspnotice"
LOG_GROUP_ID = "@csplogs" 

MIN_DEPOSIT = 10.0          
user_states = {}

# =======================================================================================
# 2. DATABASE ENGINE
# =======================================================================================
def execute_db(query, params=(), fetch=False, fetch_all=False, return_id=False):
    try:
        with sqlite3.connect('panel_v11.db', check_same_thread=False, timeout=20) as conn:
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
    execute_db("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT, balance REAL DEFAULT 0.0, total_spent REAL DEFAULT 0.0, verified INTEGER DEFAULT 0, is_banned INTEGER DEFAULT 0)")
    execute_db("CREATE TABLE IF NOT EXISTS transactions (tx_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount REAL, status TEXT, date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    execute_db("CREATE TABLE IF NOT EXISTS orders (db_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, api_order_id TEXT, service_id INTEGER, quantity INTEGER, cost REAL, date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    execute_db("CREATE TABLE IF NOT EXISTS managed_services (service_id INTEGER PRIMARY KEY, category TEXT, name TEXT, rate REAL, margin REAL DEFAULT 1.45, orders_count INTEGER DEFAULT 0)")
    execute_db("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
    execute_db("CREATE TABLE IF NOT EXISTS promos (code TEXT PRIMARY KEY, amount REAL, max_uses INTEGER, current_uses INTEGER DEFAULT 0)")
    execute_db("CREATE TABLE IF NOT EXISTS promo_redeems (user_id INTEGER, code TEXT, PRIMARY KEY(user_id, code))")
    execute_db("CREATE TABLE IF NOT EXISTS tickets (ticket_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, message TEXT, status TEXT DEFAULT 'OPEN')")
    
    if not execute_db("SELECT value FROM settings WHERE key='global_margin'", fetch=True):
        execute_db("INSERT INTO settings (key, value) VALUES ('global_margin', '1.45')")

# =======================================================================================
# 3. MIDDLEWARE & CHECKS
# =======================================================================================
def check_sub(uid):
    if uid == ADMIN_ID: return True
    try: 
        status = bot.get_chat_member(CHANNEL_ID, uid).status
        return status in ['member', 'administrator', 'creator']
    except Exception: return True # Failsafe so bot doesn't crash if channel is missing

def log_order(user, sname, qty):
    try: bot.send_message(LOG_GROUP_ID, f"🎉 *NEW ORDER*\n👤 @{user}\n📦 `{qty}x` {sname}\n✅ Status: Processing", parse_mode="Markdown")
    except: pass

def get_margin():
    r = execute_db("SELECT value FROM settings WHERE key='global_margin'", fetch=True)
    return float(r[0]) if r else 1.45

def call_api(action, extra=None):
    payload = {'key': API_KEY, 'action': action}
    if extra: payload.update(extra)
    try: return requests.post(API_URL, data=payload, timeout=15).json()
    except: return None

# =======================================================================================
# 4. KEYBOARDS
# =======================================================================================
def main_kb(uid):
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add("🛒 Browse Services 🚀", "💰 My Profile")
    kb.add("💳 Add Funds", "📦 Order History")
    kb.add("🎟️ Redeem Promo", "📞 Support")
    kb.add("⚖️ Compare Services", "🎥 Tutorial")
    if uid == ADMIN_ID:
        kb.add("👑 --- ADMIN ZONE --- 👑")
        kb.add("⚙️ Manage Services", "📈 Adjust Margins")
        kb.add("📢 Broadcast", "🎟️ Create Promo")
        kb.add("🏦 API Ledger", "🎟️ Open Tickets")
    return kb

def cancel_kb(): return ReplyKeyboardMarkup(resize_keyboard=True).add("❌ Cancel")

# =======================================================================================
# 5. CORE HANDLERS
# =======================================================================================
@bot.message_handler(commands=['start'])
def h_start(m):
    uid = m.from_user.id
    if not check_sub(uid):
        kb = InlineKeyboardMarkup().add(InlineKeyboardButton("Join Channel", url=CHANNEL_LINK))
        return bot.send_message(m.chat.id, "🛑 You must join our channel to use the bot!", reply_markup=kb)
    
    u = execute_db("SELECT * FROM users WHERE user_id=?", (uid,), fetch=True)
    if not u: 
        execute_db("INSERT INTO users (user_id, username, first_name) VALUES (?,?,?)", (uid, m.from_user.username, m.from_user.first_name))
        u = execute_db("SELECT * FROM users WHERE user_id=?", (uid,), fetch=True)
    elif u[6] == 1: 
        return bot.send_message(m.chat.id, "🚫 You have been banned from using this bot.")
    
    bot.send_message(m.chat.id, f"⚡ *ENTERPRISE V11 MASTER*\n💰 Wallet Balance: `₹{u[3]:.2f}`", parse_mode="Markdown", reply_markup=main_kb(uid))

@bot.message_handler(func=lambda m: m.text == "❌ Cancel")
def h_cancel(m):
    user_states.pop(m.from_user.id, None)
    bot.send_message(m.chat.id, "🚫 Action Cancelled.", reply_markup=main_kb(m.from_user.id))

@bot.message_handler(func=lambda m: m.text == "💰 My Profile")
def h_profile(m):
    u = execute_db("SELECT * FROM users WHERE user_id=?", (m.from_user.id,), fetch=True)
    badge = "🏅 *Verified*" if u[5] else "👤 *User*"
    bot.send_message(m.chat.id, f"💧 *USER PROFILE* 💧\n━━━━━━━━━━━━━━━━━━━\n🆔 *ID:* `{u[0]}`\n🎖️ *Status:* {badge}\n💰 *Balance:* `₹{u[3]:.2f}`\n📈 *Total Spent:* `₹{u[4]:.2f}`\n━━━━━━━━━━━━━━━━━━━", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🎥 Tutorial")
def h_tutorial(m):
    bot.send_message(m.chat.id, "🎥 *HOW TO ORDER*\n1. Tap 'Add Funds' and scan the QR code.\n2. Tap 'Browse Services' and select a category.\n3. Read the stats, click Proceed, and paste your link.\n4. Enter quantity. Track it in 'Order History'.", parse_mode="Markdown")

# =======================================================================================
# 6. BROWSING & ORDERING FLOW (WITH STATS PREVIEW)
# =======================================================================================
@bot.message_handler(func=lambda m: m.text == "⚖️ Compare Services")
def h_compare(m):
    cats = execute_db("SELECT DISTINCT category FROM managed_services", fetch_all=True)
    if not cats: return bot.send_message(m.chat.id, "Store empty.")
    kb = InlineKeyboardMarkup(row_width=2)
    for c in cats: kb.add(InlineKeyboardButton(f"⚖️ {c[0]}", callback_data=f"comp_{c[0]}"))
    bot.send_message(m.chat.id, "⚖️ Select category to compare Cheap vs High-Quality:", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("comp_"))
def h_do_compare(c):
    cat = c.data.split("_")[1]
    svcs = execute_db("SELECT name, (rate*margin) as p FROM managed_services WHERE category=? ORDER BY p ASC", (cat,), fetch_all=True)
    if len(svcs) < 2: return bot.answer_callback_query(c.id, "Need 2+ services to compare.", show_alert=True)
    msg = f"⚖️ *{cat.upper()} COMPARISON*\n\n🟢 *Cheapest Option:*\n{svcs[0][0]}\n💰 `₹{svcs[0][1]:.2f}/1k`\n\n💎 *Best Quality:*\n{svcs[-1][0]}\n💰 `₹{svcs[-1][1]:.2f}/1k`"
    bot.edit_message_text(msg, c.message.chat.id, c.message.message_id, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🛒 Browse Services 🚀")
def h_browse(m):
    cats = execute_db("SELECT DISTINCT category FROM managed_services", fetch_all=True)
    if not cats: return bot.send_message(m.chat.id, "⚠️ Store is empty.")
    kb = InlineKeyboardMarkup(row_width=2)
    for c in cats: kb.add(InlineKeyboardButton(f"📁 {c[0]}", callback_data=f"cat_{c[0]}"))
    bot.send_message(m.chat.id, "🛒 *Select Category:*", parse_mode="Markdown", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("cat_"))
def h_cat(c):
    cat = c.data.split("_")[1]
    svcs = execute_db("SELECT service_id, name, rate, margin FROM managed_services WHERE category=?", (cat,), fetch_all=True)
    kb = InlineKeyboardMarkup(row_width=1)
    for s in svcs: kb.add(InlineKeyboardButton(f"🔥 {s[1]} - ₹{s[2]*s[3]:.2f}/1k", callback_data=f"stats_{s[0]}"))
    bot.edit_message_text(f"📁 *{cat.upper()} SERVICES*", c.message.chat.id, c.message.message_id, parse_mode="Markdown", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("stats_"))
def h_stats(c):
    sid = int(c.data.split("_")[1])
    res = call_api('services')
    try:
        s = next(i for i in res if int(i['service']) == sid)
        m = execute_db("SELECT margin FROM managed_services WHERE service_id=?", (sid,), fetch=True)[0]
        msg = f"📊 *SERVICE STATS*\n━━━━━━━━━━━━━━━━━━━\n🏷️ *Service:* {s['name']}\n🆔 *ID:* `{sid}`\n💰 *Price:* `₹{float(s['rate'])*m:.2f}/1k`\n📉 *Limits:* Min `{s['min']}` | Max `{s['max']}`\n━━━━━━━━━━━━━━━━━━━"
        kb = InlineKeyboardMarkup().add(InlineKeyboardButton("✅ Proceed to Order", callback_data=f"buy_{sid}"), InlineKeyboardButton("❌ Cancel", callback_data="cancel_order"))
        bot.edit_message_text(msg, c.message.chat.id, c.message.message_id, parse_mode="Markdown", reply_markup=kb)
    except: bot.answer_callback_query(c.id, "Error fetching stats.")

@bot.callback_query_handler(func=lambda c: c.data == "cancel_order")
def h_cancel_order(c):
    try: bot.delete_message(c.message.chat.id, c.message.message_id)
    except: pass

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
    cost = (qty / 1000.0) * (s_db[0] * s_db[1])
    
    u = execute_db("SELECT balance FROM users WHERE user_id=?", (uid,), fetch=True)
    if u[0] < cost: return bot.send_message(m.chat.id, f"❌ You need `₹{cost:.2f}`", parse_mode="Markdown", reply_markup=main_kb(uid))
        
    wait = bot.send_message(m.chat.id, "⏳ *Processing...*", parse_mode="Markdown", reply_markup=main_kb(uid))
    api_res = call_api('add', {'service': state["sid"], 'link': state["link"], 'quantity': qty})
    try: bot.delete_message(m.chat.id, wait.message_id)
    except: pass

    if api_res and 'order' in api_res:
        execute_db("UPDATE users SET balance=balance-?, total_spent=total_spent+? WHERE user_id=?", (cost, cost, uid))
        execute_db("INSERT INTO orders (user_id, api_order_id, service_id, quantity, cost) VALUES (?,?,?,?,?)", (uid, api_res['order'], state["sid"], qty, cost))
        bot.send_message(m.chat.id, f"✅ *ORDER PLACED*\n🧾 ID: `{api_res['order']}`\n💰 Cost: `₹{cost:.2f}`", parse_mode="Markdown")
        threading.Thread(target=log_order, args=(m.from_user.username, s_data['name'], qty)).start()
    else: bot.send_message(m.chat.id, "❌ Provider Error. Check Link.", parse_mode="Markdown")
    user_states.pop(uid, None)

# =======================================================================================
# 7. ADD FUNDS & ESCROW SYSTEM
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
        bot.edit_message_caption(f"✅ APPROVED TXN-{tx} | Added ₹{amt}", c.message.chat.id, c.message.message_id)
        try: bot.send_message(uid, f"🎉 *APPROVED!* `₹{amt}` added to your wallet.", parse_mode="Markdown")
        except: pass
    else:
        execute_db("UPDATE transactions SET status='REJECTED' WHERE tx_id=?", (tx,))
        bot.edit_message_caption(f"❌ REJECTED TXN-{tx}", c.message.chat.id, c.message.message_id)

# =======================================================================================
# 8. HISTORY & REFILL
# =======================================================================================
@bot.message_handler(func=lambda m: m.text == "📦 Order History")
def h_hist(m):
    orders = execute_db("SELECT api_order_id, quantity, cost FROM orders WHERE user_id=? ORDER BY date DESC LIMIT 4", (m.from_user.id,), fetch_all=True)
    if not orders: return bot.send_message(m.chat.id, "No orders found.")
    kb = InlineKeyboardMarkup()
    for o in orders: kb.add(InlineKeyboardButton(f"🔄 Track #{o[0]} (₹{o[2]:.2f})", callback_data=f"tr_{o[0]}"))
    bot.send_message(m.chat.id, "📦 *Recent Orders:* Click to track status.", parse_mode="Markdown", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("tr_"))
def h_track(c):
    oid = c.data.split("_")[1]
    res = call_api('status', {'order': oid})
    if res and 'status' in res:
        kb = InlineKeyboardMarkup()
        if res['status'].upper() in ["COMPLETED", "PARTIAL"]: kb.add(InlineKeyboardButton("♻️ Request Refill", callback_data=f"ref_{oid}"))
        bot.send_message(c.message.chat.id, f"📊 *STATUS:* `{res['status'].upper()}`\n📉 Remains: `{res.get('remains', 0)}`", parse_mode="Markdown", reply_markup=kb)
    bot.answer_callback_query(c.id)

@bot.callback_query_handler(func=lambda c: c.data.startswith("ref_"))
def h_refill(c):
    res = call_api('refill', {'order': c.data.split("_")[1]})
    if res and 'refill' in res: bot.answer_callback_query(c.id, f"✅ Refill Requested! ID: {res['refill']}", show_alert=True)
    else: bot.answer_callback_query(c.id, "❌ Refill unavailable for this order.", show_alert=True)

# =======================================================================================
# 9. PROMOS & SUPPORT TICKETS
# =======================================================================================
@bot.message_handler(func=lambda m: m.text == "🎟️ Redeem Promo")
def h_promo(m):
    user_states[m.from_user.id] = {"state": "promo"}
    bot.send_message(m.chat.id, "🎟️ *Enter Promo Code:*", parse_mode="Markdown", reply_markup=cancel_kb())

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get("state") == "promo")
def h_promo_run(m):
    uid, code = m.from_user.id, m.text.strip().upper()
    if execute_db("SELECT * FROM promo_redeems WHERE user_id=? AND code=?", (uid, code), fetch=True):
        return bot.send_message(m.chat.id, "❌ You already used this code.", reply_markup=main_kb(uid))
    
    p = execute_db("SELECT amount, max_uses, current_uses FROM promos WHERE code=?", (code,), fetch=True)
    if p and p[2] < p[1]:
        execute_db("UPDATE promos SET current_uses=current_uses+1 WHERE code=?", (code,))
        execute_db("INSERT INTO promo_redeems (user_id, code) VALUES (?, ?)", (uid, code))
        execute_db("UPDATE users SET balance=balance+? WHERE user_id=?", (p[0], uid))
        bot.send_message(m.chat.id, f"🎉 *SUCCESS!* `₹{p[0]}` added!", parse_mode="Markdown", reply_markup=main_kb(uid))
    else: bot.send_message(m.chat.id, "❌ Invalid or Expired code.", reply_markup=main_kb(uid))
    user_states.pop(uid, None)

@bot.message_handler(func=lambda m: m.text == "📞 Support" or m.text == "🎟️ Open Tickets")
def h_sup(m):
    if m.text == "🎟️ Open Tickets" and m.from_user.id == ADMIN_ID:
        ts = execute_db("SELECT ticket_id, user_id, message FROM tickets WHERE status='OPEN'", fetch_all=True)
        if not ts: return bot.send_message(ADMIN_ID, "✅ No open tickets.")
        for t in ts:
            kb = InlineKeyboardMarkup().add(InlineKeyboardButton(f"Reply #{t[0]}", callback_data=f"rept_{t[0]}_{t[1]}"))
            bot.send_message(ADMIN_ID, f"🚨 *TICKET #{t[0]}* (`{t[1]}`)\n{t[2]}", parse_mode="Markdown", reply_markup=kb)
    else:
        user_states[m.from_user.id] = {"state": "ticket"}
        bot.send_message(m.chat.id, "📝 *Type your issue/message to Admin:*", parse_mode="Markdown", reply_markup=cancel_kb())

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get("state") == "ticket")
def h_ticket(m):
    tid = execute_db("INSERT INTO tickets (user_id, message) VALUES (?, ?)", (m.from_user.id, m.text), return_id=True)
    kb = InlineKeyboardMarkup().add(InlineKeyboardButton(f"Reply #{tid}", callback_data=f"rept_{tid}_{m.from_user.id}"))
    bot.send_message(ADMIN_ID, f"🚨 *TICKET #{tid}* (`{m.from_user.id}`)\n{m.text}", parse_mode="Markdown", reply_markup=kb)
    bot.send_message(m.chat.id, "✅ Ticket Sent to Admin.", reply_markup=main_kb(m.from_user.id))
    user_states.pop(m.from_user.id, None)

@bot.callback_query_handler(func=lambda c: c.data.startswith("rept_"))
def h_rept(c):
    if c.from_user.id != ADMIN_ID: return
    _, tid, uid = c.data.split("_")
    user_states[ADMIN_ID] = {"state": "treply", "tid": tid, "uid": uid}
    bot.send_message(ADMIN_ID, f"✍️ *Reply to #{tid}:*", parse_mode="Markdown", reply_markup=cancel_kb())

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and user_states.get(ADMIN_ID, {}).get("state") == "treply")
def h_treply(m):
    tid, uid = user_states[ADMIN_ID]["tid"], user_states[ADMIN_ID]["uid"]
    execute_db("UPDATE tickets SET status='CLOSED' WHERE ticket_id=?", (tid,))
    try: bot.send_message(uid, f"📩 *SUPPORT REPLY (#{tid})*\n\n{m.text}", parse_mode="Markdown")
    except: pass
    bot.send_message(ADMIN_ID, "✅ Reply Sent.", reply_markup=main_kb(ADMIN_ID))
    user_states.pop(ADMIN_ID, None)

# =======================================================================================
# 10. ADMIN COMMANDS (Verify, Addbal, Ban, Ledger, Broadcast)
# =======================================================================================
@bot.message_handler(commands=['addbal', 'verify', 'ban'])
def admin_cmds(m):
    if m.from_user.id != ADMIN_ID: return
    try:
        p = m.text.split()
        if '/addbal' in m.text: 
            execute_db("UPDATE users SET balance=balance+? WHERE user_id=?", (float(p[2]), int(p[1])))
            bot.send_message(ADMIN_ID, f"✅ Added {p[2]} to {p[1]}")
            try: bot.send_message(int(p[1]), f"💰 Admin added ₹{p[2]} to your wallet.")
            except: pass
        elif '/verify' in m.text: 
            execute_db("UPDATE users SET verified=1 WHERE user_id=?", (int(p[1]),))
            bot.send_message(ADMIN_ID, f"✅ User {p[1]} Verified.")
        elif '/ban' in m.text: 
            execute_db("UPDATE users SET is_banned=1 WHERE user_id=?", (int(p[1]),))
            bot.send_message(ADMIN_ID, f"✅ User {p[1]} Banned.")
    except: bot.send_message(ADMIN_ID, "❌ Format error. Use: /addbal [ID] [Amt], /verify [ID], /ban [ID]")

@bot.message_handler(func=lambda m: m.text == "🎟️ Create Promo" and m.from_user.id == ADMIN_ID)
def h_create_promo(m):
    user_states[ADMIN_ID] = {"state": "c_promo"}
    bot.send_message(ADMIN_ID, "🎟️ Format: `[CODE] [AMOUNT] [MAX_USERS]`\nExample: `FREE50 50 10`", parse_mode="Markdown", reply_markup=cancel_kb())

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and user_states.get(ADMIN_ID, {}).get("state") == "c_promo")
def h_c_promo(m):
    try:
        p = m.text.split()
        execute_db("INSERT INTO promos (code, amount, max_uses) VALUES (?,?,?)", (p[0].upper(), float(p[1]), int(p[2])))
        bot.send_message(ADMIN_ID, f"✅ Promo `{p[0].upper()}` Created!", parse_mode="Markdown", reply_markup=main_kb(ADMIN_ID))
    except: bot.send_message(ADMIN_ID, "❌ Format Error.", reply_markup=main_kb(ADMIN_ID))
    user_states.pop(ADMIN_ID, None)

@bot.message_handler(func=lambda m: m.text == "🏦 API Ledger" and m.from_user.id == ADMIN_ID)
def h_ledger(m):
    res = call_api('balance')
    bal = res.get('balance', 'Err') if res else 'Err'
    bot.send_message(ADMIN_ID, f"🏦 *API PROVIDER BALANCE:* `₹{bal}`", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "📢 Broadcast" and m.from_user.id == ADMIN_ID)
def broad_1(m):
    user_states[ADMIN_ID] = {"state": "broad"}
    bot.send_message(ADMIN_ID, "📢 *Type message to send to all users:*", parse_mode="Markdown", reply_markup=cancel_kb())

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and user_states.get(ADMIN_ID, {}).get("state") == "broad")
def broad_2(m):
    users = execute_db("SELECT user_id FROM users", fetch_all=True)
    bot.send_message(ADMIN_ID, f"⏳ Sending to {len(users)} users...", reply_markup=main_kb(ADMIN_ID))
    for u in users:
        try: bot.send_message(u[0], f"📢 *ANNOUNCEMENT*\n\n{m.text}", parse_mode="Markdown")
        except: pass
    bot.send_message(ADMIN_ID, f"✅ Done.")
    user_states.pop(ADMIN_ID, None)

@bot.message_handler(func=lambda m: m.text == "📈 Adjust Margins" and m.from_user.id == ADMIN_ID)
def margin_1(m):
    user_states[ADMIN_ID] = {"state": "margin"}
    bot.send_message(ADMIN_ID, "📈 Enter new margin % (e.g. 50):", reply_markup=cancel_kb())

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and user_states.get(ADMIN_ID, {}).get("state") == "margin")
def margin_2(m):
    try:
        val = 1 + (float(m.text) / 100)
        execute_db("UPDATE settings SET value=? WHERE key='global_margin'", (str(val),))
        execute_db("UPDATE managed_services SET margin=?", (val,))
        bot.send_message(ADMIN_ID, f"✅ Margin updated to {m.text}%. All prices updated.", reply_markup=main_kb(ADMIN_ID))
    except: pass
    user_states.pop(ADMIN_ID, None)

@bot.message_handler(func=lambda m: m.text == "⚙️ Manage Services" and m.from_user.id == ADMIN_ID)
def m_svc_1(m):
    user_states[ADMIN_ID] = {"state": "svc_cat"}
    bot.send_message(ADMIN_ID, "📁 Category Name (e.g. Instagram):", reply_markup=cancel_kb())

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and user_states.get(ADMIN_ID, {}).get("state") == "svc_cat")
def m_svc_2(m):
    user_states[ADMIN_ID].update({"state": "svc_ids", "cat": m.text.strip()})
    bot.send_message(ADMIN_ID, "🔢 Send Provider Service IDs (Space separated for bulk add):")

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and user_states.get(ADMIN_ID, {}).get("state") == "svc_ids")
def m_svc_3(m):
    ids = m.text.replace(',', ' ').split()
    api_svcs = call_api('services')
    count = 0
    margin = get_margin()
    for sid in ids:
        try:
            s = next(i for i in api_svcs if str(i['service']) == sid.strip())
            execute_db("INSERT OR REPLACE INTO managed_services (service_id, category, name, rate, margin) VALUES (?,?,?,?,?)", (int(sid), user_states[ADMIN_ID]["cat"], s['name'], float(s['rate']), margin))
            count += 1
        except: pass
    bot.send_message(ADMIN_ID, f"✅ Successfully added {count} services to {user_states[ADMIN_ID]['cat']}.", reply_markup=main_kb(ADMIN_ID))
    user_states.pop(ADMIN_ID, None)

# =======================================================================================
# 11. STARTUP (409 CONFLICT FIX APPLIED)
# =======================================================================================
if __name__ == '__main__':
    # Fix for 409 Conflict: Removes any stuck webhooks/polling sessions
    try: bot.remove_webhook()
    except: pass
    
    # Start the engine
    threading.Thread(target=lambda: (init_database(), bot.infinity_polling(skip_pending=True, timeout=20)), daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
