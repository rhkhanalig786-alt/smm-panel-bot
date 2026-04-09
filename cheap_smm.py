"""
=========================================================================================
🔥 CHEAP SMM PANEL BOT - ENTERPRISE V6 (GOD MODE EDITION) 🔥
Features: Admin UI Buttons, Live Tracking, Low Balance Alerts, God Mode Funding
=========================================================================================
"""

import telebot, requests, sqlite3, logging, time, os, threading
from flask import Flask
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# =======================================================================================
# 1. SERVER & CONFIGURATION
# =======================================================================================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
app = Flask(__name__)
@app.route('/')
def home(): return "🔥 ENTERPRISE V6 (GOD MODE) ONLINE 🔥"

BOT_TOKEN = os.environ.get('BOT_TOKEN', '8228287584:AAEznVpPO0bjGL-WfBjlMmK4tUMg0KB6GqQ')
API_KEY = os.environ.get('API_KEY', 'w4NIpEsjLOWxMM87R0ZxiPeMgu2ri8ugJeYPmMa206aPmOhDu9NJSl13mvQvPUEZ')
bot = telebot.TeleBot(BOT_TOKEN)

API_URL = "https://indiansmmprovider.in/api/v2"
ADMIN_ID = 6034840006  
UPI_ID = "rahikhann@fam"
MARKUP_PERCENTAGE, MIN_DEPOSIT, LOW_BAL_ALERT = 1.45, 10.0, 15.0
TARGET_IDS = [15979, 16411, 16453, 16441, 16439, 15397, 16451, 15843]
user_states = {}

# =======================================================================================
# 2. DATABASE ENGINE
# =======================================================================================
def db_exec(query, params=(), fetch=False, fetch_all=False):
    with sqlite3.connect('panel_enterprise.db', check_same_thread=False, timeout=15) as conn:
        c = conn.cursor()
        c.execute(query, params)
        if fetch: return c.fetchone()
        if fetch_all: return c.fetchall()
        conn.commit()
    return True

def init_db():
    queries = [
        "CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT, balance REAL DEFAULT 0.0, total_spent REAL DEFAULT 0.0, join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
        "CREATE TABLE IF NOT EXISTS transactions (tx_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount REAL, status TEXT, date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
        "CREATE TABLE IF NOT EXISTS orders (db_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, api_order_id TEXT, service_id INTEGER, quantity INTEGER, cost REAL, date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
    ]
    for q in queries: db_exec(q)

def get_u(uid, uname=None, fname=None):
    u = db_exec("SELECT * FROM users WHERE user_id=?", (uid,), True)
    if not u and uname:
        db_exec("INSERT INTO users (user_id, username, first_name) VALUES (?,?,?)", (uid, uname, fname))
        u = db_exec("SELECT * FROM users WHERE user_id=?", (uid,), True)
    return u

# =======================================================================================
# 3. DYNAMIC KEYBOARDS (USER vs ADMIN)
# =======================================================================================
def get_main_kb(user_id):
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add("🛒 Browse Services 🚀", "💰 My Drip (Profile)")
    kb.add("💳 Add Funds (Wallet)", "📦 Order History")
    kb.add("📞 Support")
    
    # SECRET ADMIN MENU
    if user_id == ADMIN_ID:
        kb.add("👑 --- ADMIN ZONE --- 👑")
        kb.add("📢 Broadcast Msg", "📩 Direct Msg")
        kb.add("💰 Manage Funds (Add/Remove)")
    return kb

def cancel_kb():
    return ReplyKeyboardMarkup(resize_keyboard=True).add("❌ Cancel Action")

# =======================================================================================
# 4. CORE HANDLERS
# =======================================================================================
@bot.message_handler(commands=['start'])
def start(m):
    user_states.pop(m.from_user.id, None)
    u = get_u(m.from_user.id, m.from_user.username, m.from_user.first_name)
    bot.send_message(m.chat.id, f"⚡ *SYSTEM V6 ONLINE*\n💰 Wallet: `₹{u[3]:.2f}`", parse_mode="Markdown", reply_markup=get_main_kb(m.from_user.id))

@bot.message_handler(func=lambda m: m.text == "❌ Cancel Action")
def cancel(m):
    user_states.pop(m.from_user.id, None)
    bot.send_message(m.chat.id, "🚫 Action Cancelled.", reply_markup=get_main_kb(m.from_user.id))

