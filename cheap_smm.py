import telebot, requests, sqlite3, logging, time, os, urllib.parse, threading
from io import BytesIO
from flask import Flask
from datetime import datetime
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# 1. SETUP & CONFIG
logging.basicConfig(level=logging.INFO)
app = Flask(__name__)
@app.route('/')
def home(): return "🔥 ENTERPRISE V11.2 MASTER ONLINE 🔥"

BOT_TOKEN = '8228287584:AAEo7o4vYgRi5tCTUg4COzpo5DyS9LAgnWM'
API_KEY = 'rB105ycZUiN4wLIV7BUuOpGGZgWdbrXVw1jg1RKQ0hRbU30OEhi2Dnefb1Vqq430'
bot = telebot.TeleBot(BOT_TOKEN, threaded=True)

API_URL, ADMIN_ID, UPI_ID = "https://indiansmmprovider.in/api/v2", 6034840006, "rahikhann@fam"
CHANNEL_ID, LOG_GROUP_ID = "-1002263433555", "@csplogs"
CHANNEL_LINK = "https://t.me/cspnotice"
user_states = {}

# 2. DATABASE ENGINE
def db(q, p=(), f=False, fa=False):
    with sqlite3.connect('panel_v11.db', check_same_thread=False) as conn:
        c = conn.cursor()
        c.execute(q, p)
        if f: return c.fetchone()
        if fa: return c.fetchall()
        conn.commit()
        return True

