"""
=========================================================================================
🔥 CHEAP SMM PANEL BOT - ENTERPRISE V3 (RENDER SAFE EDITION) 🔥
=========================================================================================
Description: A fully-automated Telegram Bot for SMM Panel services.
Features:
- Flask Web Server Integrated (Prevents Render from crashing)
- Multi-threading Enabled
- Direct API Purchasing & Escrow System
- Failsafe Token Loading
=========================================================================================
"""

import telebot
import requests
import sqlite3
import logging
import time
import urllib.parse
import string
import random
import os
import threading
from flask import Flask
from datetime import datetime, timedelta
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# =======================================================================================
# 1. ADVANCED LOGGING & RENDER WEB SERVER
# =======================================================================================
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Flask App to keep Render happy
app = Flask(__name__)
@app.route('/')
def home():
    return "🔥 SMM Panel Bot is ONLINE and running on Render! 🔥"

# =======================================================================================
# 2. CORE CONFIGURATION & CREDENTIALS (FAILSAFE)
# =======================================================================================
# It looks for Render variables first. If not found, it uses your hardcoded ones so it NEVER crashes.
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8228287584:AAFa93-H1WLx-sY_JNO3XJmeqzOogPImhqM')
API_KEY = os.environ.get('API_KEY', 'w4NIpEsjLOWxMM87R0ZxiPeMgu2ri8ugJeYPmMa206aPmOhDu9NJSl13mvQvPUEZ')

bot = telebot.TeleBot(BOT_TOKEN)
API_URL = "https://indiansmmprovider.in/api/v2"

# ADMIN & SUPPORT DETAILS
ADMIN_ID = 6034840006  
SUPPORT_HANDLE = "@Cristae99" 
SUPPORT_LINK = f"https://t.me/{SUPPORT_HANDLE.replace('@', '')}"

# PAYMENT & ECONOMY SETTINGS
UPI_ID = "rahikhann@fam"
MIN_DEPOSIT = 10.0  
MARKUP_PERCENTAGE = 1.45 
REFERRAL_BONUS = 5.0 

TARGET_IDS = [15979, 16411, 16453, 16441, 16439, 15397, 16451, 15843]
user_states = {}

