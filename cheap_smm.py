"""
=========================================================================================
🔥 CHEAP SMM PANEL BOT - BULLETPROOF ENTERPRISE V8.3 🔥
Fix: Flawless Dynamic QR Code Generation & Memory Buffer Fix
=========================================================================================
"""

import telebot
import requests
import sqlite3
import logging
import time
import string
import random
import os
import urllib.parse
import threading
from io import BytesIO
from flask import Flask
from datetime import datetime, timedelta
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# =======================================================================================
# 1. SERVER, LOGGING & CONFIGURATION
# =======================================================================================
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
@app.route('/')
def home(): 
    return "🔥 V8.3 MASTER CONTROL IS ONLINE 🔥"

BOT_TOKEN = os.environ.get('BOT_TOKEN', '8228287584:AAHcMXNJpqHkYZQJhoOX45L9YioMAh7wzaY')
API_KEY = os.environ.get('API_KEY', 'w4NIpEsjLOWxMM87R0ZxiPeMgu2ri8ugJeYPmMa206aPmOhDu9NJSl13mvQvPUEZ')
bot = telebot.TeleBot(BOT_TOKEN)

API_URL = "https://indiansmmprovider.in/api/v2"
ADMIN_ID = 6034840006  
UPI_ID = "rahikhann@fam"

MIN_DEPOSIT = 10.0          
LOW_BAL_ALERT = 15.0        
REFERRAL_BONUS = 5.0        
DAILY_BONUS_AMT = 1.0       

user_states = {}

# =======================================================================================
# 2. THREAD-SAFE DATABASE ENGINE
# =======================================================================================
def execute_db(query, params=(), fetch=False, fetch_all=False, return_id=False):
    try:
        with sqlite3.connect('panel_enterprise.db', check_same_thread=False, timeout=20) as conn:
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
        logger.error(f"DB Error: {e} | Query: {query}")
        return False