def init_db():
    db("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT, balance REAL DEFAULT 0.0, total_spent REAL DEFAULT 0.0, verified INTEGER DEFAULT 0, is_banned INTEGER DEFAULT 0)")
    db("CREATE TABLE IF NOT EXISTS managed_services (service_id INTEGER PRIMARY KEY, category TEXT, name TEXT, rate REAL, margin REAL DEFAULT 1.45, orders_count INTEGER DEFAULT 0)")
    db("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
    db("CREATE TABLE IF NOT EXISTS promos (code TEXT PRIMARY KEY, amount REAL, max_uses INTEGER, current_uses INTEGER DEFAULT 0)")
    db("CREATE TABLE IF NOT EXISTS promo_redeems (user_id INTEGER, code TEXT, PRIMARY KEY(user_id, code))")
    db("CREATE TABLE IF NOT EXISTS orders (db_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, api_order_id TEXT, cost REAL, date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    if not db("SELECT value FROM settings WHERE key='margin'", f=True): db("INSERT INTO settings VALUES ('margin', '1.45')")

# 3. HELPERS
def is_sub(uid):
    if uid == ADMIN_ID: return True
    try: return bot.get_chat_member(CHANNEL_ID, uid).status in ['member', 'administrator', 'creator']
    except: return True

def main_kb(uid):
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add("🛒 Browse Services 🚀", "💰 My Profile", "💳 Add Funds", "📦 Order History", "🎟️ Redeem Promo", "🎥 Tutorial", "⚖️ Compare")
    if uid == ADMIN_ID: kb.add("👑 ADMIN", "⚙️ Services", "📈 Margin", "📢 Broadcast", "🎟️ Create Promo", "🏦 Ledger")
    return kb

# 4. CORE HANDLERS
@bot.message_handler(commands=['start'])
def start(m):
    uid = m.from_user.id
    if not is_sub(uid):
        return bot.send_message(m.chat.id, "🛑 Join @cspnotice first!", reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("Join", url=CHANNEL_LINK)))
    u = db("SELECT balance, verified, is_banned FROM users WHERE user_id=?", (uid,), f=True)
    if not u: db("INSERT INTO users (user_id, username) VALUES (?,?)", (uid, m.from_user.username))
    elif u[2] == 1: return bot.send_message(m.chat.id, "🚫 Banned.")
    bot.send_message(m.chat.id, f"⚡ *ENTERPRISE V11.2*\n💰 Balance: `₹{u[0] if u else 0:.2f}`", parse_mode="Markdown", reply_markup=main_kb(uid))

# 5. ORDERING FLOW WITH STATS PREVIEW
@bot.message_handler(func=lambda m: m.text == "🛒 Browse Services 🚀")
def browse(m):
    cats = db("SELECT DISTINCT category FROM managed_services", fa=True)
    kb = InlineKeyboardMarkup(row_width=2)
    for c in cats: kb.add(InlineKeyboardButton(f"📁 {c[0]}", callback_data=f"cat_{c[0]}"))
    bot.send_message(m.chat.id, "📂 Select Category:", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("cat_"))
def show_svcs(c):
    cat = c.data.split("_")[1]
    svcs = db("SELECT service_id, name, rate, margin FROM managed_services WHERE category=?", (cat,), fa=True)
    kb = InlineKeyboardMarkup(row_width=1)
    for s in svcs: kb.add(InlineKeyboardButton(f"{s[1]} - ₹{s[2]*s[3]:.2f}", callback_data=f"stats_{s[0]}"))
    bot.edit_message_text(f"📁 {cat}", c.message.chat.id, c.message.message_id, reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("stats_"))
def show_stats(c):
    sid = int(c.data.split("_")[1])
    res = requests.post(API_URL, data={'key': API_KEY, 'action': 'services'}).json()
    s = next(i for i in res if int(i['service']) == sid)
    m = db("SELECT margin FROM managed_services WHERE service_id=?", (sid,), f=True)[0]
    msg = f"📊 *SERVICE STATS*\n━━━━━━━━━━━━\n🏷️ {s['name']}\n🆔 ID: `{sid}`\n💰 Price: `₹{float(s['rate'])*m:.2f}/1k`\n📉 Min: {s['min']} | Max: {s['max']}\n━━━━━━━━━━━━"
    kb = InlineKeyboardMarkup().add(InlineKeyboardButton("✅ Proceed", callback_data=f"buy_{sid}"), InlineKeyboardButton("❌ Back", callback_data="back_to_cats"))
    bot.edit_message_text(msg, c.message.chat.id, c.message.message_id, parse_mode="Markdown", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data == "back_to_cats")
def back_cats(c):
    try: bot.delete_message(c.message.chat.id, c.message.message_id)
    except: pass
    browse(c.message)

@bot.callback_query_handler(func=lambda c: c.data.startswith("buy_"))
def buy_init(c):
    sid = c.data.split("_")[1]
    user_states[c.from_user.id] = {"state": "link", "sid": sid}
    bot.send_message(c.message.chat.id, "🔗 Send Link:", reply_markup=ReplyKeyboardMarkup(True).add("❌ Cancel"))

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get("state") == "link")
def get_link(m):
    if m.text == "❌ Cancel": 
        user_states.pop(m.from_user.id, None)
        return bot.send_message(m.chat.id, "Cancelled.", reply_markup=main_kb(m.from_user.id))
    user_states[m.from_user.id].update({"state": "qty", "link": m.text})
    bot.send_message(m.chat.id, "🔢 Enter Quantity:")

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get("state") == "qty")
def get_qty(m):
    uid = m.from_user.id
    state = user_states[uid]
    try:
        qty = int(m.text)
        s_db = db("SELECT rate, margin, name FROM managed_services WHERE service_id=?", (state["sid"],), f=True)
        cost = (qty/1000) * (s_db[0]*s_db[1])
        u_bal = db("SELECT balance FROM users WHERE user_id=?", (uid,), f=True)[0]
        if u_bal < cost: return bot.send_message(m.chat.id, "❌ Low Balance", reply_markup=main_kb(uid))
        
        res = requests.post(API_URL, data={'key': API_KEY, 'action': 'add', 'service': state['sid'], 'link': state['link'], 'quantity': qty}).json()
        if 'order' in res:
            db("UPDATE users SET balance=balance-?, total_spent=total_spent+? WHERE user_id=?", (cost, cost, uid))
            bot.send_message(m.chat.id, f"✅ Order Placed: `{res['order']}`", parse_mode="Markdown", reply_markup=main_kb(uid))
            bot.send_message(LOG_GROUP_ID, f"🎉 *NEW ORDER*\n📦 {s_db[2]}\n🔢 Qty: {qty}\n👤 @{m.from_user.username}", parse_mode="Markdown")
        else: bot.send_message(m.chat.id, "❌ API Error.", reply_markup=main_kb(uid))
    except: bot.send_message(m.chat.id, "Error. Try again.")
    user_states.pop(uid, None)

