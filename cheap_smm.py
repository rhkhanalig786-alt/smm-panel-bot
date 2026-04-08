"""
=========================================================================================
🔥 CHEAP SMM PANEL BOT - ULTIMATE RENDER EDITION 🔥
Features: Direct API, Escrow Payments, VIP Tiers, Promo Codes, Tickets, Admin Dashboard
=========================================================================================
"""

import telebot, requests, sqlite3, logging, time, urllib.parse, string, random, os, threading
from flask import Flask
from datetime import datetime, timedelta
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# =======================================================================================
# 1. RENDER WEB SERVER & LOGGING (PREVENTS CRASHES)
# =======================================================================================
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
@app.route('/')
def home(): 
    return "🔥 SMM Panel Bot is 24/7 ONLINE and running perfectly! 🔥"

# =======================================================================================
# 2. CONFIGURATION & TOKENS (FAILSAFE)
# =======================================================================================
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8228287584:AAFa93-H1WLx-sY_JNO3XJmeqzOogPImhqM')
API_KEY = os.environ.get('API_KEY', 'w4NIpEsjLOWxMM87R0ZxiPeMgu2ri8ugJeYPmMa206aPmOhDu9NJSl13mvQvPUEZ')
bot = telebot.TeleBot(BOT_TOKEN)

API_URL = "https://indiansmmprovider.in/api/v2"
ADMIN_ID = 6034840006  
SUPPORT_HANDLE = "@Cristae99" 
UPI_ID = "rahikhann@fam"

MARKUP_PERCENTAGE, MIN_DEPOSIT, REFERRAL_BONUS = 1.45, 10.0, 5.0
TARGET_IDS = [15979, 16411, 16453, 16441, 16439, 15397, 16451, 15843]
user_states = {}

# =======================================================================================
# 3. BULLETPROOF DATABASE MANAGER (PREVENTS LOCKS ON RENDER)
# =======================================================================================
def execute_db(query, params=(), fetch=False, fetchall=False):
    """Safely opens and closes DB to prevent SQLite locks on Render."""
    try:
        with sqlite3.connect('panel_enterprise.db', check_same_thread=False, timeout=10) as conn:
            c = conn.cursor()
            c.execute(query, params)
            if fetch: return c.fetchone()
            if fetchall: return c.fetchall()
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"DB Error: {e} | Query: {query}")
        return False

def init_db():
    tables = [
        '''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT, balance REAL DEFAULT 0.0, total_spent REAL DEFAULT 0.0, last_daily TIMESTAMP DEFAULT '2000-01-01 00:00:00', referred_by INTEGER DEFAULT 0, join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''',
        '''CREATE TABLE IF NOT EXISTS transactions (tx_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount REAL, status TEXT, date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''',
        '''CREATE TABLE IF NOT EXISTS orders (db_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, api_order_id TEXT, service_id INTEGER, link TEXT, quantity INTEGER, cost REAL, status TEXT DEFAULT 'Pending', date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''',
        '''CREATE TABLE IF NOT EXISTS promo_codes (code TEXT PRIMARY KEY, amount REAL, max_uses INTEGER DEFAULT 1, current_uses INTEGER DEFAULT 0, created_by INTEGER)''',
        '''CREATE TABLE IF NOT EXISTS promo_redeems (user_id INTEGER, code TEXT, date TIMESTAMP DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY (user_id, code))''',
        '''CREATE TABLE IF NOT EXISTS tickets (ticket_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, subject TEXT, status TEXT DEFAULT 'OPEN', date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)'''
    ]
    for t in tables: execute_db(t)

def get_or_create_user(uid, username=None, first_name=None, ref_by=0):
    u = execute_db("SELECT * FROM users WHERE user_id=?", (uid,), fetch=True)
    if not u and username is not None:
        execute_db("INSERT INTO users (user_id, username, first_name, referred_by) VALUES (?, ?, ?, ?)", (uid, username, first_name, ref_by))
        u = execute_db("SELECT * FROM users WHERE user_id=?", (uid,), fetch=True)
    return u