# =======================================================================================
# 5. ORDER SYSTEM & LOW BALANCE ALERTS
# =======================================================================================
@bot.message_handler(func=lambda m: m.text == "🛒 Browse Services 🚀")
def browse(m):
    try:
        res = requests.post(API_URL, data={'key': API_KEY, 'action': 'services'}, timeout=15).json()
        kb = InlineKeyboardMarkup(row_width=1)
        for i in res:
            if int(i['service']) in TARGET_IDS:
                kb.add(InlineKeyboardButton(f"🔥 {i['name']} - ₹{float(i['rate'])*MARKUP_PERCENTAGE:.2f}", callback_data=f"buy_{i['service']}"))
        bot.send_message(m.chat.id, "🛒 *SELECT SERVICE:*", reply_markup=kb)
    except: bot.send_message(m.chat.id, "❌ API Offline.")

@bot.callback_query_handler(func=lambda c: c.data.startswith("buy_"))
def ask_link(c):
    user_states[c.from_user.id] = {"s": "link", "id": int(c.data.split("_")[1])}
    bot.send_message(c.message.chat.id, "🔗 *Send Target Link:*", parse_mode="Markdown", reply_markup=cancel_kb())

@bot.message_handler(func=lambda m: m.from_user.id in user_states and user_states[m.from_user.id]["s"] == "link")
def ask_qty(m):
    if m.text == "❌ Cancel Action": return cancel(m)
    user_states[m.from_user.id].update({"s": "qty", "l": m.text})
    bot.send_message(m.chat.id, "🔢 *Enter Quantity:*")

@bot.message_handler(func=lambda m: m.from_user.id in user_states and user_states[m.from_user.id]["s"] == "qty")
def process_order(m):
    if m.text == "❌ Cancel Action": return cancel(m)
    uid, st = m.from_user.id, user_states[m.from_user.id]
    
    try:
        qty = int(m.text)
        res = requests.post(API_URL, data={'key': API_KEY, 'action': 'services'}, timeout=10).json()
        s_data = next(i for i in res if int(i['service']) == st["id"])
        cost = (qty/1000) * (float(s_data['rate']) * MARKUP_PERCENTAGE)
        
        user = get_u(uid)
        if user[3] < cost: return bot.send_message(m.chat.id, f"❌ Insufficient Funds! Cost: `₹{cost:.2f}`", parse_mode="Markdown")
        
        order = requests.post(API_URL, data={'key': API_KEY, 'action': 'add', 'service': st['id'], 'link': st['l'], 'quantity': qty}, timeout=20).json()
        if 'order' in order:
            new_bal = user[3] - cost
            db_exec("UPDATE users SET balance = ?, total_spent = total_spent + ? WHERE user_id=?", (new_bal, cost, uid))
            db_exec("INSERT INTO orders (user_id, api_order_id, service_id, quantity, cost) VALUES (?,?,?,?,?)", (uid, order['order'], st['id'], qty, cost))
            
            bot.send_message(m.chat.id, f"✅ *ORDER PLACED!*\n🧾 ID: `{order['order']}`\n💰 Cost: `₹{cost:.2f}`\n💳 Rem: `₹{new_bal:.2f}`", parse_mode="Markdown", reply_markup=get_main_kb(uid))
            
            # LOW BALANCE ALERT
            if new_bal < LOW_BAL_ALERT:
                bot.send_message(m.chat.id, f"⚠️ *LOW BALANCE ALERT*\nYou only have `₹{new_bal:.2f}` left. Top up now so you don't miss out on future orders!", parse_mode="Markdown")
        else: bot.send_message(m.chat.id, f"❌ Error: {order.get('error')}", reply_markup=get_main_kb(uid))
    except: bot.send_message(m.chat.id, "❌ Failed. Numbers only.", reply_markup=get_main_kb(uid))
    user_states.pop(uid, None)

# =======================================================================================
# 6. LIVE ORDER TRACKING
# =======================================================================================
@bot.message_handler(func=lambda m: m.text == "📦 Order History")
def history(m):
    orders = db_exec("SELECT api_order_id, quantity, cost, date FROM orders WHERE user_id=? ORDER BY date DESC LIMIT 3", (m.from_user.id,), fetch_all=True)
    if not orders: return bot.send_message(m.chat.id, "No recent orders.")
    
    text = "📦 *LAST 3 ORDERS* 📦\n\n"
    kb = InlineKeyboardMarkup(row_width=2)
    buttons = []
    
    for o in orders:
        text += f"🧾 *ID:* `{o[0]}` | Qty: {o[1]} | Cost: ₹{o[2]:.2f}\n📅 {o[3].split()[0]}\n\n"
        buttons.append(InlineKeyboardButton(f"🔄 Track: {o[0]}", callback_data=f"track_{o[0]}"))
    
    kb.add(*buttons)
    bot.send_message(m.chat.id, text, parse_mode="Markdown", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("track_"))