# 6. ADD FUNDS
@bot.message_handler(func=lambda m: m.text == "💳 Add Funds")
def funds_1(m):
    user_states[m.from_user.id] = {"state": "amt"}
    bot.send_message(m.chat.id, "💸 Enter Amount (₹10+):", reply_markup=ReplyKeyboardMarkup(True).add("❌ Cancel"))

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get("state") == "amt")
def funds_2(m):
    try:
        amt = float(m.text)
        user_states[m.from_user.id] = {"state": "ss", "amt": amt}
        qr = f"https://api.qrserver.com/v1/create-qr-code/?size=400x400&data={urllib.parse.quote(f'upi://pay?pa={UPI_ID}&am={amt}')}"
        bot.send_photo(m.chat.id, requests.get(qr).content, caption=f"Pay ₹{amt} to `{UPI_ID}`\n📸 Send screenshot after payment.", parse_mode="Markdown")
    except: bot.send_message(m.chat.id, "Numbers only.")

@bot.message_handler(content_types=['photo'])
def ss_handler(m):
    if user_states.get(m.from_user.id, {}).get("state") == "ss":
        amt = user_states[m.from_user.id]["amt"]
        tx = db("INSERT INTO transactions (user_id, amount, status) VALUES (?,?,'PENDING')", (m.from_user.id, amt), return_id=True)
        kb = InlineKeyboardMarkup().add(InlineKeyboardButton("✅ Approve", callback_data=f"ap_{m.from_user.id}_{amt}"), InlineKeyboardButton("❌ Reject", callback_data="rj"))
        bot.send_photo(ADMIN_ID, m.photo[-1].file_id, caption=f"Deposit: ₹{amt} from {m.from_user.id}", reply_markup=kb)
        bot.send_message(m.chat.id, "⏳ Pending Approval.", reply_markup=main_kb(m.from_user.id))
        user_states.pop(m.from_user.id, None)

@bot.callback_query_handler(func=lambda c: c.data.startswith("ap_"))
def admin_ap(c):
    _, uid, amt = c.data.split("_")
    db("UPDATE users SET balance=balance+? WHERE user_id=?", (float(amt), int(uid)))
    try: bot.send_message(uid, f"✅ ₹{amt} Added to wallet!")
    except: pass
    bot.edit_message_caption("✅ Approved", c.message.chat.id, c.message.message_id)

# 7. ADMIN ZONE
@bot.message_handler(func=lambda m: m.text == "⚙️ Services" and m.from_user.id == ADMIN_ID)
def adm_svc(m):
    user_states[ADMIN_ID] = {"state": "s_cat"}
    bot.send_message(ADMIN_ID, "📁 Category Name:", reply_markup=ReplyKeyboardMarkup(True).add("❌ Cancel"))

@bot.message_handler(func=lambda m: user_states.get(ADMIN_ID, {}).get("state") == "s_cat")
def adm_svc_2(m):
    user_states[ADMIN_ID].update({"state": "s_ids", "cat": m.text})
    bot.send_message(ADMIN_ID, "🔢 Paste IDs (Space separated):")

@bot.message_handler(func=lambda m: user_states.get(ADMIN_ID, {}).get("state") == "s_ids")
def adm_svc_3(m):
    ids = m.text.split()
    api_svcs = requests.post(API_URL, data={'key': API_KEY, 'action': 'services'}).json()
    margin = float(db("SELECT value FROM settings WHERE key='margin'", f=True)[0])
    for sid in ids:
        s = next(i for i in api_svcs if str(i['service']) == sid.strip())
        db("INSERT OR REPLACE INTO managed_services (service_id, category, name, rate, margin) VALUES (?,?,?,?,?)", (int(sid), user_states[ADMIN_ID]['cat'], s['name'], float(s['rate']), margin))
    bot.send_message(ADMIN_ID, f"✅ Added {len(ids)} services.", reply_markup=main_kb(ADMIN_ID))
    user_states.pop(ADMIN_ID, None)

@bot.message_handler(commands=['addbal', 'verify', 'ban'])
def admin_cmds(m):
    if m.from_user.id != ADMIN_ID: return
    p = m.text.split()
    if '/addbal' in m.text: db("UPDATE users SET balance=balance+? WHERE user_id=?", (float(p[2]), int(p[1])))
    elif '/verify' in m.text: db("UPDATE users SET verified=1 WHERE user_id=?", (int(p[1]),))
    elif '/ban' in m.text: db("UPDATE users SET is_banned=1 WHERE user_id=?", (int(p[1]),))
    bot.send_message(ADMIN_ID, "✅ Success.")

if __name__ == '__main__':
    threading.Thread(target=lambda: (init_db(), bot.infinity_polling()), daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