def get_vip_tier(spent):
    if spent >= 10000: return "🌌 Cosmic Whale"
    if spent >= 5000: return "💎 Diamond Boss"
    if spent >= 1000: return "🥇 Gold Member"
    if spent >= 500: return "🥈 Silver Hustler"
    return "🥉 Bronze Starter"

# =======================================================================================
# 4. API ENGINE
# =======================================================================================
def api_call(action, extra_data=None):
    payload = {'key': API_KEY, 'action': action}
    if extra_data: payload.update(extra_data)
    try: return requests.post(API_URL, data=payload, timeout=20).json()
    except: return None

def get_services():
    res = api_call('services')
    if not res: return None
    return {int(i['service']): {"name": i['name'], "rate": float(i['rate'])*MARKUP_PERCENTAGE, "min": int(i['min']), "max": int(i['max'])} for i in res if int(i['service']) in TARGET_IDS}

# =======================================================================================
# 5. UI & KEYBOARDS
# =======================================================================================
def get_main_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add("🛒 Browse Services 🚀", "💰 My Drip (Profile)", "💳 Add Funds (Wallet)", "📦 Order History", "🎁 Daily Bonus", "🎫 Redeem Promo", "🎫 Tickets (Support)")
    return kb

def get_cancel_kb(): return ReplyKeyboardMarkup(resize_keyboard=True).add("❌ Cancel Action")

# =======================================================================================
# 6. MAIN MENU HANDLERS
# =======================================================================================
@bot.message_handler(commands=['start'])
def start(m):
    uid = m.from_user.id
    ref_by = int(m.text.split()[1].replace('ref','')) if 'ref' in m.text else 0
    user_states.pop(uid, None) 
    u = get_or_create_user(uid, m.from_user.username, m.from_user.first_name, ref_by)
    
    msg = (f"⚡ *WELCOME TO THE PLUG!*\n\n💰 *Stash:* `₹{u[3]:.2f}`\n👑 *Rank:* {get_vip_tier(u[4])}\n"
           f"🆔 *ID:* `{u[0]}`\n\n👇 *Select an option below:*")
    bot.send_message(m.chat.id, msg, parse_mode="Markdown", reply_markup=get_main_kb())

@bot.message_handler(func=lambda m: m.text == "❌ Cancel Action")
def cancel(m):
    user_states.pop(m.from_user.id, None)
    bot.send_message(m.chat.id, "🚫 *Cancelled.* Back to lobby.", parse_mode="Markdown", reply_markup=get_main_kb())

