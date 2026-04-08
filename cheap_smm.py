import telebot, requests, sqlite3, logging, time, urllib.parse, string, random, os, threading
from flask import Flask
from datetime import datetime, timedelta
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# 1. RENDER WEB SERVER (CRITICAL: Prevents Port-Binding errors)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
@app.route('/')
def home(): return "🔥 SMM Bot is 24/7 ONLINE! 🔥"

# 2. CONFIGURATION
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

# 3. DB MANAGER (Thread-Safe & Reliable)
def db_exec(query, params=(), fetch=False):
    with sqlite3.connect('panel_enterprise.db', check_same_thread=False, timeout=15) as conn:
        c = conn.cursor()
        c.execute(query, params)
        if fetch: return c.fetchone()
        conn.commit()
    return True

def init_db():
    queries = [
        "CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT, balance REAL DEFAULT 0.0, total_spent REAL DEFAULT 0.0, last_daily TIMESTAMP DEFAULT '2000-01-01 00:00:00', referred_by INTEGER DEFAULT 0, join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
        "CREATE TABLE IF NOT EXISTS transactions (tx_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount REAL, status TEXT, date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
        "CREATE TABLE IF NOT EXISTS orders (db_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, api_order_id TEXT, service_id INTEGER, link TEXT, quantity INTEGER, cost REAL, status TEXT DEFAULT 'Pending', date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
        "CREATE TABLE IF NOT EXISTS promo_codes (code TEXT PRIMARY KEY, amount REAL, max_uses INTEGER DEFAULT 1, current_uses INTEGER DEFAULT 0, created_by INTEGER)",
        "CREATE TABLE IF NOT EXISTS promo_redeems (user_id INTEGER, code TEXT, date TIMESTAMP DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY (user_id, code))"
    ]
    for q in queries: db_exec(q)

def get_u(uid, uname=None, fname=None, ref=0):
    u = db_exec("SELECT * FROM users WHERE user_id=?", (uid,), True)
    if not u and uname:
        db_exec("INSERT INTO users (user_id, username, first_name, referred_by) VALUES (?,?,?,?)", (uid, uname, fname, ref))
        u = db_exec("SELECT * FROM users WHERE user_id=?", (uid,), True)
    return u

# 4. API & KEYBOARDS
def get_services():
    try:
        res = requests.post(API_URL, data={'key': API_KEY, 'action': 'services'}, timeout=15).json()
        return {int(i['service']): {"name": i['name'], "rate": float(i['rate'])*MARKUP_PERCENTAGE, "min": int(i['min']), "max": int(i['max'])} for i in res if int(i['service']) in TARGET_IDS}
    except: return None

def main_kb():
    return ReplyKeyboardMarkup(resize_keyboard=True, row_width=2).add("🛒 Browse Services 🚀", "💰 My Drip (Profile)", "💳 Add Funds (Wallet)", "📦 Order History", "🎁 Daily Bonus", "🎫 Redeem Promo")

# 5. BOT LOGIC
@bot.message_handler(commands=['start'])
def start(m):
    ref = int(m.text.split()[1].replace('ref','')) if 'ref' in m.text else 0
    u = get_u(m.from_user.id, m.from_user.username, m.from_user.first_name, ref)
    bot.send_message(m.chat.id, f"⚡ *ENTERPRISE V4 ACTIVE*\n💰 Balance: `₹{u[3]:.2f}`", parse_mode="Markdown", reply_markup=main_kb())

@bot.message_handler(func=lambda m: m.text == "🛒 Browse Services 🚀")
def browse(m):
    data = get_services()
    if not data: return bot.send_message(m.chat.id, "❌ API Offline.")
    kb = InlineKeyboardMarkup(row_width=1)
    for sid, s in data.items(): kb.add(InlineKeyboardButton(f"🔥 {s['name']} - ₹{s['rate']:.2f}", callback_data=f"buy_{sid}"))
    bot.send_message(m.chat.id, "🛒 *SERVICES:*", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("buy_"))
def ask_link(c):
    user_states[c.from_user.id] = {"s": "link", "id": int(c.data.split("_")[1])}
    bot.send_message(c.message.chat.id, "🔗 *Send Link:*", parse_mode="Markdown", reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add("❌ Cancel Action"))

