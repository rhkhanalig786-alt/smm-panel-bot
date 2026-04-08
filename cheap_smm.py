import telebot, requests, sqlite3, logging, time, urllib.parse, os, threading
from datetime import datetime, timedelta
from flask import Flask
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# 1. SETUP & ENV
logging.basicConfig(level=logging.INFO)
BOT_TOKEN = os.environ.get('8228287584:AAFa93-H1WLx-sY_JNO3XJmeqzOogPImhqM')
API_KEY = os.environ.get('iyQl8EohC0u3Be7I6FTh054FUHBJPRVE761vsZB02dNF5kkSznjVfNGThZfoYRhN')
bot = telebot.TeleBot(BOT_TOKEN)
API_URL, ADMIN_ID = "https://indiansmmprovider.in/api/v2", 6034840006
SUPPORT, UPI = "@Not_your_rahi", "rahikhann@fam"
TARGET_IDS = [15979, 16411, 16453, 16441, 16439, 15397, 16451, 15843]
states = {}

# 2. DATABASE CORE
def db_query(query, params=(), fetch=False):
    with sqlite3.connect('panel.db', check_same_thread=False) as conn:
        cursor = conn.execute(query, params)
        return cursor.fetchall() if fetch else conn.commit()

def init_db():
    db_query("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, user TEXT, bal REAL DEFAULT 0, spent REAL DEFAULT 0, daily TEXT DEFAULT '2000-01-01')")
    db_query("CREATE TABLE IF NOT EXISTS tx (id INTEGER PRIMARY KEY AUTOINCREMENT, uid INTEGER, amt REAL, status TEXT)")
    db_query("CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY, uid INTEGER, api_id TEXT, cost REAL)")

# 3. API & LOGIC
def get_services():
    try:
        res = requests.post(API_URL, data={'key': API_KEY, 'action': 'services'}).json()
        return {int(i['service']): {"n": i['name'], "r": float(i['rate'])*1.45, "m": i['min']} for i in res if int(i['service']) in TARGET_IDS}
    except: return None

def get_kb():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🛒 Browse Services 🚀", "💰 My Drip", "💳 Add Funds", "🎁 Daily Bonus", "📞 Support")
    return markup

# 4. HANDLERS
@bot.message_handler(commands=['start'])
def start(m):
    db_query("INSERT OR IGNORE INTO users (id, user) VALUES (?,?)", (m.from_user.id, m.from_user.first_name))
    u = db_query("SELECT bal FROM users WHERE id=?", (m.from_user.id,), True)[0]
    bot.send_message(m.chat.id, f"⚡ *WELCOME TO THE PLUG!*\n💰 Balance: `₹{u[0]:.2f}`\n🆔 ID: `{m.from_user.id}`", parse_mode="Markdown", reply_markup=get_kb())

@bot.message_handler(func=lambda m: m.text == "🛒 Browse Services 🚀")
def browse(m):
    data = get_services()
    if not data: return bot.send_message(m.chat.id, "API acting sus. Try later.")
    kb = InlineKeyboardMarkup(row_width=1)
    for s_id, s in data.items():
        kb.add(InlineKeyboardButton(f"🔥 {s['n']} - ₹{s['r']:.2f}", callback_data=f"buy_{s_id}"))
    bot.send_message(m.chat.id, "🛒 *THE MAIN ROSTER:*", parse_mode="Markdown", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("buy_"))
def buy(c):
    s_id = int(c.data.split("_")[1])
    states[c.from_user.id] = {"s": "link", "id": s_id}
    bot.send_message(c.message.chat.id, "🔗 *Send Target Link:*", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.from_user.id in states)
def handle_flow(m):
    u_id, data = m.from_user.id, states[u_id]
    if data["s"] == "link":
        states[u_id].update({"s": "qty", "l": m.text})
        bot.send_message(m.chat.id, "🔢 *How many?*")
    elif data["s"] == "qty":
        try:
            qty = int(m.text)
            srv = get_services()[data["id"]]
            cost = (qty/1000) * srv["r"]
            bal = db_query("SELECT bal FROM users WHERE id=?", (u_id,), True)[0][0]
            if bal < cost: return bot.send_message(m.chat.id, "❌ Low balance!")
            res = requests.post(API_URL, data={'key': API_KEY, 'action': 'add', 'service': data["id"], 'link': data["l"], 'quantity': qty}).json()
            if 'order' in res:
                db_query("UPDATE users SET bal = bal - ?, spent = spent + ? WHERE id=?", (cost, cost, u_id))
                bot.send_message(m.chat.id, f"✅ *ORDER PLACED!* ID: `{res['order']}`\nStarts in 30 mins. 🚀", parse_mode="Markdown", reply_markup=get_kb())
            else: bot.send_message(m.chat.id, "❌ API Error.")
        except: bot.send_message(m.chat.id, "❌ Error.")
        del states[u_id]

@bot.message_handler(func=lambda m: m.text == "💳 Add Funds")
def add_funds(m):
    states[m.from_user.id] = {"s": "pay"}
    bot.send_message(m.chat.id, "💸 *Amount to add?*")

@bot.message_handler(func=lambda m: m.from_user.id in states and states[m.from_user.id]["s"] == "pay")
def pay(m):
    amt = m.text
    qr = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={urllib.parse.quote(f'upi://pay?pa={UPI}&am={amt}&cu=INR')}"
    bot.send_photo(m.chat.id, qr, caption=f"💳 Pay ₹{amt} to `{UPI}`\n📸 Send Screenshot now.")
    states[m.from_user.id] = {"s": "ss", "a": float(amt)}

@bot.message_handler(content_types=['photo'])
def ss(m):
    if m.from_user.id in states and states[m.from_user.id]["s"] == "ss":
        amt = states[m.from_user.id]["a"]
        kb = InlineKeyboardMarkup().add(InlineKeyboardButton("✅ Approve", callback_data=f"ap_{m.from_user.id}_{amt}"), InlineKeyboardButton("❌ Reject", callback_data="rj"))
        bot.send_photo(ADMIN_ID, m.photo[-1].file_id, caption=f"🚨 DEP: ₹{amt} from {m.from_user.id}", reply_markup=kb)
        bot.send_message(m.chat.id, "⏳ Sent to Admin.", reply_markup=get_kb())
        del states[m.from_user.id]

@bot.callback_query_handler(func=lambda c: c.data.startswith("ap_"))
def approve(c):
    _, u_id, amt = c.data.split("_")
    db_query("UPDATE users SET bal = bal + ? WHERE id=?", (float(amt), int(u_id)))
    bot.send_message(int(u_id), f"🎉 Added ₹{amt}!")
    bot.edit_message_caption("✅ Approved", c.message.chat.id, c.message.message_id)

# 5. RENDER SERVER
app = Flask(__name__)
@app.route('/')
def home(): return "ONLINE"

def run_bot():
    init_db()
    while True:
        try: bot.infinity_polling()
        except: time.sleep(5)

if __name__ == '__main__':
    threading.Thread(target=run_bot).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