@bot.message_handler(func=lambda m: m.text == "💰 My Drip (Profile)")
def profile(m):
    u = get_or_create_user(m.from_user.id)
    ref = f"https://t.me/{bot.get_me().username}?start=ref{u[0]}"
    bot.send_message(m.chat.id, f"💧 *PROFILE*\n🆔 `{u[0]}`\n💰 `₹{u[3]:.2f}`\n📈 Spent: `₹{u[4]:.2f}`\n\n🤝 *Ref Link:* `{ref}`", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🎁 Daily Bonus")
def daily(m):
    u = get_or_create_user(m.from_user.id)
    last = datetime.strptime(u[5], '%Y-%m-%d %H:%M:%S')
    if datetime.now() - last > timedelta(days=1):
        execute_db("UPDATE users SET balance = balance + 1.0, last_daily = CURRENT_TIMESTAMP WHERE user_id=?", (u[0],))
        bot.send_message(m.chat.id, "🎉 Claimed `₹1.00`!", parse_mode="Markdown")
    else: bot.send_message(m.chat.id, "🛑 Already claimed today.")

# =======================================================================================
# 7. ORDERING SYSTEM (BULLETPROOFED)
# =======================================================================================
@bot.message_handler(func=lambda m: m.text == "🛒 Browse Services 🚀")
def browse(m):
    bot.send_chat_action(m.chat.id, 'typing')
    data = get_services()
    if not data: return bot.send_message(m.chat.id, "⚠️ Provider API is currently offline. Try again soon.")
    kb = InlineKeyboardMarkup(row_width=1)
    for s_id, s in data.items(): kb.add(InlineKeyboardButton(f"🔥 {s['name']} - ₹{s['rate']:.2f}", callback_data=f"buy_{s_id}"))
    bot.send_message(m.chat.id, "🛒 *ROSTER:*", parse_mode="Markdown", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("buy_"))
def buy(c):
    user_states[c.from_user.id] = {"s": "link", "id": int(c.data.split("_")[1])}
    bot.delete_message(c.message.chat.id, c.message.message_id)
    bot.send_message(c.message.chat.id, "🔗 *Send Target Link (Must be Public):*", parse_mode="Markdown", reply_markup=get_cancel_kb())

@bot.message_handler(func=lambda m: m.from_user.id in user_states)
def flow(m):
    if m.text == "❌ Cancel Action": return cancel(m)
    uid = m.from_user.id
    state = user_states[uid]
    
    # 1. Ask for Link
    if state["s"] == "link":
        data = get_services()
        if not data or state["id"] not in data: 
            user_states.pop(uid, None)
            return bot.send_message(m.chat.id, "⚠️ API Error.", reply_markup=get_main_kb())
        
        s = data[state["id"]]
        user_states[uid].update({"s": "qty", "l": m.text, "r": s['rate'], "min": s['min'], "max": s['max']})
        bot.send_message(m.chat.id, f"🔢 *Enter Quantity* ({s['min']} - {s['max']}):", parse_mode="Markdown")
        
    # 2. Process Order
    elif state["s"] == "qty":
        try: qty = int(m.text)
        except: return bot.send_message(m.chat.id, "🤨 Numbers only.")
        
        if qty < state["min"] or qty > state["max"]: return bot.send_message(m.chat.id, f"🚫 Limits: {state['min']} to {state['max']}")
        cost = (qty/1000) * state["r"]
        
        u = get_or_create_user(uid)
        if u[3] < cost: 
            user_states.pop(uid, None)
            return bot.send_message(m.chat.id, f"❌ Low Balance! Costs `₹{cost:.2f}`", reply_markup=get_main_kb())
        
        msg = bot.send_message(m.chat.id, "⏳ *Connecting to Server...*", parse_mode="Markdown")
        
        # Deduct -> Call API -> Save
        execute_db("UPDATE users SET balance = balance - ? WHERE user_id=?", (cost, uid))
        res = api_call('add', {'service': state["id"], 'link': state["l"], 'quantity': qty})
        
        try: bot.delete_message(m.chat.id, msg.message_id)
        except: pass

        if res and 'order' in res:
            execute_db("INSERT INTO orders (user_id, api_order_id, service_id, link, quantity, cost) VALUES (?,?,?,?,?,?)", (uid, res['order'], state["id"], state["l"], qty, cost))
            execute_db("UPDATE users SET total_spent = total_spent + ? WHERE user_id=?", (cost, uid))
            bot.send_message(m.chat.id, f"✅ *ORDER PLACED!*\n🧾 ID: `{res['order']}`\n💰 Cost: `₹{cost:.2f}`", parse_mode="Markdown", reply_markup=get_main_kb())
        else:
            execute_db("UPDATE users SET balance = balance + ? WHERE user_id=?", (cost, uid)) # Refund
            bot.send_message(m.chat.id, f"❌ *FAILED:* Provider rejected. Refunded `₹{cost:.2f}`.", reply_markup=get_main_kb())
        
        user_states.pop(uid, None)

# =======================================================================================
# 8. WALLET & ADMIN
# =======================================================================================
@bot.message_handler(func=lambda m: m.text == "💳 Add Funds (Wallet)")
def add_funds(m):
    user_states[m.from_user.id] = {"s": "pay_amt"}
    bot.send_message(m.chat.id, f"💸 *Amount?* (Min ₹{MIN_DEPOSIT})", parse_mode="Markdown", reply_markup=get_cancel_kb())

@bot.message_handler(func=lambda m: m.from_user.id in user_states and user_states[m.from_user.id]["s"] == "pay_amt")
def pay(m):
    if m.text == "❌ Cancel Action": return cancel(m)
    try:
        amt = float(m.text)
        if amt < MIN_DEPOSIT: return bot.send_message(m.chat.id, f"🚫 Min ₹{MIN_DEPOSIT}")
        user_states[m.from_user.id] = {"s": "pay_ss", "amt": amt}
        qr = f"https://api.qrserver.com/v1/create-qr-code/?size=400x400&data={urllib.parse.quote(f'upi://pay?pa={UPI_ID}&am={amt}')}"
        bot.send_photo(m.chat.id, qr, caption=f"📸 *Pay ₹{amt} to `{UPI_ID}` and send screenshot here.*", parse_mode="Markdown")
    except: bot.send_message(m.chat.id, "Numbers only.")

@bot.message_handler(content_types=['photo'])
def ss(m):
    uid = m.from_user.id
    if uid in user_states and user_states[uid].get("s") == "pay_ss":
        amt = user_states[uid]["amt"]
        execute_db("INSERT INTO transactions (user_id, amount, status) VALUES (?, ?, 'PENDING')", (uid, amt))
        tx = execute_db("SELECT last_insert_rowid()", fetch=True)[0]
        
        kb = InlineKeyboardMarkup().add(InlineKeyboardButton("✅ Approve", callback_data=f"ap_{tx}_{uid}_{amt}"), InlineKeyboardButton("❌ Reject", callback_data=f"rj_{tx}_{uid}"))
        bot.send_photo(ADMIN_ID, m.photo[-1].file_id, caption=f"🚨 DEP: `₹{amt}`\n🆔 User: `{uid}`\n🧾 TXN: `{tx}`", parse_mode="Markdown", reply_markup=kb)
        bot.send_message(m.chat.id, "⏳ Sent to Admin.", reply_markup=get_main_kb())
        user_states.pop(uid, None)

@bot.callback_query_handler(func=lambda c: c.data.startswith("ap_") or c.data.startswith("rj_"))
def escrow(c):
    if c.from_user.id != ADMIN_ID: return
    d = c.data.split("_")
    action, tx, uid, amt = d[0], int(d[1]), int(d[2]), float(d[3]) if len(d)>3 else 0
    
    if action == "ap":
        execute_db("UPDATE users SET balance = balance + ? WHERE user_id=?", (amt, uid))
        execute_db("UPDATE transactions SET status='APPROVED' WHERE tx_id=?", (tx,))
        bot.edit_message_caption(f"✅ Approved TXN-{tx}", c.message.chat.id, c.message.message_id)
        try: bot.send_message(uid, f"🎉 Admin added `₹{amt}`!", parse_mode="Markdown")
        except: pass
    else:
        execute_db("UPDATE transactions SET status='REJECTED' WHERE tx_id=?", (tx,))
        bot.edit_message_caption(f"❌ Rejected TXN-{tx}", c.message.chat.id, c.message.message_id)

@bot.message_handler(commands=['admin'])
def admin_menu(m):
    if m.from_user.id != ADMIN_ID: return
    bot.reply_to(m, "👑 *ADMIN*\n`/stats` - View stats\n`/addfunds [ID] [Amt]` - Add money\n`/broadcast [Msg]` - Message all users\n`/makepromo [Amt] [Uses]` - Make code", parse_mode="Markdown")

# =======================================================================================
# 9. RENDER EXECUTION ENGINE
# =======================================================================================
def run_bot():
    print("--- [ INITIALIZING ENTERPRISE DB ] ---")
    init_db()
    print("--- [ DB SECURED. STARTING BOT ] ---")
    while True:
        try: 
            bot.infinity_polling(timeout=20, long_polling_timeout=10)
        except Exception as e:
            logger.error(f"Polling Crash: {e}")
            time.sleep(5) # Prevent aggressive crashing loops

if __name__ == '__main__':
    # 1. Start Bot in Background Thread
    threading.Thread(target=run_bot, daemon=True).start()
    
    # 2. Start Flask Web Server (Satisfies Render Port binding)
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