# =======================================================================================
# 3. ENTERPRISE RELATIONAL DATABASE ENGINE (Thread-Safe)
# =======================================================================================
def init_db():
    try:
        conn = sqlite3.connect('panel_enterprise.db', check_same_thread=False)
        c = conn.cursor()
        
        c.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT, balance REAL DEFAULT 0.0, total_spent REAL DEFAULT 0.0, last_daily TIMESTAMP DEFAULT '2000-01-01 00:00:00', referred_by INTEGER DEFAULT 0, join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        c.execute('''CREATE TABLE IF NOT EXISTS transactions (tx_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount REAL, status TEXT, date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        c.execute('''CREATE TABLE IF NOT EXISTS orders (db_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, api_order_id TEXT, service_id INTEGER, link TEXT, quantity INTEGER, cost REAL, status TEXT DEFAULT 'Pending', date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        c.execute('''CREATE TABLE IF NOT EXISTS promo_codes (code TEXT PRIMARY KEY, amount REAL, max_uses INTEGER DEFAULT 1, current_uses INTEGER DEFAULT 0, created_by INTEGER)''')
        c.execute('''CREATE TABLE IF NOT EXISTS promo_redeems (user_id INTEGER, code TEXT, date TIMESTAMP DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY (user_id, code))''')
        c.execute('''CREATE TABLE IF NOT EXISTS tickets (ticket_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, subject TEXT, status TEXT DEFAULT 'OPEN', date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

        conn.commit()
        conn.close()
        logger.info("Enterprise Database Engine Initialized.")
    except Exception as e: logger.error(f"Database Init Error: {e}")

def get_user(user_id, username=None, first_name=None, ref_by=0):
    try:
        conn = sqlite3.connect('panel_enterprise.db', check_same_thread=False)
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
        user = c.fetchone()
        
        if not user and username is not None:
            c.execute('''INSERT INTO users (user_id, username, first_name, balance, total_spent, referred_by) VALUES (?, ?, ?, 0.0, 0.0, ?)''', (user_id, username, first_name, ref_by))
            conn.commit()
            if ref_by != 0:
                try: bot.send_message(ref_by, f"🎉 *New Referral!* `{first_name}` joined! You get a bonus when they deposit.")
                except: pass
            c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
            user = c.fetchone()
        conn.close()
        return user
    except Exception as e:
        logger.error(f"User Fetch Error: {e}")
        return None

def update_balance(user_id, amount):
    try:
        conn = sqlite3.connect('panel_enterprise.db', check_same_thread=False)
        c = conn.cursor()
        c.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e: return False

def increase_total_spent(user_id, amount):
    try:
        conn = sqlite3.connect('panel_enterprise.db', check_same_thread=False)
        c = conn.cursor()
        c.execute("UPDATE users SET total_spent = total_spent + ? WHERE user_id = ?", (amount, user_id))
        conn.commit()
        conn.close()
    except Exception as e: pass

def get_vip_tier(total_spent):
    if total_spent >= 10000: return "🌌 Cosmic Whale"
    elif total_spent >= 5000: return "💎 Diamond Boss"
    elif total_spent >= 1000: return "🥇 Gold Member"
    elif total_spent >= 500: return "🥈 Silver Hustler"
    else: return "🥉 Bronze Starter"

def generate_random_code(length=8):
    letters_and_digits = string.ascii_uppercase + string.digits
    return ''.join(random.choice(letters_and_digits) for i in range(length))

# =======================================================================================
# 4. SMM PANEL API CORE 
# =======================================================================================
def api_get_services():
    try:
        payload = {'key': API_KEY, 'action': 'services'}
        response = requests.post(API_URL, data=payload, timeout=15)
        if response.status_code == 200:
            services = response.json()
            data = {}
            for item in services:
                try: s_id = int(item.get('service', 0))
                except ValueError: continue
                if s_id in TARGET_IDS:
                    try: base_rate = float(item.get('rate', '0.00'))
                    except ValueError: base_rate = 0.00
                    data[s_id] = {
                        "name": item.get('name', 'Service'),
                        "rate": base_rate * MARKUP_PERCENTAGE, 
                        "min": int(item.get('min', '100')),
                        "max": int(item.get('max', '10000')),
                        "category": item.get('category', 'SMM')
                    }
            return data
        return None
    except Exception as e: return None

def api_place_order(service_id, link, quantity):
    try:
        payload = {'key': API_KEY, 'action': 'add', 'service': service_id, 'link': link, 'quantity': quantity}
        response = requests.post(API_URL, data=payload, timeout=20)
        result = response.json()
        if 'order' in result: return {"status": "success", "order_id": result['order']}
        else: return {"status": "error", "message": result.get('error', 'Unknown API Error')}
    except Exception as e: return {"status": "error", "message": "Failed to connect to panel."}

def api_check_status(order_id):
    try:
        payload = {'key': API_KEY, 'action': 'status', 'order': order_id}
        response = requests.post(API_URL, data=payload, timeout=15)
        result = response.json()
        if 'status' in result: return result['status']
        return "Unknown"
    except Exception as e: return "Error fetching status"

# =======================================================================================
# 5. UI KEYBOARDS & BOTS COMMANDS
# =======================================================================================
def main_reply_keyboard():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🛒 Browse Services 🚀")
    markup.add("💰 My Drip (Profile)", "💳 Add Funds (Wallet)")
    markup.add("📦 Order History", "🎁 Daily Bonus")
    markup.add("🎫 Redeem Promo", "📞 Support / Help")
    return markup

def cancel_keyboard():
    return ReplyKeyboardMarkup(resize_keyboard=True).add("❌ Cancel Action")

@bot.message_handler(commands=['start'])
def welcome(message):
    user_id = message.from_user.id
    ref_by = 0
    if len(message.text.split()) > 1:
        param = message.text.split()[1]
        if param.startswith('ref'):
            try:
                ref_by = int(param.replace('ref', ''))
                if ref_by == user_id: ref_by = 0
            except ValueError: pass
            
    user_states.pop(user_id, None) 
    user = get_user(user_id, message.from_user.username, message.from_user.first_name, ref_by)
    
    welcome_msg = (f"Yooo, welcome to the plug 🔌✨, *{message.from_user.first_name}*!\n\n"
                   f"🔥 *CHEAP SMM PANEL V3* 🔥\nDirect API Access. Instant Orders. No Cap.\n\n"
                   f"💸 *Your Stash:* `₹{user[3]:.2f}`\n👑 *Rank:* {get_vip_tier(user[4])}\n"
                   f"🆔 *Your ID:* `{user[0]}`\n\n👇 *Hit the menu below to level up!*")
    bot.send_message(message.chat.id, welcome_msg, parse_mode="Markdown", reply_markup=main_reply_keyboard())

@bot.message_handler(func=lambda message: message.text == "❌ Cancel Action")
def cancel_state(message):
    user_states.pop(message.from_user.id, None)
    bot.send_message(message.chat.id, "🚫 *Action Cancelled.* Returning to lobby.", parse_mode="Markdown", reply_markup=main_reply_keyboard())

@bot.message_handler(func=lambda message: message.text == "🛒 Browse Services 🚀")
def show_services(message):
    bot.send_chat_action(message.chat.id, 'typing')
    service_data = api_get_services()
    if not service_data: return bot.send_message(message.chat.id, "API is offline right now. Try again later.")

    markup = InlineKeyboardMarkup(row_width=1)
    for s_id in TARGET_IDS:
        s_info = service_data.get(s_id)
        if s_info: markup.add(InlineKeyboardButton(f"🔥 {s_info['name']} - ₹{s_info['rate']:.2f}", callback_data=f"info_{s_id}"))
    bot.send_message(message.chat.id, "🛒 *The Main Roster*\nTap a service to check stats & buy:", parse_mode="Markdown", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == "💰 My Drip (Profile)")
def show_profile(message):
    user = get_user(message.from_user.id)
    bot_info = bot.get_me()
    text = (f"💧 *PROFILE CHECK* 💧\n━━━━━━━━━━━━━━━━━━━\n🆔 *ID:* `{user[0]}`\n👤 *Alias:* {user[2]}\n"
            f"👑 *Status:* {get_vip_tier(user[4])}\n💰 *Stash:* `₹{user[3]:.2f}`\n📈 *Spent:* `₹{user[4]:.2f}`\n"
            f"━━━━━━━━━━━━━━━━━━━\n🤝 *Affiliate Program:*\nInvite friends for a `₹{REFERRAL_BONUS}` bonus!\n"
            f"🔗 *Your Link:* `https://t.me/{bot_info.username}?start=ref{user[0]}`")
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == "🎁 Daily Bonus")
def claim_daily(message):
    user = get_user(message.from_user.id)
    last_claim = datetime.strptime(user[5], '%Y-%m-%d %H:%M:%S')
    now = datetime.now()
    if now - last_claim > timedelta(days=1):
        update_balance(message.from_user.id, 1.0)
        conn = sqlite3.connect('panel_enterprise.db', check_same_thread=False)
        conn.execute("UPDATE users SET last_daily = CURRENT_TIMESTAMP WHERE user_id = ?", (message.from_user.id,))
        conn.commit()
        conn.close()
        bot.send_message(message.chat.id, "🎉 *W Drip!* Claimed `₹1.00`. Come back tomorrow.", parse_mode="Markdown")
    else: bot.send_message(message.chat.id, "🛑 Already claimed today. Try again tomorrow.", parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == "📞 Support / Help")
def support_menu(message):
    bot.send_message(message.chat.id, f"🛠️ *HELP DESK*\nNeed admin help? Message here: 👉 {SUPPORT_LINK}", parse_mode="Markdown")

# --- ORDERING SYSTEM ---
@bot.callback_query_handler(func=lambda call: call.data.startswith("info_"))
def show_service_details(call):
    s_id = int(call.data.split("_")[1])
    data = api_get_services()
    if not data or s_id not in data: return bot.answer_callback_query(call.id, "Service offline.", show_alert=True)
    
    s = data[s_id]
    detail_text = (f"📊 *SERVICE STATS* 📊\n━━━━━━━━━━━━━━━━━━━\n🏷️ *Name:* {s['name']}\n🆔 *ID:* `{s_id}`\n"
                   f"💰 *Price (1k):* `₹{s['rate']:.2f}`\n📉 *Limits:* Min {s['min']} | Max {s['max']}\n━━━━━━━━━━━━━━━━━━━")
    
    markup = InlineKeyboardMarkup().add(InlineKeyboardButton("🛒 Purchase Directly", callback_data=f"buy_{s_id}"))
    bot.edit_message_text(detail_text, call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("buy_"))
def initiate_purchase(call):
    s_id = int(call.data.split("_")[1])
    user_states[call.from_user.id] = {"state": "ordering_link", "service_id": s_id}
    bot.delete_message(call.message.chat.id, call.message.message_id)
    bot.send_message(call.message.chat.id, "🔗 *Send the Target Link* (Must be PUBLIC):", parse_mode="Markdown", reply_markup=cancel_keyboard())

@bot.message_handler(func=lambda m: m.from_user.id in user_states and user_states[m.from_user.id].get("state") == "ordering_link")
def get_order_link(message):
    if message.text == "❌ Cancel Action": return cancel_state(message)
    user_id = message.from_user.id
    s_id = user_states[user_id]["service_id"]
    data = api_get_services()
    if not data or s_id not in data: return bot.send_message(message.chat.id, "API Error.", reply_markup=main_reply_keyboard())
    
    user_states[user_id].update({"state": "ordering_qty", "link": message.text, "rate": data[s_id]['rate'], "min": data[s_id]['min'], "max": data[s_id]['max']})
    bot.send_message(message.chat.id, f"🔢 *Enter Quantity* (Min {data[s_id]['min']} - Max {data[s_id]['max']}):", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.from_user.id in user_states and user_states[m.from_user.id].get("state") == "ordering_qty")
def process_order(message):
    if message.text == "❌ Cancel Action": return cancel_state(message)
    user_id = message.from_user.id
    state = user_states[user_id]
    
    try: qty = int(message.text)
    except ValueError: return bot.send_message(message.chat.id, "🤨 Numbers only.")
        
    if qty < state["min"] or qty > state["max"]: return bot.send_message(message.chat.id, f"🚫 Between {state['min']} and {state['max']}.")
    cost = (qty / 1000) * state["rate"]
    
    user = get_user(user_id)
    if user[3] < cost: return bot.send_message(message.chat.id, f"❌ Insufficient Funds! Costs `₹{cost:.2f}`.", parse_mode="Markdown", reply_markup=main_reply_keyboard())
        
    bot.send_message(message.chat.id, "⏳ Processing order...")
    update_balance(user_id, -cost)
    api_res = api_place_order(state["service_id"], state["link"], qty)
    
    if api_res["status"] == "success":
        try:
            conn = sqlite3.connect('panel_enterprise.db', check_same_thread=False)
            conn.execute("INSERT INTO orders (user_id, api_order_id, service_id, link, quantity, cost) VALUES (?, ?, ?, ?, ?, ?)", (user_id, api_res["order_id"], state["service_id"], state["link"], qty, cost))
            conn.commit()
            conn.close()
        except: pass
        increase_total_spent(user_id, cost)
        bot.send_message(message.chat.id, f"✅ *ORDER PLACED!*\n🧾 ID: `{api_res['order_id']}`\n💰 Cost: `₹{cost:.2f}`", parse_mode="Markdown", reply_markup=main_reply_keyboard())
    else:
        update_balance(user_id, cost)
        bot.send_message(message.chat.id, f"❌ *FAILED:*\n{api_res['message']}\nRefunded: `₹{cost:.2f}`", parse_mode="Markdown", reply_markup=main_reply_keyboard())
    del user_states[user_id]

# --- WALLET & ESCROW ---
@bot.message_handler(func=lambda message: message.text == "💳 Add Funds (Wallet)")
def trigger_add_funds(message):
    user_states[message.from_user.id] = {"state": "awaiting_amount"}
    bot.send_message(message.chat.id, f"💸 *How much ₹₹₹ to add?*\nMin: ₹{MIN_DEPOSIT}", parse_mode="Markdown", reply_markup=cancel_keyboard())

@bot.message_handler(func=lambda m: m.from_user.id in user_states and user_states[m.from_user.id].get("state") == "awaiting_amount")
def process_amount(message):
    if message.text == "❌ Cancel Action": return cancel_state(message)
    try:
        amount = float(message.text)
        if amount < MIN_DEPOSIT: return bot.send_message(message.chat.id, f"🚫 Minimum is `₹{MIN_DEPOSIT}`.")
        user_states[message.from_user.id] = {"state": "awaiting_ss", "amount": amount}
        qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=400x400&data={urllib.parse.quote(f'upi://pay?pa={UPI_ID}&pn=Admin&am={amount}&cu=INR')}"
        bot.send_photo(message.chat.id, photo=qr_url, caption=f"💳 *PAY: ₹{amount}*\nUPI: `{UPI_ID}`\n📸 *Send Screenshot Here Now.*", parse_mode="Markdown")
    except ValueError: bot.send_message(message.chat.id, "🤨 Valid number please.")

@bot.message_handler(content_types=['photo'])
def handle_screenshot(message):
    user_id = message.from_user.id
    if user_id in user_states and user_states[user_id].get("state") == "awaiting_ss":
        amount = user_states[user_id]["amount"]
        try:
            conn = sqlite3.connect('panel_enterprise.db', check_same_thread=False)
            c = conn.cursor()
            c.execute("INSERT INTO transactions (user_id, amount, status) VALUES (?, ?, 'PENDING')", (user_id, amount))
            tx_id = c.lastrowid
            conn.commit()
            conn.close()
        except: return

        bot.send_message(message.chat.id, "⏳ Sent to Admin. Wait for approval.", reply_markup=main_reply_keyboard())
        del user_states[user_id]
        
        markup = InlineKeyboardMarkup().add(InlineKeyboardButton("✅ Approve", callback_data=f"approve_{tx_id}_{user_id}_{amount}"), InlineKeyboardButton("❌ Reject", callback_data=f"reject_{tx_id}_{user_id}_{amount}"))
        bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=f"🚨 *DEPOSIT*\n🆔 `{user_id}`\n💰 `₹{amount}`\n🧾 `TXN-{tx_id}`", parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("approve_") or call.data.startswith("reject_"))
def admin_escrow_decision(call):
    if call.from_user.id != ADMIN_ID: return
    data = call.data.split("_")
    action, tx_id, user_id, amount = data[0], int(data[1]), int(data[2]), float(data[3])
    
    conn = sqlite3.connect('panel_enterprise.db', check_same_thread=False)
    if action == "approve":
        conn.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
        conn.execute("UPDATE transactions SET status = 'APPROVED' WHERE tx_id = ?", (tx_id,))
        bot.edit_message_caption(caption=f"✅ *APPROVED: ₹{amount} to {user_id}*", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown")
        try: bot.send_message(user_id, f"🎉 Admin approved `₹{amount}`. 🚀", parse_mode="Markdown")
        except: pass
    else:
        conn.execute("UPDATE transactions SET status = 'REJECTED' WHERE tx_id = ?", (tx_id,))
        bot.edit_message_caption(caption=f"❌ *REJECTED: TXN-{tx_id}*", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown")
    conn.commit()
    conn.close()

# --- ADMIN COMMANDS ---
@bot.message_handler(commands=['addfunds'])
def manual_add(message):
    if message.from_user.id != ADMIN_ID: return
    try:
        args = message.text.split()
        target, amount = int(args[1]), float(args[2])
        update_balance(target, amount)
        bot.reply_to(message, f"✅ Added ₹{amount} to {target}.")
    except: bot.reply_to(message, "Usage: `/addfunds [user_id] [amount]`")

# =======================================================================================
# 6. RENDER EXECUTION ENGINE (Flask + Polling)
# =======================================================================================
def run_bot():
    print("--- [ INITIALIZING ENTERPRISE ENGINE ] ---")
    init_db()
    print("--- [ DATABASE SECURED & ONLINE ] ---")
    print("--- [ BOT V3 RUNNING - DIRECT API ENABLED ] ---")
    while True:
        try: bot.infinity_polling(timeout=20, long_polling_timeout=10)
        except Exception as e:
            logger.error(f"System Crash: {e}")
            time.sleep(5)

if __name__ == '__main__':
    # 1. Start the bot logic in a background thread
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.start()
    
    # 2. Start the Flask server on the main thread (CRITICAL FOR RENDER)
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