def track_api(c):
    order_id = c.data.split("_")[1]
    try:
        res = requests.post(API_URL, data={'key': API_KEY, 'action': 'status', 'order': order_id}, timeout=15).json()
        if 'status' in res:
            msg = f"📊 *LIVE STATUS - ID: {order_id}*\n\n🚥 Status: `{res['status'].upper()}`\n📈 Start Count: `{res.get('start_count', 'N/A')}`\n📉 Remains: `{res.get('remains', 'N/A')}`"
            bot.send_message(c.message.chat.id, msg, parse_mode="Markdown")
        else: bot.answer_callback_query(c.id, "Status not available yet.", show_alert=True)
    except: bot.answer_callback_query(c.id, "API connection failed.", show_alert=True)

# =======================================================================================
# 7. ADD FUNDS (TEXT SAFE)
# =======================================================================================
@bot.message_handler(func=lambda m: m.text == "💳 Add Funds (Wallet)")
def fund_start(m):
    user_states[m.from_user.id] = {"s": "f_amt"}
    bot.send_message(m.chat.id, "💸 *Amount to deposit?*", parse_mode="Markdown", reply_markup=cancel_kb())

@bot.message_handler(func=lambda m: m.from_user.id in user_states and user_states[m.from_user.id]["s"] == "f_amt")
def fund_ss(m):
    if m.text == "❌ Cancel Action": return cancel(m)
    try:
        amt = float(m.text)
        user_states[m.from_user.id] = {"s": "f_ss", "amt": amt}
        bot.send_message(m.chat.id, f"💳 *PAY ₹{amt} TO:*\n`{UPI_ID}`\n\n📸 *Send Screenshot now.*", parse_mode="Markdown")
    except: bot.send_message(m.chat.id, "Numbers only.")

@bot.message_handler(content_types=['photo'])
def fund_confirm(m):
    uid = m.from_user.id
    if uid in user_states and user_states[uid].get("s") == "f_ss":
        amt = user_states[uid]["amt"]
        kb = InlineKeyboardMarkup().add(InlineKeyboardButton("✅ Approve", callback_data=f"ap_{uid}_{amt}"))
        bot.send_photo(ADMIN_ID, m.photo[-1].file_id, caption=f"🚨 DEP: ₹{amt}\nID: `{uid}`", reply_markup=kb)
        bot.send_message(m.chat.id, "⏳ Sent to Admin.", reply_markup=get_main_kb(uid))
        user_states.pop(uid, None)

@bot.callback_query_handler(func=lambda c: c.data.startswith("ap_"))
def fund_approve(c):
    _, uid, amt = c.data.split("_")
    db_exec("UPDATE users SET balance = balance + ? WHERE user_id=?", (float(amt), int(uid)))
    bot.send_message(int(uid), f"🎉 Added ₹{amt}!")
    bot.edit_message_caption("✅ Approved", c.message.chat.id, c.message.message_id)

# =======================================================================================
# 8. SECRET ADMIN ZONE (GOD MODE, BROADCAST, DMs)
# =======================================================================================

# --- GOD MODE FUNDING ---
@bot.message_handler(func=lambda m: m.text == "💰 Manage Funds (Add/Remove)" and m.from_user.id == ADMIN_ID)
def god_funds_1(m):
    user_states[ADMIN_ID] = {"s": "god_id"}
    bot.send_message(m.chat.id, "👑 *GOD MODE: FUNDING*\nSend the Target *User ID*:", parse_mode="Markdown", reply_markup=cancel_kb())

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and user_states.get(ADMIN_ID, {}).get("s") == "god_id")
def god_funds_2(m):
    if m.text == "❌ Cancel Action": return cancel(m)
    user_states[ADMIN_ID].update({"s": "god_amt", "uid": int(m.text)})
    bot.send_message(m.chat.id, f"ID `{m.text}` saved.\n\n💸 *Send Amount:*\n(Send `100` to Add, or `-50` to Deduct)", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and user_states.get(ADMIN_ID, {}).get("s") == "god_amt")