def init_database():
    execute_db('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT, 
        balance REAL DEFAULT 0.0, total_spent REAL DEFAULT 0.0, 
        last_daily TIMESTAMP DEFAULT '2000-01-01 00:00:00', 
        referred_by INTEGER DEFAULT 0, join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    execute_db('''CREATE TABLE IF NOT EXISTS transactions (
        tx_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount REAL, 
        status TEXT, date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    execute_db('''CREATE TABLE IF NOT EXISTS orders (
        db_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, api_order_id TEXT, 
        service_id INTEGER, quantity INTEGER, cost REAL, date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    execute_db('''CREATE TABLE IF NOT EXISTS managed_services (
        service_id INTEGER PRIMARY KEY, category TEXT, name TEXT, rate REAL, margin REAL DEFAULT 1.45
    )''')
    execute_db('''CREATE TABLE IF NOT EXISTS tickets (
        ticket_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, message TEXT, 
        status TEXT DEFAULT 'OPEN', date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    execute_db('''CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY, value TEXT
    )''')
    
    if not execute_db("SELECT value FROM settings WHERE key='global_margin'", fetch=True):
        execute_db("INSERT INTO settings (key, value) VALUES ('global_margin', '1.45')")

# =======================================================================================
# 3. UTILITY FUNCTIONS & API MANAGER
# =======================================================================================
def get_global_margin():
    row = execute_db("SELECT value FROM settings WHERE key='global_margin'", fetch=True)
    return float(row[0]) if row else 1.45

def get_or_create_user(user_id, username=None, first_name=None, ref_by=0):
    user = execute_db("SELECT * FROM users WHERE user_id=?", (user_id,), fetch=True)
    if not user and username is not None:
        execute_db("INSERT INTO users (user_id, username, first_name, referred_by) VALUES (?, ?, ?, ?)", (user_id, username, first_name, ref_by))
        if ref_by != 0 and ref_by != user_id:
            try: bot.send_message(ref_by, f"🎉 *New Referral!* {first_name} joined using your link!", parse_mode="Markdown")
            except: pass
        user = execute_db("SELECT * FROM users WHERE user_id=?", (user_id,), fetch=True)
    return user

def call_smm_api(action, extra_data=None):
    payload = {'key': API_KEY, 'action': action}
    if extra_data: payload.update(extra_data)
    try: return requests.post(API_URL, data=payload, timeout=20).json()
    except Exception: return None

# =======================================================================================
# 4. KEYBOARD GENERATORS
# =======================================================================================
def generate_main_keyboard(user_id):
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(KeyboardButton("🛒 Browse Services 🚀"), KeyboardButton("💰 My Drip (Profile)"))
    kb.add(KeyboardButton("💳 Add Funds (Wallet)"), KeyboardButton("📦 Order History"))
    kb.add(KeyboardButton("🎁 Daily Bonus"), KeyboardButton("📞 Support / Tickets"))
    
    if user_id == ADMIN_ID:
        kb.add(KeyboardButton("👑 --- ADMIN ZONE --- 👑"))
        kb.add(KeyboardButton("⚙️ Manage Services"), KeyboardButton("📈 Adjust Margins"))
        kb.add(KeyboardButton("💰 God Mode Funds"), KeyboardButton("📢 Broadcast"))
        kb.add(KeyboardButton("🎟️ Open Tickets"), KeyboardButton("📩 Direct Msg"))
    return kb

def cancel_keyboard():
    return ReplyKeyboardMarkup(resize_keyboard=True).add(KeyboardButton("❌ Cancel Action"))

# =======================================================================================
# 5. CORE HANDLERS
# =======================================================================================
@bot.message_handler(commands=['start'])
def handle_start(message):
    user_id = message.from_user.id
    ref_by = 0
    if len(message.text.split()) > 1 and message.text.split()[1].startswith('ref'):
        try: ref_by = int(message.text.split()[1].replace('ref', ''))
        except: pass

    user_states.pop(user_id, None) 
    user = get_or_create_user(user_id, message.from_user.username, message.from_user.first_name, ref_by)
    
    msg = (f"⚡ *WELCOME TO ENTERPRISE V8.3* ⚡\n\n💰 *Wallet:* `₹{user[3]:.2f}`\n\nUse the menu below to navigate.")
    bot.send_message(message.chat.id, msg, parse_mode="Markdown", reply_markup=generate_main_keyboard(user_id))

@bot.message_handler(func=lambda m: m.text in ["❌ Cancel Action", "👑 --- ADMIN ZONE --- 👑"])
def handle_cancel(message):
    user_states.pop(message.from_user.id, None)
    if message.text == "❌ Cancel Action":
        bot.send_message(message.chat.id, "🚫 Action Cancelled.", reply_markup=generate_main_keyboard(message.from_user.id))

# =======================================================================================
# 6. USER PROFILE & DAILY BONUS
# =======================================================================================
@bot.message_handler(func=lambda m: m.text == "💰 My Drip (Profile)")
def handle_profile(message):
    user = get_or_create_user(message.from_user.id)
    text = (f"💧 *USER PROFILE* 💧\n━━━━━━━━━━━━━━━━━━━\n🆔 *ID:* `{user[0]}`\n💰 *Balance:* `₹{user[3]:.2f}`\n"
            f"📈 *Total Spent:* `₹{user[4]:.2f}`\n━━━━━━━━━━━━━━━━━━━\n"
            f"🤝 *REFERRAL LINK*\nEarn `₹{REFERRAL_BONUS}` per active invite!\n🔗 `https://t.me/{bot.get_me().username}?start=ref{user[0]}`")
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🎁 Daily Bonus")
def handle_daily_bonus(message):
    uid = message.from_user.id
    user = get_or_create_user(uid)
    last_claim = datetime.strptime(user[5], '%Y-%m-%d %H:%M:%S')
    
    if datetime.now() - last_claim > timedelta(days=1):
        execute_db("UPDATE users SET balance = balance + ?, last_daily = CURRENT_TIMESTAMP WHERE user_id = ?", (DAILY_BONUS_AMT, uid))
        bot.send_message(message.chat.id, f"🎉 *Claimed!* `₹{DAILY_BONUS_AMT:.2f}` added.", parse_mode="Markdown")
    else:
        bot.send_message(message.chat.id, "🛑 You already claimed today. Come back tomorrow.", parse_mode="Markdown")

# =======================================================================================
# 7. CATEGORY BROWSING & ORDERING
# =======================================================================================
@bot.message_handler(func=lambda m: m.text == "🛒 Browse Services 🚀")
def handle_browse_categories(message):
    categories = execute_db("SELECT DISTINCT category FROM managed_services", fetch_all=True)
    if not categories: return bot.send_message(message.chat.id, "⚠️ Store is empty.")
    
    kb = InlineKeyboardMarkup(row_width=2)
    for cat in categories: kb.add(InlineKeyboardButton(f"📁 {cat[0]}", callback_data=f"cat_{cat[0]}"))
    bot.send_message(message.chat.id, "🛒 *SELECT A CATEGORY:*", parse_mode="Markdown", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("cat_"))
def handle_show_services(call):
    bot.answer_callback_query(call.id)
    category = call.data.split("_", 1)[1]
    services = execute_db("SELECT service_id, name, rate, margin FROM managed_services WHERE category=?", (category,), fetch_all=True)
    
    kb = InlineKeyboardMarkup(row_width=1)
    for s in services: kb.add(InlineKeyboardButton(f"🔥 {s[1]} - ₹{s[2]*s[3]:.2f}/1k", callback_data=f"buy_{s[0]}"))
    kb.add(InlineKeyboardButton("⬅️ Back to Categories", callback_data="back_cats"))
    bot.edit_message_text(f"📁 *{category.upper()} SERVICES*", call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data == "back_cats")
def handle_back_categories(call):
    bot.answer_callback_query(call.id)
    try: bot.delete_message(call.message.chat.id, call.message.message_id)
    except: pass
    handle_browse_categories(call.message)

@bot.callback_query_handler(func=lambda c: c.data.startswith("buy_"))
def handle_buy_start(call):
    bot.answer_callback_query(call.id)
    user_states[call.from_user.id] = {"state": "order_link", "service_id": int(call.data.split("_")[1])}
    try: bot.delete_message(call.message.chat.id, call.message.message_id)
    except: pass
    bot.send_message(call.message.chat.id, "🔗 *STEP 1: Send Target Link*", parse_mode="Markdown", reply_markup=cancel_keyboard())

@bot.message_handler(func=lambda m: m.from_user.id in user_states and user_states[m.from_user.id].get("state") == "order_link")
def handle_order_link(message):
    if message.text == "❌ Cancel Action": return handle_cancel(message)
    uid = message.from_user.id
    
    api_res = call_smm_api('services')
    if not api_res: return bot.send_message(message.chat.id, "❌ API Error.", reply_markup=generate_main_keyboard(uid))
        
    try:
        s_data = next(i for i in api_res if int(i['service']) == user_states[uid]["service_id"])
        user_states[uid].update({"state": "order_qty", "link": message.text, "min": int(s_data['min']), "max": int(s_data['max'])})
        bot.send_message(message.chat.id, f"🔢 *STEP 2: Enter Quantity*\n📉 Min: `{s_data['min']}` | 📈 Max: `{s_data['max']}`", parse_mode="Markdown")
    except Exception: bot.send_message(message.chat.id, "❌ Service error.", reply_markup=generate_main_keyboard(uid))

@bot.message_handler(func=lambda m: m.from_user.id in user_states and user_states[m.from_user.id].get("state") == "order_qty")
def handle_order_qty(message):
    if message.text == "❌ Cancel Action": return handle_cancel(message)
    uid = message.from_user.id
    state = user_states[uid]
    
    try: qty = int(message.text)
    except: return bot.send_message(message.chat.id, "🤨 Numbers only.")
        
    if qty < state["min"] or qty > state["max"]: return bot.send_message(message.chat.id, f"🚫 Limits: {state['min']} - {state['max']}.")
        
    s_db = execute_db("SELECT rate, margin FROM managed_services WHERE service_id=?", (state["service_id"],), fetch=True)
    cost = (qty / 1000.0) * (s_db[0] * s_db[1])
    
    user = get_or_create_user(uid)
    if user[3] < cost: return bot.send_message(message.chat.id, f"❌ Need `₹{cost:.2f}`", parse_mode="Markdown", reply_markup=generate_main_keyboard(uid))
        
    msg_wait = bot.send_message(message.chat.id, "⏳ *Processing...*", parse_mode="Markdown", reply_markup=generate_main_keyboard(uid))
    api_res = call_smm_api('add', {'service': state["service_id"], 'link': state["link"], 'quantity': qty})
    
    try: bot.delete_message(message.chat.id, msg_wait.message_id)
    except: pass

    if api_res and 'order' in api_res:
        execute_db("UPDATE users SET balance=balance-?, total_spent=total_spent+? WHERE user_id=?", (cost, cost, uid))
        execute_db("INSERT INTO orders (user_id, api_order_id, service_id, quantity, cost) VALUES (?,?,?,?,?)", (uid, api_res['order'], state["service_id"], qty, cost))
        bot.send_message(message.chat.id, f"✅ *ORDER PLACED*\n🧾 ID: `{api_res['order']}`\n💰 Cost: `₹{cost:.2f}`", parse_mode="Markdown")
    else: bot.send_message(message.chat.id, "❌ *Provider Error*", parse_mode="Markdown")

    user_states.pop(uid, None)

# =======================================================================================
# 8. THE FAIL-PROOF QR ENGINE (V8.3 FULL FIX)
# =======================================================================================
@bot.message_handler(func=lambda m: m.text == "💳 Add Funds (Wallet)")
def handle_add_funds(message):
    user_states[message.from_user.id] = {"state": "fund_amount"}
    bot.send_message(message.chat.id, f"💸 *Enter deposit amount (₹):*\n(Min: `₹{MIN_DEPOSIT}`)", parse_mode="Markdown", reply_markup=cancel_keyboard())

@bot.message_handler(func=lambda m: m.from_user.id in user_states and user_states[m.from_user.id].get("state") == "fund_amount")
def handle_qr_generation(message):
    if message.text == "❌ Cancel Action": return handle_cancel(message)
    uid = message.from_user.id
    
    try:
        amt = float(message.text)
        if amt < MIN_DEPOSIT: 
            return bot.send_message(message.chat.id, f"🚫 Minimum deposit is `₹{MIN_DEPOSIT}`.", parse_mode="Markdown")
            
        user_states[uid] = {"state": "fund_screenshot", "amount": amt}
        
        # 1. SEND TEXT INSTRUCTIONS FIRST
        instruction_msg = (f"💳 *PAYMENT INSTRUCTIONS*\n\n"
                           f"1️⃣ Amount to pay: `₹{amt}`\n"
                           f"2️⃣ UPI ID: `{UPI_ID}`\n\n"
                           f"📸 *AFTER PAYING: Upload your screenshot here.*")
        bot.send_message(message.chat.id, instruction_msg, parse_mode="Markdown", reply_markup=cancel_keyboard())
        
        # 2. SHOW TYPING STATUS & GENERATE QR
        bot.send_chat_action(message.chat.id, 'upload_photo')
        
        upi_uri = f"upi://pay?pa={UPI_ID}&pn=SMM+Panel&am={amt}&cu=INR"
        encoded_uri = urllib.parse.quote(upi_uri)
        qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=400x400&data={encoded_uri}"
        
        try:
            response = requests.get(qr_url, timeout=10)
            if response.status_code == 200:
                img_stream = BytesIO(response.content)
                img_stream.seek(0) # CRITICAL FIX: Rewinds the image so Telegram doesn't crash
                bot.send_photo(message.chat.id, img_stream, caption="☝️ *Scan this QR to auto-fill the exact amount.*", parse_mode="Markdown")
            else:
                bot.send_message(message.chat.id, "⚠️ _Could not generate QR. Please manually copy the UPI ID above._", parse_mode="Markdown")
        except Exception as e:
            logger.error(f"QR API Error: {e}")
            bot.send_message(message.chat.id, "⚠️ _QR Service busy. Please use the UPI ID above._", parse_mode="Markdown")

    except ValueError: 
        bot.send_message(message.chat.id, "🤨 Please enter numbers only (e.g., 50).")
    except Exception as e:
        logger.error(f"Add Funds Error: {e}")
        bot.send_message(message.chat.id, "❌ System Error. Returning to Menu.", reply_markup=generate_main_keyboard(uid))
        user_states.pop(uid, None)

@bot.message_handler(content_types=['photo'])
def handle_screenshot(message):
    uid = message.from_user.id
    if uid in user_states and user_states[uid].get("state") == "fund_screenshot":
        amt = user_states[uid]["amount"]
        tx_id = execute_db("INSERT INTO transactions (user_id, amount, status) VALUES (?, ?, 'PENDING')", (uid, amt), return_id=True)
        kb = InlineKeyboardMarkup().add(InlineKeyboardButton("✅ Apprv", callback_data=f"esc_ap_{tx_id}_{uid}_{amt}"), InlineKeyboardButton("❌ Rjt", callback_data=f"esc_rj_{tx_id}_{uid}"))
        bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=f"🚨 *DEP*\n🆔 `{uid}`\n💰 `₹{amt}`\n🧾 `TXN-{tx_id}`", parse_mode="Markdown", reply_markup=kb)
        bot.send_message(message.chat.id, "⏳ Sent to Admin.", reply_markup=generate_main_keyboard(uid))
        user_states.pop(uid, None)

@bot.callback_query_handler(func=lambda c: c.data.startswith("esc_"))
def handle_escrow(call):
    if call.from_user.id != ADMIN_ID: return
    bot.answer_callback_query(call.id)
    parts = call.data.split("_")
    action, tx_id, uid = parts[1], int(parts[2]), int(parts[3])
    
    if action == "ap":
        amt = float(parts[4])
        execute_db("UPDATE users SET balance = balance + ? WHERE user_id=?", (amt, uid))
        execute_db("UPDATE transactions SET status = 'APPROVED' WHERE tx_id=?", (tx_id,))
        bot.edit_message_caption(f"✅ APPROVED TXN-{tx_id} | Added ₹{amt}", call.message.chat.id, call.message.message_id)
        try: bot.send_message(uid, f"🎉 *APPROVED!* `₹{amt}` added.", parse_mode="Markdown")
        except: pass
    else:
        execute_db("UPDATE transactions SET status = 'REJECTED' WHERE tx_id=?", (tx_id,))
        bot.edit_message_caption(f"❌ REJECTED TXN-{tx_id}", call.message.chat.id, call.message.message_id)

# =======================================================================================
# 9. ORDER HISTORY & TICKETS
# =======================================================================================
@bot.message_handler(func=lambda m: m.text == "📦 Order History")
def handle_history(m):
    orders = execute_db("SELECT api_order_id, quantity, cost, date FROM orders WHERE user_id=? ORDER BY date DESC LIMIT 4", (m.from_user.id,), fetch_all=True)
    if not orders: return bot.send_message(m.chat.id, "No orders.")
    kb = InlineKeyboardMarkup()
    text = "📦 *ORDERS*\n\n"
    for o in orders:
        text += f"🧾 `{o[0]}` | Qty: {o[1]} | `₹{o[2]:.2f}`\n"
        kb.add(InlineKeyboardButton(f"🔄 Track {o[0]}", callback_data=f"track_{o[0]}"))
    bot.send_message(m.chat.id, text, parse_mode="Markdown", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("track_"))
def handle_track(c):
    res = call_smm_api('status', {'order': c.data.split("_")[1]})
    if res and 'status' in res: bot.send_message(c.message.chat.id, f"📊 *STATUS:* `{res['status'].upper()}`\n📉 Remains: `{res.get('remains', 'N/A')}`", parse_mode="Markdown")
    else: bot.answer_callback_query(c.id, "Unavailable.", show_alert=True)
    bot.answer_callback_query(c.id)

@bot.message_handler(func=lambda m: m.text == "📞 Support / Tickets")
def handle_support(m):
    kb = InlineKeyboardMarkup().add(InlineKeyboardButton("📝 Open Ticket", callback_data="new_ticket"))
    bot.send_message(m.chat.id, "🛠️ *SUPPORT*", parse_mode="Markdown", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data == "new_ticket")
def start_ticket(c):
    bot.answer_callback_query(c.id)
    user_states[c.from_user.id] = {"state": "ticket_msg"}
    bot.send_message(c.message.chat.id, "📝 *Type issue:*", parse_mode="Markdown", reply_markup=cancel_keyboard())

@bot.message_handler(func=lambda m: m.from_user.id in user_states and user_states[m.from_user.id].get("state") == "ticket_msg")
def save_ticket(m):
    if m.text == "❌ Cancel Action": return handle_cancel(m)
    uid = m.from_user.id
    tid = execute_db("INSERT INTO tickets (user_id, message) VALUES (?, ?)", (uid, m.text), return_id=True)
    kb = InlineKeyboardMarkup().add(InlineKeyboardButton(f"Reply #{tid}", callback_data=f"rep_t_{tid}_{uid}"))
    bot.send_message(ADMIN_ID, f"🚨 *TICKET #{tid}* (`{uid}`)\n💬 {m.text}", parse_mode="Markdown", reply_markup=kb)
    bot.send_message(m.chat.id, f"✅ Ticket #{tid} Sent.", reply_markup=generate_main_keyboard(uid))
    user_states.pop(uid, None)

@bot.message_handler(func=lambda m: m.text == "🎟️ Open Tickets" and m.from_user.id == ADMIN_ID)
def view_tickets(m):
    tickets = execute_db("SELECT ticket_id, user_id, message FROM tickets WHERE status='OPEN'", fetch_all=True)
    if not tickets: return bot.send_message(m.chat.id, "✅ No open tickets.")
    for t in tickets:
        kb = InlineKeyboardMarkup().add(InlineKeyboardButton(f"Reply #{t[0]}", callback_data=f"rep_t_{t[0]}_{t[1]}"))
        bot.send_message(m.chat.id, f"🚨 *TICKET #{t[0]}* (`{t[1]}`)\n💬 {t[2]}", parse_mode="Markdown", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("rep_t_"))
def reply_ticket(c):
    if c.from_user.id != ADMIN_ID: return
    bot.answer_callback_query(c.id)
    _, _, tid, uid = c.data.split("_")
    user_states[ADMIN_ID] = {"state": "admin_reply", "tid": tid, "uid": int(uid)}
    bot.send_message(ADMIN_ID, f"✍️ *Reply to #{tid}:*", parse_mode="Markdown", reply_markup=cancel_keyboard())

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and user_states.get(ADMIN_ID, {}).get("state") == "admin_reply")
def send_ticket_reply(m):
    if m.text == "❌ Cancel Action": return handle_cancel(m)
    tid = user_states[ADMIN_ID]["tid"]
    uid = user_states[ADMIN_ID]["uid"]
    execute_db("UPDATE tickets SET status = 'CLOSED' WHERE ticket_id=?", (tid,))
    try: bot.send_message(uid, f"📩 *SUPPORT REPLY (#{tid})*\n\n{m.text}", parse_mode="Markdown")
    except: pass
    bot.send_message(ADMIN_ID, "✅ Sent.", reply_markup=generate_main_keyboard(ADMIN_ID))
    user_states.pop(ADMIN_ID, None)

# =======================================================================================
# 10. ADMIN ZONE - CATEGORIES, SERVICES & MARGINS
# =======================================================================================
@bot.message_handler(func=lambda m: m.text == "⚙️ Manage Services" and m.from_user.id == ADMIN_ID)
def handle_manage_svc(m):
    kb = InlineKeyboardMarkup(row_width=1).add(InlineKeyboardButton("➕ Add Service", callback_data="svc_add"), InlineKeyboardButton("❌ Remove Service", callback_data="svc_del"))
    bot.send_message(m.chat.id, "⚙️ *SERVICE MANAGER*", parse_mode="Markdown", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data == "svc_add")
def svc_add_1(c):
    bot.answer_callback_query(c.id)
    user_states[ADMIN_ID] = {"state": "svc_cat"}
    bot.send_message(ADMIN_ID, "📁 *Category Name:* (e.g., Instagram)", parse_mode="Markdown", reply_markup=cancel_keyboard())

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and user_states.get(ADMIN_ID, {}).get("state") == "svc_cat")
def svc_add_2(m):
    if m.text == "❌ Cancel Action": return handle_cancel(m)
    user_states[ADMIN_ID].update({"state": "svc_id", "cat": m.text.strip()})
    bot.send_message(ADMIN_ID, f"🔢 *Provider Service ID:*", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and user_states.get(ADMIN_ID, {}).get("state") == "svc_id")
def svc_add_3(m):
    if m.text == "❌ Cancel Action": return handle_cancel(m)
    sid, cat, margin = m.text.strip(), user_states[ADMIN_ID]["cat"], get_global_margin()
    api_res = call_smm_api('services')
    try:
        s_data = next(i for i in api_res if str(i['service']) == sid)
        execute_db("INSERT OR REPLACE INTO managed_services (service_id, category, name, rate, margin) VALUES (?,?,?,?,?)", (int(sid), cat, s_data['name'], float(s_data['rate']), margin))
        bot.send_message(ADMIN_ID, f"✅ *ADDED:* `{s_data['name']}`", parse_mode="Markdown", reply_markup=generate_main_keyboard(ADMIN_ID))
    except: bot.send_message(ADMIN_ID, f"❌ ID {sid} not found.", reply_markup=generate_main_keyboard(ADMIN_ID))
    user_states.pop(ADMIN_ID, None)

@bot.callback_query_handler(func=lambda c: c.data == "svc_del")
def svc_del_list(c):
    bot.answer_callback_query(c.id)
    services = execute_db("SELECT service_id, name FROM managed_services", fetch_all=True)
    kb = InlineKeyboardMarkup(row_width=1)
    for s in services: kb.add(InlineKeyboardButton(f"🗑️ {s[1][:25]}", callback_data=f"ds_{s[0]}"))
    bot.send_message(c.message.chat.id, "❌ *Click to Remove:*", parse_mode="Markdown", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("ds_"))
def svc_del_confirm(c):
    sid = c.data.split("_")[1]
    execute_db("DELETE FROM managed_services WHERE service_id=?", (sid,))
    bot.answer_callback_query(c.id, f"Deleted {sid}", show_alert=True)
    try: bot.delete_message(c.message.chat.id, c.message.message_id)
    except: pass

@bot.message_handler(func=lambda m: m.text == "📈 Adjust Margins" and m.from_user.id == ADMIN_ID)
def margin_adj_1(m):
    user_states[ADMIN_ID] = {"state": "margin_val"}
    bot.send_message(ADMIN_ID, f"📈 Enter new margin % (e.g. `50` for 50% profit):", parse_mode="Markdown", reply_markup=cancel_keyboard())

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and user_states.get(ADMIN_ID, {}).get("state") == "margin_val")
def margin_adj_2(m):
    if m.text == "❌ Cancel Action": return handle_cancel(m)
    try:
        perc = float(m.text)
        multiplier = 1 + (perc / 100.0)
        execute_db("UPDATE settings SET value=? WHERE key='global_margin'", (str(multiplier),))
        execute_db("UPDATE managed_services SET margin=?", (multiplier,))
        bot.send_message(ADMIN_ID, f"✅ Global Margin updated to `{perc}%`.", parse_mode="Markdown", reply_markup=generate_main_keyboard(ADMIN_ID))
    except: bot.send_message(ADMIN_ID, "Error.", reply_markup=generate_main_keyboard(ADMIN_ID))
    user_states.pop(ADMIN_ID, None)

# =======================================================================================
# 11. ADMIN GOD MODE & BROADCAST
# =======================================================================================
@bot.message_handler(func=lambda m: m.text == "💰 God Mode Funds" and m.from_user.id == ADMIN_ID)
def god_funds(m):
    user_states[ADMIN_ID] = {"state": "god_id"}
    bot.send_message(ADMIN_ID, "👑 Target *User ID*:", parse_mode="Markdown", reply_markup=cancel_keyboard())

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and user_states.get(ADMIN_ID, {}).get("state") == "god_id")
def god_id(m):
    if m.text == "❌ Cancel Action": return handle_cancel(m)
    user_states[ADMIN_ID].update({"state": "god_amt", "uid": int(m.text)})
    bot.send_message(ADMIN_ID, "💸 *Amount* (+ to add, - to deduct):", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and user_states.get(ADMIN_ID, {}).get("state") == "god_amt")
def god_amt(m):
    if m.text == "❌ Cancel Action": return handle_cancel(m)
    try:
        amt = float(m.text)
        uid = user_states[ADMIN_ID]["uid"]
        execute_db("UPDATE users SET balance = balance + ? WHERE user_id=?", (amt, uid))
        bot.send_message(ADMIN_ID, f"✅ Applied `{amt}` to `{uid}`", parse_mode="Markdown", reply_markup=generate_main_keyboard(ADMIN_ID))
    except: bot.send_message(ADMIN_ID, "Error.", reply_markup=generate_main_keyboard(ADMIN_ID))
    user_states.pop(ADMIN_ID, None)

@bot.message_handler(func=lambda m: m.text == "📩 Direct Msg" and m.from_user.id == ADMIN_ID)
def dm_1(m):
    user_states[ADMIN_ID] = {"state": "dm_id"}
    bot.send_message(ADMIN_ID, "📩 Target *User ID*:", parse_mode="Markdown", reply_markup=cancel_keyboard())

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and user_states.get(ADMIN_ID, {}).get("state") == "dm_id")
def dm_2(m):
    if m.text == "❌ Cancel Action": return handle_cancel(m)
    user_states[ADMIN_ID].update({"state": "dm_msg", "uid": int(m.text)})
    bot.send_message(ADMIN_ID, "✍️ *Message:*", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and user_states.get(ADMIN_ID, {}).get("state") == "dm_msg")
def dm_3(m):
    if m.text == "❌ Cancel Action": return handle_cancel(m)
    try: bot.send_message(user_states[ADMIN_ID]["uid"], f"📩 *Admin:*\n\n{m.text}", parse_mode="Markdown")
    except: pass
    bot.send_message(ADMIN_ID, "✅ Sent.", reply_markup=generate_main_keyboard(ADMIN_ID))
    user_states.pop(ADMIN_ID, None)

@bot.message_handler(func=lambda m: m.text == "📢 Broadcast" and m.from_user.id == ADMIN_ID)
def broad_1(m):
    user_states[ADMIN_ID] = {"state": "broad_msg"}
    bot.send_message(ADMIN_ID, "📢 *Type message:*", parse_mode="Markdown", reply_markup=cancel_keyboard())

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and user_states.get(ADMIN_ID, {}).get("state") == "broad_msg")
def broad_2(m):
    if m.text == "❌ Cancel Action": return handle_cancel(m)
    users = execute_db("SELECT user_id FROM users", fetch_all=True)
    bot.send_message(ADMIN_ID, "⏳ Sending...", reply_markup=generate_main_keyboard(ADMIN_ID))
    for u in users:
        try: bot.send_message(u[0], f"📢 *ANNOUNCEMENT*\n\n{m.text}", parse_mode="Markdown")
        except: pass
    bot.send_message(ADMIN_ID, f"✅ Done.")
    user_states.pop(ADMIN_ID, None)

# =======================================================================================
# 12. INITIALIZATION
# =======================================================================================
def run_telegram_bot():
    init_database()
    logger.info("Bot Engine Active.")
    while True:
        try: bot.infinity_polling(timeout=20, long_polling_timeout=15)
        except Exception as e:
            logger.error(f"Crash: {e}. Restarting...")
            time.sleep(5)

if __name__ == '__main__':
    threading.Thread(target=run_telegram_bot, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
