"""
=========================================================================================
🔥 CHEAP SMM PANEL BOT - FULL ENTERPRISE EDITION (RENDER SAFE) 🔥
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
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove

# =======================================================================================
# 1. RENDER WEB SERVER & LOGGING
# =======================================================================================
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
@app.route('/')
def home(): 
    return "🔥 SMM Panel Bot is 24/7 ONLINE! 🔥"

# =======================================================================================
# 2. CONFIGURATION & CREDENTIALS
# =======================================================================================
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8228287584:AAFa93-H1WLx-sY_JNO3XJmeqzOogPImhqM')
API_KEY = os.environ.get('API_KEY', 'w4NIpEsjLOWxMM87R0ZxiPeMgu2ri8ugJeYPmMa206aPmOhDu9NJSl13mvQvPUEZ')
bot = telebot.TeleBot(BOT_TOKEN)

API_URL = "https://indiansmmprovider.in/api/v2"
ADMIN_ID = 6034840006  
SUPPORT_HANDLE = "@Cristae99" 
SUPPORT_LINK = f"https://t.me/{SUPPORT_HANDLE.replace('@', '')}"
UPI_ID = "rahikhann@fam"

MIN_DEPOSIT = 10.0  
MARKUP_PERCENTAGE = 1.45 
REFERRAL_BONUS = 5.0 
TARGET_IDS = [15979, 16411, 16453, 16441, 16439, 15397, 16451, 15843]

user_states = {}

# =======================================================================================
# 3. ENTERPRISE DATABASE ENGINE (THREAD-SAFE)
# =======================================================================================
def get_db():
    return sqlite3.connect('panel_enterprise.db', check_same_thread=False, timeout=20)

def init_db():
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT, balance REAL DEFAULT 0.0, total_spent REAL DEFAULT 0.0, last_daily TIMESTAMP DEFAULT '2000-01-01 00:00:00', referred_by INTEGER DEFAULT 0, join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        c.execute('''CREATE TABLE IF NOT EXISTS transactions (tx_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount REAL, status TEXT, date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        c.execute('''CREATE TABLE IF NOT EXISTS orders (db_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, api_order_id TEXT, service_id INTEGER, link TEXT, quantity INTEGER, cost REAL, status TEXT DEFAULT 'Pending', date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        c.execute('''CREATE TABLE IF NOT EXISTS promo_codes (code TEXT PRIMARY KEY, amount REAL, max_uses INTEGER DEFAULT 1, current_uses INTEGER DEFAULT 0, created_by INTEGER)''')
        c.execute('''CREATE TABLE IF NOT EXISTS promo_redeems (user_id INTEGER, code TEXT, date TIMESTAMP DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY (user_id, code))''')
        c.execute('''CREATE TABLE IF NOT EXISTS tickets (ticket_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, subject TEXT, status TEXT DEFAULT 'OPEN', date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"DB Init Error: {e}")

def get_user(user_id, username=None, first_name=None, ref_by=0):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    user = c.fetchone()
    
    if not user and username is not None:
        c.execute("INSERT INTO users (user_id, username, first_name, balance, total_spent, referred_by) VALUES (?, ?, ?, 0.0, 0.0, ?)", (user_id, username, first_name, ref_by))
        conn.commit()
        if ref_by != 0:
            try: bot.send_message(ref_by, f"🎉 *New Referral!* `{first_name}` joined using your link!")
            except: pass
        c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
        user = c.fetchone()
    conn.close()
    return user

def update_balance(user_id, amount):
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()

def get_vip_tier(total_spent):
    if total_spent >= 10000: return "🌌 Cosmic Whale"
    elif total_spent >= 5000: return "💎 Diamond Boss"
    elif total_spent >= 1000: return "🥇 Gold Member"
    elif total_spent >= 500: return "🥈 Silver Hustler"
    else: return "🥉 Bronze Starter"

def generate_random_code(length=8):
    return ''.join(random.choice(string.ascii_uppercase + string.digits) for i in range(length))

# =======================================================================================
# 4. API ENGINE
# =======================================================================================
def api_get_services():
    try:
        response = requests.post(API_URL, data={'key': API_KEY, 'action': 'services'}, timeout=15)
        if response.status_code == 200:
            data = {}
            for item in response.json():
                s_id = int(item.get('service', 0))
                if s_id in TARGET_IDS:
                    data[s_id] = {
                        "name": item.get('name', 'Service'),
                        "rate": float(item.get('rate', '0.00')) * MARKUP_PERCENTAGE, 
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
        response = requests.post(API_URL, data=payload, timeout=20).json()
        if 'order' in response: return {"status": "success", "order_id": response['order']}
        else: return {"status": "error", "message": response.get('error', 'Unknown API Error')}
    except Exception as e: return {"status": "error", "message": "Failed to connect to the panel."}

def api_check_status(order_id):
    try:
        response = requests.post(API_URL, data={'key': API_KEY, 'action': 'status', 'order': order_id}, timeout=15).json()
        if 'status' in response: return response['status']
        return "Unknown"
    except Exception as e: return "Error fetching status"

# =======================================================================================
# 5. UI KEYBOARDS
# =======================================================================================
def main_reply_keyboard():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(KeyboardButton("🛒 Browse Services 🚀"))
    markup.add(KeyboardButton("💰 My Drip (Profile)"), KeyboardButton("💳 Add Funds (Wallet)"))
    markup.add(KeyboardButton("📦 Order History"), KeyboardButton("🎁 Daily Bonus"))
    markup.add(KeyboardButton("🎫 Redeem Promo"), KeyboardButton("📞 Support / Help"))
    return markup

def cancel_keyboard():
    return ReplyKeyboardMarkup(resize_keyboard=True).add(KeyboardButton("❌ Cancel Action"))

# =======================================================================================
# 6. CORE BOT COMMANDS
# =======================================================================================
@bot.message_handler(commands=['start'])
def welcome(message):
    user_id = message.from_user.id
    ref_by = 0
    if len(message.text.split()) > 1 and message.text.split()[1].startswith('ref'):
        try: ref_by = int(message.text.split()[1].replace('ref', ''))
        except: pass
        if ref_by == user_id: ref_by = 0

    user_states.pop(user_id, None) 
    user = get_user(user_id, message.from_user.username, message.from_user.first_name, ref_by)
    
    welcome_msg = (
        f"Yooo, welcome to the plug 🔌✨, *{message.from_user.first_name}*!\n\n"
        f"🔥 *CHEAP SMM PANEL V4* 🔥\n"
        f"Direct API Access. Instant Orders. No Cap. 🧢🚫\n\n"
        f"💸 *Your Stash:* `₹{user[3]:.2f}`\n"
        f"👑 *Rank:* {get_vip_tier(user[4])}\n"
        f"🆔 *Your ID:* `{user[0]}`\n\n"
        f"👇 *Hit the menu below to level up your socials!*"
    )
    bot.send_message(message.chat.id, welcome_msg, parse_mode="Markdown", reply_markup=main_reply_keyboard())

@bot.message_handler(func=lambda message: message.text == "❌ Cancel Action")
def cancel_state(message):
    user_states.pop(message.from_user.id, None)
    bot.send_message(message.chat.id, "🚫 *Action Cancelled.* We go back to the lobby.", parse_mode="Markdown", reply_markup=main_reply_keyboard())

# =======================================================================================
# 7. MAIN MENU HANDLERS (ALL RESTORED)
# =======================================================================================
@bot.message_handler(func=lambda message: message.text == "💰 My Drip (Profile)")
def show_profile(message):
    user = get_user(message.from_user.id)
    ref_link = f"https://t.me/{bot.get_me().username}?start=ref{user[0]}"
    text = (
        f"💧 *THE VAULT - PROFILE CHECK* 💧\n━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 *User ID:* `{user[0]}`\n👤 *Alias:* {user[2]}\n👑 *Status:* {get_vip_tier(user[4])}\n\n"
        f"💰 *Current Stash:* `₹{user[3]:.2f}`\n📈 *Total Flexed (Spent):* `₹{user[4]:.2f}`\n━━━━━━━━━━━━━━━━━━━\n"
        f"🤝 *Affiliate Program:*\nInvite friends for a `₹{REFERRAL_BONUS}` bonus on their first deposit!\n🔗 *Your Link:* `{ref_link}`"
    )
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == "🎁 Daily Bonus")
def claim_daily(message):
    user = get_user(message.from_user.id)
    last_claim = datetime.strptime(user[5], '%Y-%m-%d %H:%M:%S')
    if datetime.now() - last_claim > timedelta(days=1):
        conn = get_db()
        conn.execute("UPDATE users SET balance = balance + 1.0, last_daily = CURRENT_TIMESTAMP WHERE user_id = ?", (user[0],))
        conn.commit()
        conn.close()
        bot.send_message(message.chat.id, "🎉 *W Drip!* You claimed your daily `₹1.00`.", parse_mode="Markdown")
    else:
        bot.send_message(message.chat.id, "🛑 *Chill bro.* You already claimed today.", parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == "📞 Support / Help")
def support_menu(message):
    text = f"🛠️ *HELP DESK & SUPPORT* 🛠️\n\nQ: How long do orders take?\nA: Most start within 30 mins.\n\n📞 *Contact Admin:*\n👉 {SUPPORT_LINK}"
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

# =======================================================================================
# 8. ORDERING SYSTEM (API DIRECT)
# =======================================================================================
@bot.message_handler(func=lambda message: message.text == "🛒 Browse Services 🚀")
def show_services(message):
    bot.send_chat_action(message.chat.id, 'typing')
    service_data = api_get_services()
    if not service_data:
        return bot.send_message(message.chat.id, "Big yikes 😬. API is acting sus. Try again in a min.")

    markup = InlineKeyboardMarkup(row_width=1)
    for s_id, s_info in service_data.items():
        markup.add(InlineKeyboardButton(f"🔥 {s_info['name']} - ₹{s_info['rate']:.2f}", callback_data=f"info_{s_id}"))
    bot.send_message(message.chat.id, "🛒 *The Main Roster*\nTap a service to check stats & buy:", parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("info_"))
def show_service_details(call):
    s_id = int(call.data.split("_")[1])
    data = api_get_services()
    if not data or s_id not in data: return bot.answer_callback_query(call.id, "Service offline.", show_alert=True)
        
    s = data[s_id]
    detail_text = (f"📊 *SERVICE STATS* 📊\n━━━━━━━━━━━━━━━━━━━\n🏷️ *Service:* {s['name']}\n🆔 *ID:* `{s_id}`\n"
                   f"💰 *Price (per 1k):* `₹{s['rate']:.2f}`\n📉 *Limits:* Min {s['min']} | Max {s['max']}\n━━━━━━━━━━━━━━━━━━━")
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🛒 Purchase Directly", callback_data=f"buy_{s_id}"))
    bot.edit_message_text(detail_text, call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("buy_"))
def initiate_purchase(call):
    s_id = int(call.data.split("_")[1])
    user_states[call.from_user.id] = {"state": "ordering_link", "service_id": s_id}
    bot.delete_message(call.message.chat.id, call.message.message_id)
    bot.send_message(call.message.chat.id, "🔗 *ORDER SETUP: STEP 1*\nPlease send the *Target Link* (Make sure it's public):", parse_mode="Markdown", reply_markup=cancel_keyboard())

@bot.message_handler(func=lambda message: message.from_user.id in user_states and user_states[message.from_user.id].get("state") == "ordering_link")
def get_order_link(message):
    if message.text == "❌ Cancel Action": return cancel_state(message)
    user_id = message.from_user.id
    s_id = user_states[user_id]["service_id"]
    data = api_get_services()
    
    if not data or s_id not in data:
        user_states.pop(user_id, None)
        return bot.send_message(message.chat.id, "Connection lost to provider.", reply_markup=main_reply_keyboard())
        
    limits = data[s_id]
    user_states[user_id].update({"state": "ordering_qty", "link": message.text, "rate": limits['rate'], "min": limits['min'], "max": limits['max']})
    
    bot.send_message(message.chat.id, f"🔢 *ORDER SETUP: STEP 2*\nLink saved.\n\nHow many do you want to add?\n📉 Min: {limits['min']} | 📈 Max: {limits['max']}", parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.from_user.id in user_states and user_states[message.from_user.id].get("state") == "ordering_qty")
def process_order(message):
    if message.text == "❌ Cancel Action": return cancel_state(message)
    user_id = message.from_user.id
    state_data = user_states[user_id]
    
    try: qty = int(message.text)
    except: return bot.send_message(message.chat.id, "🤨 *Invalid Input.* Numbers only.")
        
    if qty < state_data["min"] or qty > state_data["max"]:
        return bot.send_message(message.chat.id, f"🚫 Amount must be between {state_data['min']} and {state_data['max']}.")
        
    cost = (qty / 1000) * state_data["rate"]
    user = get_user(user_id)
    
    if user[3] < cost:
        user_states.pop(user_id, None)
        return bot.send_message(message.chat.id, f"❌ *Insufficient Funds!*\nCosts `₹{cost:.2f}` but you have `₹{user[3]:.2f}`.", parse_mode="Markdown", reply_markup=main_reply_keyboard())
        
    bot.send_chat_action(message.chat.id, 'typing')
    msg = bot.send_message(message.chat.id, "⏳ Processing your order with the server...", reply_markup=main_reply_keyboard())
    
    update_balance(user_id, -cost)
    api_res = api_place_order(state_data["service_id"], state_data["link"], qty)
    
    try: bot.delete_message(message.chat.id, msg.message_id)
    except: pass

    if api_res["status"] == "success":
        conn = get_db()
        conn.execute("INSERT INTO orders (user_id, api_order_id, service_id, link, quantity, cost) VALUES (?, ?, ?, ?, ?, ?)", (user_id, api_res["order_id"], state_data["service_id"], state_data["link"], qty, cost))
        conn.execute("UPDATE users SET total_spent = total_spent + ? WHERE user_id = ?", (cost, user_id))
        conn.commit()
        conn.close()
        
        bot.send_message(message.chat.id, f"✅ *ORDER SUCCESS!* ✅\n\n🧾 *ID:* `{api_res['order_id']}`\n💰 *Cost:* `₹{cost:.2f}`", parse_mode="Markdown")
    else:
        update_balance(user_id, cost)
        bot.send_message(message.chat.id, f"❌ *ORDER FAILED*\nServer rejected: `{api_res['message']}`\n`₹{cost:.2f}` refunded.", parse_mode="Markdown")

    user_states.pop(user_id, None)

# =======================================================================================
# 9. ORDER HISTORY & PROMOS
# =======================================================================================
@bot.message_handler(func=lambda message: message.text == "📦 Order History")
def view_order_history(message):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT api_order_id, service_id, quantity, cost, date FROM orders WHERE user_id=? ORDER BY date DESC LIMIT 5", (message.from_user.id,))
    orders = c.fetchall()
    conn.close()
    
    if not orders: return bot.send_message(message.chat.id, "You haven't placed any orders yet.")
        
    text = "📦 *YOUR RECENT ORDERS (LAST 5)* 📦\n\n"
    for o in orders:
        text += f"🔹 *ID:* `{o[0]}` | Date: {o[4].split()[0]}\n   Qty: {o[2]} | Cost: ₹{o[3]:.2f}\n\n"
        
    markup = InlineKeyboardMarkup().add(InlineKeyboardButton("🔍 Track an Order Status", callback_data="track_order"))
    bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "track_order")
def prompt_track_order(call):
    user_states[call.from_user.id] = {"state": "tracking"}
    bot.send_message(call.message.chat.id, "🔍 Send me the *Order ID*:", reply_markup=cancel_keyboard())

@bot.message_handler(func=lambda message: message.from_user.id in user_states and user_states[message.from_user.id].get("state") == "tracking")
def track_order_api(message):
    if message.text == "❌ Cancel Action": return cancel_state(message)
    bot.send_chat_action(message.chat.id, 'typing')
    status = api_check_status(message.text)
    bot.send_message(message.chat.id, f"📊 *ORDER STATUS*\n\n🧾 *ID:* `{message.text}`\n🚥 *Status:* `{status.upper()}`", parse_mode="Markdown", reply_markup=main_reply_keyboard())
    user_states.pop(message.from_user.id, None)

@bot.message_handler(func=lambda message: message.text == "🎫 Redeem Promo")
def prompt_promo(message):
    user_states[message.from_user.id] = {"state": "redeeming"}
    bot.send_message(message.chat.id, "🎫 Enter your *Promo Code*:", parse_mode="Markdown", reply_markup=cancel_keyboard())

@bot.message_handler(func=lambda message: message.from_user.id in user_states and user_states[message.from_user.id].get("state") == "redeeming")
def redeem_promo(message):
    if message.text == "❌ Cancel Action": return cancel_state(message)
    code = message.text.upper()
    user_id = message.from_user.id
    
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM promo_redeems WHERE user_id=? AND code=?", (user_id, code))
    if c.fetchone():
        bot.send_message(message.chat.id, "🚫 Already used this code.", reply_markup=main_reply_keyboard())
    else:
        c.execute("SELECT amount, max_uses, current_uses FROM promo_codes WHERE code=?", (code,))
        promo = c.fetchone()
        if promo and promo[2] < promo[1]:
            c.execute("UPDATE promo_codes SET current_uses = current_uses + 1 WHERE code=?", (code,))
            c.execute("INSERT INTO promo_redeems (user_id, code) VALUES (?, ?)", (user_id, code))
            c.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (promo[0], user_id))
            conn.commit()
            bot.send_message(message.chat.id, f"🎉 *SUCCESS!* `₹{promo[0]:.2f}` added!", parse_mode="Markdown", reply_markup=main_reply_keyboard())
        else:
            bot.send_message(message.chat.id, "🚫 Invalid or expired code.", reply_markup=main_reply_keyboard())
    conn.close()
    user_states.pop(user_id, None)

# =======================================================================================
# 10. WALLET / FUNDS (TEXT ONLY TO PREVENT HANGING)
# =======================================================================================
@bot.message_handler(func=lambda message: message.text == "💳 Add Funds (Wallet)")
def trigger_add_funds(message):
    user_states[message.from_user.id] = {"state": "awaiting_amount"}
    bot.send_message(message.chat.id, f"💸 *TIME TO RELOAD*\nHow much ₹₹₹ to add? (Min ₹{MIN_DEPOSIT})", parse_mode="Markdown", reply_markup=cancel_keyboard())

@bot.message_handler(func=lambda message: message.from_user.id in user_states and user_states[message.from_user.id].get("state") == "awaiting_amount")
def process_amount(message):
    if message.text == "❌ Cancel Action": return cancel_state(message)
    try:
        amount = float(message.text)
        if amount < MIN_DEPOSIT: return bot.send_message(message.chat.id, f"🚫 Minimum is `₹{MIN_DEPOSIT}`.")
            
        user_states[message.from_user.id] = {"state": "awaiting_screenshot", "amount": amount}
        
        caption = (
            f"💳 *PAYMENT INITIATED: ₹{amount}* 💳\n\n"
            f"Please pay manually to this UPI ID: `{UPI_ID}`\n\n"
            f"📸 *CRITICAL STEP:*\nAfter paying, upload the **Screenshot** right here."
        )
        bot.send_message(message.chat.id, caption, parse_mode="Markdown")
    except:
        bot.send_message(message.chat.id, "🤨 Enter a valid number.")

@bot.message_handler(content_types=['photo'])
def handle_screenshot(message):
    user_id = message.from_user.id
    if user_id in user_states and user_states[user_id].get("state") == "awaiting_screenshot":
        amount = user_states[user_id]["amount"]
        
        conn = get_db()
        c = conn.cursor()
        c.execute("INSERT INTO transactions (user_id, amount, status) VALUES (?, ?, 'PENDING')", (user_id, amount))
        tx_id = c.lastrowid
        conn.commit()
        conn.close()

        bot.send_message(message.chat.id, "⏳ *SCREENSHOT RECEIVED!*\nSent to Admin.", parse_mode="Markdown", reply_markup=main_reply_keyboard())
        
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("✅ Approve", callback_data=f"ap_{tx_id}_{user_id}_{amount}"), InlineKeyboardButton("❌ Reject", callback_data=f"rj_{tx_id}_{user_id}"))
        bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=f"🚨 *DEPOSIT*\n🆔 `{user_id}`\n💰 `₹{amount}`\n🧾 `TXN-{tx_id}`", parse_mode="Markdown", reply_markup=markup)
        user_states.pop(user_id, None)

@bot.callback_query_handler(func=lambda call: call.data.startswith("ap_") or call.data.startswith("rj_"))
def admin_escrow_decision(call):
    if call.from_user.id != ADMIN_ID: return
    data = call.data.split("_")
    action, tx_id, user_id = data[0], int(data[1]), int(data[2])
    
    conn = get_db()
    if action == "ap":
        amount = float(data[3])
        conn.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
        conn.execute("UPDATE transactions SET status = 'APPROVED' WHERE tx_id = ?", (tx_id,))
        bot.edit_message_caption(caption=f"✅ *APPROVED*\nTXN-{tx_id} | User: `{user_id}` | `₹{amount}` added.", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown")
        try: bot.send_message(user_id, f"🎉 *BAG SECURED!* Admin approved `₹{amount}`. 🚀", parse_mode="Markdown")
        except: pass
    else:
        conn.execute("UPDATE transactions SET status = 'REJECTED' WHERE tx_id = ?", (tx_id,))
        bot.edit_message_caption(caption=f"❌ *REJECTED*\nTXN-{tx_id} | User: `{user_id}`", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown")
    conn.commit()
    conn.close()

# =======================================================================================
# 11. ADMIN COMMANDS
# =======================================================================================
@bot.message_handler(commands=['admin'])
def admin_menu(message):
    if message.from_user.id != ADMIN_ID: return
    bot.reply_to(message, "👑 *BOSS DASHBOARD*\n`/stats`\n`/addfunds [ID] [Amt]`\n`/makepromo [Amt] [Uses]`\n`/broadcast [Msg]`", parse_mode="Markdown")

@bot.message_handler(commands=['addfunds'])
def manual_add(message):
    if message.from_user.id != ADMIN_ID: return
    try:
        args = message.text.split()
        update_balance(int(args[1]), float(args[2]))
        bot.reply_to(message, f"✅ Added ₹{args[2]} to {args[1]}.")
    except: bot.reply_to(message, "Usage: `/addfunds [user_id] [amount]`")

@bot.message_handler(commands=['makepromo'])
def make_promo(message):
    if message.from_user.id != ADMIN_ID: return
    try:
        args = message.text.split()
        code = generate_random_code()
        conn = get_db()
        conn.execute("INSERT INTO promo_codes (code, amount, max_uses, created_by) VALUES (?, ?, ?, ?)", (code, float(args[1]), int(args[2]), ADMIN_ID))
        conn.commit()
        conn.close()
        bot.reply_to(message, f"✅ Code: `{code}`\nValue: ₹{args[1]}\nUses: {args[2]}", parse_mode="Markdown")
    except: bot.reply_to(message, "Usage: `/makepromo [amount] [uses]`")

@bot.message_handler(commands=['stats'])
def get_stats(message):
    if message.from_user.id != ADMIN_ID: return
    try:
        conn = get_db()
        u_stats = conn.execute("SELECT COUNT(*), SUM(balance), SUM(total_spent) FROM users").fetchone()
        o_stats = conn.execute("SELECT COUNT(*), SUM(cost) FROM orders").fetchone()
        conn.close()
        bot.reply_to(message, f"📊 *STATS*\nUsers: {u_stats[0]}\nTotal Balances: ₹{u_stats[1] or 0:.2f}\nTotal Spent: ₹{u_stats[2] or 0:.2f}\nOrders: {o_stats[0]}", parse_mode="Markdown")
    except: pass

@bot.message_handler(commands=['broadcast'])
def broadcast(message):
    if message.from_user.id != ADMIN_ID: return
    msg = message.text.replace("/broadcast ", "")
    conn = get_db()
    users = conn.execute("SELECT user_id FROM users").fetchall()
    conn.close()
    
    sent = 0
    bot.reply_to(message, "📢 Broadcasting...")
    for u in users:
        try:
            bot.send_message(u[0], msg, parse_mode="Markdown")
            sent += 1
            time.sleep(0.05)
        except: pass
    bot.send_message(ADMIN_ID, f"✅ Broadcast sent to {sent} users.")

# =======================================================================================
# 12. EXECUTION ENGINE
# =======================================================================================
def run_bot():
    print("--- [ INITIALIZING ENTERPRISE ENGINE ] ---")
    init_db()
    while True:
        try: 
            bot.infinity_polling(timeout=20, long_polling_timeout=10)
        except Exception as e:
            logger.error(f"System Crash: {e}")
            time.sleep(5)

if __name__ == '__main__':
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
