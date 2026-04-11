import telebot, requests, sqlite3, logging, time, os, urllib.parse, threading
from io import BytesIO
from flask import Flask
from datetime import datetime
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)
@app.route('/')
def home(): return "🔥 V11 MASTER ONLINE 🔥"

BOT_TOKEN = '8228287584:AAEo7o4vYgRi5tCTUg4COzpo5DyS9LAgnWM'
API_KEY = 'rB105ycZUiN4wLIV7BUuOpGGZgWdbrXVw1jg1RKQ0hRbU30OEhi2Dnefb1Vqq430'
bot = telebot.TeleBot(BOT_TOKEN, threaded=True)

API_URL, ADMIN_ID, UPI_ID = "https://indiansmmprovider.in/api/v2", 6034840006, "rahikhann@fam"
CHANNEL_ID, CHANNEL_LINK, LOG_GROUP_ID = "@cspnotice", "https://t.me/cspnotice", "@csplogs"
user_states = {}

def execute_db(q, p=(), fetch=False, fetch_all=False):
    with sqlite3.connect('panel_v11.db', check_same_thread=False) as conn:
        c = conn.cursor()
        c.execute(q, p)
        if fetch: return c.fetchone()
        if fetch_all: return c.fetchall()
        conn.commit()
        return True

def init_database():
    execute_db("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT, balance REAL DEFAULT 0.0, total_spent REAL DEFAULT 0.0, is_banned INTEGER DEFAULT 0)")
    execute_db("CREATE TABLE IF NOT EXISTS managed_services (service_id INTEGER PRIMARY KEY, category TEXT, name TEXT, rate REAL, margin REAL DEFAULT 1.45)")
    execute_db("CREATE TABLE IF NOT EXISTS promos (code TEXT PRIMARY KEY, amount REAL, max_uses INTEGER, current_uses INTEGER DEFAULT 0)")
    execute_db("CREATE TABLE IF NOT EXISTS orders (db_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, api_order_id TEXT, cost REAL)")

def main_kb(uid):
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add("🛒 Browse Services 🚀", "💰 My Profile", "💳 Add Funds", "📦 Order History", "🎟️ Redeem Promo", "🎥 Tutorial")
    if uid == ADMIN_ID: kb.add("👑 ADMIN ZONE", "⚙️ Manage Services", "📈 Adjust Margins", "📢 Broadcast", "🎟️ Create Promo")
    return kb

@bot.message_handler(commands=['start'])
def start(m):
    if bot.get_chat_member(CHANNEL_ID, m.from_user.id).status in ['left']:
        return bot.send_message(m.chat.id, "🛑 Join @cspnotice first!", reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("Join", url=CHANNEL_LINK)))
    u = execute_db("SELECT * FROM users WHERE user_id=?", (m.from_user.id,), fetch=True)
    if not u: execute_db("INSERT INTO users (user_id, username) VALUES (?,?)", (m.from_user.id, m.from_user.username))
    bot.send_message(m.chat.id, "⚡ ENTERPRISE V11 MASTER", reply_markup=main_kb(m.from_user.id))

@bot.message_handler(func=lambda m: m.text == "🛒 Browse Services 🚀")
def browse(m):
    cats = execute_db("SELECT DISTINCT category FROM managed_services", fetch_all=True)
    kb = InlineKeyboardMarkup()
    for c in cats: kb.add(InlineKeyboardButton(c[0], callback_data=f"cat_{c[0]}"))
    bot.send_message(m.chat.id, "📁 Categories:", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("cat_"))
def show_svcs(c):
    cat = c.data.split("_")[1]
    svcs = execute_db("SELECT service_id, name, rate, margin FROM managed_services WHERE category=?", (cat,), fetch_all=True)
    kb = InlineKeyboardMarkup()
    for s in svcs: kb.add(InlineKeyboardButton(f"{s[1]} - ₹{s[2]*s[3]:.2f}", callback_data=f"buy_{s[0]}"))
    bot.edit_message_text(f"📁 {cat}", c.message.chat.id, c.message.message_id, reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("buy_"))