@bot.message_handler(func=lambda m: m.from_user.id in user_states)
def flow(m):
    if m.text == "❌ Cancel Action": 
        user_states.pop(m.from_user.id, None)
        return bot.send_message(m.chat.id, "Cancelled.", reply_markup=main_kb())
    
    uid = m.from_user.id
    st = user_states[uid]
    
    if st["s"] == "link":
        data = get_services()
        s = data[st["id"]]
        user_states[uid].update({"s": "qty", "l": m.text, "r": s['rate'], "min": s['min'], "max": s['max']})
        bot.send_message(m.chat.id, f"🔢 *Enter Qty* ({s['min']}-{s['max']}):")
        
    elif st["s"] == "qty":
        try:
            qty = int(m.text)
            if qty < st["min"] or qty > st["max"]: return bot.send_message(m.chat.id, "🚫 Out of limits.")
            cost = (qty/1000) * st["r"]
            if get_u(uid)[3] < cost: return bot.send_message(m.chat.id, "❌ Low Balance!")
            
            # API CALL
            res = requests.post(API_URL, data={'key': API_KEY, 'action': 'add', 'service': st["id"], 'link': st["l"], 'quantity': qty}, timeout=20).json()
            if 'order' in res:
                db_exec("UPDATE users SET balance = balance - ?, total_spent = total_spent + ? WHERE user_id=?", (cost, cost, uid))
                db_exec("INSERT INTO orders (user_id, api_order_id, service_id, link, quantity, cost) VALUES (?,?,?,?,?,?)", (uid, res['order'], st["id"], st["l"], qty, cost))
                bot.send_message(m.chat.id, f"✅ *ORDER SUCCESS!*\nID: `{res['order']}`", reply_markup=main_kb())
            else: bot.send_message(m.chat.id, f"❌ API Error: {res.get('error')}", reply_markup=main_kb())
        except: bot.send_message(m.chat.id, "❌ Failed.")
        user_states.pop(uid, None)

@bot.message_handler(func=lambda m: m.text == "💳 Add Funds (Wallet)")
def funds(m):
    user_states[m.from_user.id] = {"s": "amt"}
    bot.send_message(m.chat.id, "💸 *How much ₹?*")

@bot.message_handler(func=lambda m: m.from_user.id in user_states and user_states[m.from_user.id]["s"] == "amt")
def pay(m):
    try:
        amt = float(m.text)
        user_states[m.from_user.id] = {"s": "ss", "amt": amt}
        # TEXT ONLY - PREVENTS HANGING
        bot.send_message(m.chat.id, f"💳 *PAY ₹{amt} TO:*\n`{UPI_ID}`\n\n📸 *Send Screenshot now.*", parse_mode="Markdown")
    except: bot.send_message(m.chat.id, "Numbers only.")

@bot.message_handler(content_types=['photo'])
def handle_ss(m):
    if m.from_user.id in user_states and user_states[m.from_user.id]["s"] == "ss":
        amt = user_states[m.from_user.id]["amt"]
        db_exec("INSERT INTO transactions (user_id, amount, status) VALUES (?,?,'PENDING')", (m.from_user.id, amt))
        kb = InlineKeyboardMarkup().add(InlineKeyboardButton("✅ Approve", callback_data=f"ap_{m.from_user.id}_{amt}"))
        bot.send_photo(ADMIN_ID, m.photo[-1].file_id, caption=f"🚨 DEPOSIT: ₹{amt}\nID: `{m.from_user.id}`", reply_markup=kb)
        bot.send_message(m.chat.id, "⏳ Sent to Admin.", reply_markup=main_kb())
        user_states.pop(m.from_user.id, None)

@bot.callback_query_handler(func=lambda c: c.data.startswith("ap_"))
def approve(c):
    _, uid, amt = c.data.split("_")
    db_exec("UPDATE users SET balance = balance + ? WHERE user_id=?", (float(amt), int(uid)))
    bot.send_message(int(uid), f"🎉 Admin added ₹{amt}!")
    bot.edit_message_caption("✅ Approved", c.message.chat.id, c.message.message_id)

# 6. RUNNER
def run_bot():
    init_db()
    while True:
        try: bot.infinity_polling(timeout=20, long_polling_timeout=10)
        except: time.sleep(5)

if __name__ == '__main__':
    threading.Thread(target=run_bot, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