def god_funds_3(m):
    if m.text == "❌ Cancel Action": return cancel(m)
    try:
        amt = float(m.text)
        uid = user_states[ADMIN_ID]["uid"]
        db_exec("UPDATE users SET balance = balance + ? WHERE user_id=?", (amt, uid))
        
        # Notify User
        if amt > 0: bot.send_message(uid, f"🎉 *WALLET UPDATE*\nAdmin added `₹{amt}` to your wallet!", parse_mode="Markdown")
        else: bot.send_message(uid, f"⚠️ *WALLET UPDATE*\nAdmin deducted `₹{abs(amt)}` from your wallet.", parse_mode="Markdown")
        
        bot.send_message(m.chat.id, f"✅ Done. Adjusted `{uid}` by `₹{amt}`.", parse_mode="Markdown", reply_markup=get_main_kb(ADMIN_ID))
    except: bot.send_message(m.chat.id, "Error. Ensure ID and amounts are numbers.", reply_markup=get_main_kb(ADMIN_ID))
    user_states.pop(ADMIN_ID, None)

# --- DIRECT MESSAGE ---
@bot.message_handler(func=lambda m: m.text == "📩 Direct Msg" and m.from_user.id == ADMIN_ID)
def dm_1(m):
    user_states[ADMIN_ID] = {"s": "dm_id"}
    bot.send_message(m.chat.id, "📩 *DIRECT MESSAGE*\nSend the Target *User ID*:", parse_mode="Markdown", reply_markup=cancel_kb())

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and user_states.get(ADMIN_ID, {}).get("s") == "dm_id")
def dm_2(m):
    if m.text == "❌ Cancel Action": return cancel(m)
    user_states[ADMIN_ID].update({"s": "dm_msg", "uid": int(m.text)})
    bot.send_message(m.chat.id, f"ID `{m.text}` saved. \n\n✍️ *Type your message:*", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and user_states.get(ADMIN_ID, {}).get("s") == "dm_msg")
def dm_3(m):
    if m.text == "❌ Cancel Action": return cancel(m)
    uid = user_states[ADMIN_ID]["uid"]
    try:
        bot.send_message(uid, f"📩 *Message from Admin:*\n\n{m.text}", parse_mode="Markdown")
        bot.send_message(m.chat.id, "✅ Message Delivered.", reply_markup=get_main_kb(ADMIN_ID))
    except: bot.send_message(m.chat.id, "❌ Delivery failed. User may have blocked the bot.", reply_markup=get_main_kb(ADMIN_ID))
    user_states.pop(ADMIN_ID, None)

# --- SMART BROADCAST ---
@bot.message_handler(func=lambda m: m.text == "📢 Broadcast Msg" and m.from_user.id == ADMIN_ID)
def broad_1(m):
    user_states[ADMIN_ID] = {"s": "broad_msg"}
    bot.send_message(m.chat.id, "📢 *BROADCAST SYSTEM*\nType the message you want to send to ALL users:", parse_mode="Markdown", reply_markup=cancel_kb())

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and user_states.get(ADMIN_ID, {}).get("s") == "broad_msg")
def broad_2(m):
    if m.text == "❌ Cancel Action": return cancel(m)
    msg_text = m.text
    bot.send_message(m.chat.id, "⏳ Broadcasting... Do not touch anything.", reply_markup=get_main_kb(ADMIN_ID))
    
    users = db_exec("SELECT user_id FROM users", fetch_all=True)
    sent = 0
    kb = InlineKeyboardMarkup().add(InlineKeyboardButton("🛒 Check Services", callback_data="buy_15979")) # Default service link
    
    for u in users:
        try:
            bot.send_message(u[0], f"📢 *OFFICIAL ANNOUNCEMENT*\n\n{msg_text}", parse_mode="Markdown", reply_markup=kb)
            sent += 1
            time.sleep(0.05) # Prevent Telegram Ban
        except: pass
    
    bot.send_message(m.chat.id, f"✅ Broadcast finished! Sent to {sent} users.")
    user_states.pop(ADMIN_ID, None)

# =======================================================================================
# 9. EXECUTION 
# =======================================================================================
if __name__ == '__main__':
    init_db()
    threading.Thread(target=lambda: bot.infinity_polling(timeout=20), daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