def buy_flow(c):
    sid = c.data.split("_")[1]
    user_states[c.from_user.id] = {"state": "link", "sid": sid}
    bot.send_message(c.message.chat.id, "🔗 Send Link:")

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get("state") == "link")
def get_link(m):
    user_states[m.from_user.id].update({"state": "qty", "link": m.text})
    bot.send_message(m.chat.id, "🔢 Enter Quantity:")

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get("state") == "qty")
def do_order(m):
    uid = m.from_user.id
    state = user_states[uid]
    qty = int(m.text)
    s_db = execute_db("SELECT rate, margin, name FROM managed_services WHERE service_id=?", (state["sid"],), fetch=True)
    cost = (qty/1000) * (s_db[0]*s_db[1])
    
    u = execute_db("SELECT balance FROM users WHERE user_id=?", (uid,), fetch=True)
    if u[0] < cost: return bot.send_message(m.chat.id, "❌ Low Balance")
    
    res = requests.post(API_URL, data={'key': API_KEY, 'action': 'add', 'service': state['sid'], 'link': state['link'], 'quantity': qty}).json()
    if 'order' in res:
        execute_db("UPDATE users SET balance=balance-?, total_spent=total_spent+? WHERE user_id=?", (cost, cost, uid))
        bot.send_message(m.chat.id, f"✅ Order Placed: {res['order']}")
        bot.send_message(LOG_GROUP_ID, f"🎉 NEW ORDER: {s_db[2]} ({qty}x)")
    user_states.pop(uid, None)

@bot.message_handler(func=lambda m: m.text == "💳 Add Funds")
def add_funds(m):
    user_states[m.from_user.id] = {"state": "amt"}
    bot.send_message(m.chat.id, "💸 Enter Amount (Min ₹10):")

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get("state") == "amt")
def qr_send(m):
    amt = m.text
    user_states[m.from_user.id] = {"state": "ss", "amt": amt}
    qr = f"https://api.qrserver.com/v1/create-qr-code/?size=400x400&data={urllib.parse.quote(f'upi://pay?pa={UPI_ID}&am={amt}')}"
    bot.send_photo(m.chat.id, requests.get(qr).content, caption=f"Pay ₹{amt} to {UPI_ID} and upload screenshot.")

@bot.message_handler(content_types=['photo'])
def ss_recv(m):
    if user_states.get(m.from_user.id, {}).get("state") == "ss":
        amt = user_states[m.from_user.id]["amt"]
        kb = InlineKeyboardMarkup().add(InlineKeyboardButton("Approve", callback_data=f"ap_{m.from_user.id}_{amt}"), InlineKeyboardButton("Reject", callback_data="rj"))
        bot.send_photo(ADMIN_ID, m.photo[-1].file_id, caption=f"Deposit: ₹{amt} from {m.from_user.id}", reply_markup=kb)
        bot.send_message(m.chat.id, "⏳ Pending Admin Approval.")
        user_states.pop(m.from_user.id, None)

@bot.callback_query_handler(func=lambda c: c.data.startswith("ap_"))
def admin_ap(c):
    _, uid, amt = c.data.split("_")
    execute_db("UPDATE users SET balance=balance+? WHERE user_id=?", (float(amt), int(uid)))
    bot.send_message(uid, f"✅ ₹{amt} Added!")
    bot.edit_message_caption("✅ Approved", c.message.chat.id, c.message.message_id)

@bot.message_handler(func=lambda m: m.text == "⚙️ Manage Services" and m.from_user.id == ADMIN_ID)
def admin_svc(m):
    user_states[ADMIN_ID] = {"state": "svc_cat"}
    bot.send_message(ADMIN_ID, "📁 Category Name:")

@bot.message_handler(func=lambda m: user_states.get(ADMIN_ID, {}).get("state") == "svc_cat")
def admin_svc_2(m):
    user_states[ADMIN_ID].update({"state": "svc_ids", "cat": m.text})
    bot.send_message(ADMIN_ID, "🔢 Enter Service IDs (Space separated):")

@bot.message_handler(func=lambda m: user_states.get(ADMIN_ID, {}).get("state") == "svc_ids")
def admin_svc_3(m):
    ids = m.text.split()
    api_svcs = requests.post(API_URL, data={'key': API_KEY, 'action': 'services'}).json()
    for sid in ids:
        s = next(i for i in api_svcs if i['service'] == sid)
        execute_db("INSERT OR REPLACE INTO managed_services (service_id, category, name, rate) VALUES (?,?,?,?)", (int(sid), user_states[ADMIN_ID]['cat'], s['name'], float(s['rate'])))
    bot.send_message(ADMIN_ID, "✅ Services Added!")
    user_states.pop(ADMIN_ID, None)

if __name__ == '__main__':
    threading.Thread(target=lambda: (init_database(), bot.infinity_polling()), daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
