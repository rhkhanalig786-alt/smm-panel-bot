"""
=========================================================================================
🔥 CHEAP SMM PANEL BOT - ENTERPRISE V3 (RENDER EDITION) 🔥
=========================================================================================
Description: A fully-automated Telegram Bot for SMM Panel services.
Features:
- Render Support (Flask Keep-Alive + Threading)
- .env Security
- Direct API Purchasing (Auto-deducts balance & sends to panel)
- Dynamic API pricing (45% markup)
- Escrow Payment System (Amount -> QR -> Screenshot -> Admin Approve)
- VIP Tier System & Daily Rewards
- Order Tracking & Status Checking
- Promo Code Engine
- Built-in Support Ticket System
- Referral (Affiliate) Engine
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
from datetime import datetime, timedelta
from dotenv import load_dotenv
from flask import Flask
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove

# =======================================================================================
# 1. ADVANCED LOGGING SYSTEM
# =======================================================================================
logging.basicConfig(
    filename='bot_enterprise.log',
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# =======================================================================================
# 2. CORE CONFIGURATION & CREDENTIALS (.ENV SECURED)
# =======================================================================================
load_dotenv() # Loads the local .env file (Render will use its own Environment Variables)

BOT_TOKEN = os.environ.get('8228287584:AAFa93-H1WLx-sY_JNO3XJmeqzOogPImhqM')
API_KEY = os.environ.get('iyQl8EohC0u3Be7I6FTh054FUHBJPRVE761vsZB02dNF5kkSznjVfNGThZfoYRhN')

if not BOT_TOKEN or not API_KEY:
    print("❌ CRITICAL ERROR: BOT_TOKEN or API_KEY is missing from environment variables!")

bot = telebot.TeleBot(BOT_TOKEN)
API_URL = "https://indiansmmprovider.in/api/v2"

# ADMIN & SUPPORT DETAILS
ADMIN_ID = 6034840006  
SUPPORT_HANDLE = "@Not_your_rahi" 
SUPPORT_LINK = f"https://t.me/{SUPPORT_HANDLE.replace('@', '')}"

# PAYMENT & ECONOMY SETTINGS
UPI_ID = "rahikhann@fam"
MIN_DEPOSIT = 10.0  
MARKUP_PERCENTAGE = 1.45 # 45% Profit Markup
REFERRAL_BONUS = 5.0 

# TARGET SERVICE IDS
TARGET_IDS = [15979, 16411, 16453, 16441, 16439, 15397, 16451, 15843]

user_states = {}

# =======================================================================================
# 3. ENTERPRISE RELATIONAL DATABASE ENGINE
# =======================================================================================
def init_db():
    try:
        conn = sqlite3.connect('panel_enterprise.db', check_same_thread=False)
        c = conn.cursor()
        
        c.execute('''CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT, 
                balance REAL DEFAULT 0.0, total_spent REAL DEFAULT 0.0,
                last_daily TIMESTAMP DEFAULT '2000-01-01 00:00:00',
                referred_by INTEGER DEFAULT 0, join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
                
        c.execute('''CREATE TABLE IF NOT EXISTS transactions (
                tx_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
                amount REAL, status TEXT, date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
                
        c.execute('''CREATE TABLE IF NOT EXISTS orders (
                db_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
                api_order_id TEXT, service_id INTEGER, link TEXT, quantity INTEGER,
                cost REAL, status TEXT DEFAULT 'Pending', date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
                
        c.execute('''CREATE TABLE IF NOT EXISTS promo_codes (
                code TEXT PRIMARY KEY, amount REAL, max_uses INTEGER DEFAULT 1,
                current_uses INTEGER DEFAULT 0, created_by INTEGER)''')
                
        c.execute('''CREATE TABLE IF NOT EXISTS promo_redeems (
                user_id INTEGER, code TEXT, date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, code))''')

        c.execute('''CREATE TABLE IF NOT EXISTS tickets (
                ticket_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
                subject TEXT, status TEXT DEFAULT 'OPEN', date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

        conn.commit()
        conn.close()
        logger.info("Enterprise Database Engine Initialized.")
    except Exception as e:
        logger.error(f"Database Init Error: {e}")

def get_user(user_id, username=None, first_name=None, ref_by=0):
    try:
        conn = sqlite3.connect('panel_enterprise.db', check_same_thread=False)
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
        user = c.fetchone()
        
        if not user and username is not None:
            c.execute('INSERT INTO users (user_id, username, first_name, balance, total_spent, referred_by) VALUES (?, ?, ?, 0.0, 0.0, ?)',
                      (user_id, username, first_name, ref_by))
            conn.commit()
            if ref_by != 0:
                try: bot.send_message(ref_by, f"🎉 *New Referral!* `{first_name}` joined using your link!")
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
    except Exception as e:
        logger.error(f"Balance Update Error: {e}")
        return False

def increase_total_spent(user_id, amount):
    try:
        conn = sqlite3.connect('panel_enterprise.db', check_same_thread=False)
        c = conn.cursor()
        c.execute("UPDATE users SET total_spent = total_spent + ? WHERE user_id = ?", (amount, user_id))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Total Spent Update Error: {e}")

# =======================================================================================
# 4. VIP TIER & REWARD CALCULATOR
# =======================================================================================
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
# 5. SMM PANEL API CORE
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
    except Exception as e:
        logger.error(f"API Fetch Error: {e}")
        return None

def api_place_order(service_id, link, quantity):
    try:
        payload = {'key': API_KEY, 'action': 'add', 'service': service_id, 'link': link, 'quantity': quantity}
        response = requests.post(API_URL, data=payload, timeout=20)
        result = response.json()
        if 'order' in result: return {"status": "success", "order_id": result['order']}
        else: return {"status": "error", "message": result.get('error', 'Unknown API Error')}
    except Exception as e:
        logger.error(f"API Order Error: {e}")
        return {"status": "error", "message": "Failed to connect to the panel."}

def api_check_status(order_id):
    try:
        payload = {'key': API_KEY, 'action': 'status', 'order': order_id}
        response = requests.post(API_URL, data=payload, timeout=15)
        result = response.json()
        if 'status' in result: return result['status']
        return "Unknown"
    except Exception as e:
        logger.error(f"API Status Error: {e}")
        return "Error fetching status"

# =======================================================================================
# 6. UI KEYBOARDS & NAVIGATION
# =======================================================================================
def main_reply_keyboard():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(KeyboardButton("🛒 Browse Services 🚀"))
    markup.add(KeyboardButton("💰 My Drip (Profile)"), KeyboardButton("💳 Add Funds (Wallet)"))
    markup.add(KeyboardButton("📦 Order History"), KeyboardButton("🎁 Daily Bonus"))
    markup.add(KeyboardButton("🎫 Redeem Promo"), KeyboardButton("📞 Support / Help"))
    return markup

def cancel_keyboard():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton("❌ Cancel Action"))
    return markup

# =======================================================================================
# 7. WELCOME & REFERRAL HANDLER
# =======================================================================================
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
    tier = get_vip_tier(user[4])
    
    welcome_msg = (
        f"Yooo, welcome to the plug 🔌✨, *{message.from_user.first_name}*!\n\n"
        f"🔥 *CHEAP SMM PANEL V3* 🔥\n"
        f"Direct API Access. Instant Orders. No Cap. 🧢🚫\n\n"
        f"💸 *Your Stash:* `₹{user[3]:.2f}`\n"
        f"👑 *Rank:* {tier}\n"
        f"🆔 *Your ID:* `{user[0]}`\n\n"
        f"👇 *Hit the menu below to level up your socials!*"
    )
    bot.send_message(message.chat.id, welcome_msg, parse_mode="Markdown", reply_markup=main_reply_keyboard())

@bot.message_handler(func=lambda message: message.text == "❌ Cancel Action")
def cancel_state(message):
    if message.from_user.id in user_states: del user_states[message.from_user.id]
    bot.send_message(message.chat.id, "🚫 *Action Cancelled.* We go back to the lobby.", parse_mode="Markdown", reply_markup=main_reply_keyboard())

# =======================================================================================
# 8. PRIMARY MENU HANDLERS
# =======================================================================================
@bot.message_handler(func=lambda message: message.text == "🛒 Browse Services 🚀")
def show_services(message):
    bot.send_chat_action(message.chat.id, 'typing')
    service_data = api_get_services()
    if not service_data:
        bot.send_message(message.chat.id, "API is acting sus. Try again in a min.")
        return
    markup = InlineKeyboardMarkup(row_width=1)
    for s_id in TARGET_IDS:
        if s_id in service_data:
            btn_text = f"🔥 {service_data[s_id]['name']} - ₹{service_data[s_id]['rate']:.2f}"
            markup.add(InlineKeyboardButton(btn_text, callback_data=f"info_{s_id}"))
    bot.send_message(message.chat.id, "🛒 *The Main Roster*\nTap a service to check stats & buy:", parse_mode="Markdown", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == "💰 My Drip (Profile)")
def show_profile(message):
    user = get_user(message.from_user.id)
    ref_link = f"https://t.me/{bot.get_me().username}?start=ref{user[0]}"
    text = (
        f"💧 *THE VAULT - PROFILE CHECK* 💧\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 *User ID:* `{user[0]}`\n👤 *Alias:* {user[2]}\n👑 *Status:* {get_vip_tier(user[4])}\n\n"
        f"💰 *Current Stash:* `₹{user[3]:.2f}`\n📈 *Total Flexed:* `₹{user[4]:.2f}`\n"
        f"━━━━━━━━━━━━━━━━━━━\n🤝 *Affiliate Program:*\n🔗 `{ref_link}`\n_Earn ₹{REFERRAL_BONUS} on first deposit!_"
    )
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == "🎁 Daily Bonus")
def claim_daily(message):
    user = get_user(message.from_user.id)
    last_claim = datetime.strptime(user[5], '%Y-%m-%d %H:%M:%S')
    now = datetime.now()
    if now - last_claim > timedelta(days=1):
        update_balance(message.from_user.id, 1.0)
        conn = sqlite3.connect('panel_enterprise.db', check_same_thread=False)
        c = conn.cursor()
        c.execute("UPDATE users SET last_daily = CURRENT_TIMESTAMP WHERE user_id = ?", (message.from_user.id,))
        conn.commit()
        conn.close()
        bot.send_message(message.chat.id, "🎉 You claimed your daily `₹1.00`. W Drip!", parse_mode="Markdown")
    else:
        tl = timedelta(days=1) - (now - last_claim)
        bot.send_message(message.chat.id, f"🛑 Chill bro. Come back in `{tl.seconds//3600}h {(tl.seconds//60)%60}m`.", parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == "📞 Support / Help")
def support_menu(message):
    text = f"🛠️ *HELP DESK*\nNeed admin help? Reach out here: {SUPPORT_LINK}"
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

# =======================================================================================
# 9. AUTOMATED ORDERING ENGINE
# =======================================================================================
@bot.callback_query_handler(func=lambda call: call.data.startswith("info_"))
def show_service_details(call):
    s_id = int(call.data.split("_")[1])
    data = api_get_services()
    if not data or s_id not in data:
        bot.answer_callback_query(call.id, "Service offline. Try again.", show_alert=True)
        return
    s = data[s_id]
    detail_text = (f"📊 *SERVICE STATS*\n🏷️ *Service:* {s['name']}\n🆔 *ID:* `{s_id}`\n"
                   f"💰 *Price (per 1k):* `₹{s['rate']:.2f}`\n📉 *Limits:* Min {s['min']} | Max {s['max']}")
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🛒 Purchase Directly", callback_data=f"buy_{s_id}"))
    bot.edit_message_text(detail_text, call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("buy_"))
def initiate_purchase(call):
    s_id = int(call.data.split("_")[1])
    user_states[call.from_user.id] = {"state": "ordering_link", "service_id": s_id}
    bot.delete_message(call.message.chat.id, call.message.message_id)
    bot.send_message(call.message.chat.id, "🔗 Send the *Target Link*:", parse_mode="Markdown", reply_markup=cancel_keyboard())

@bot.message_handler(func=lambda message: message.from_user.id in user_states and user_states[message.from_user.id].get("state") == "ordering_link")
def get_order_link(message):
    if message.text == "❌ Cancel Action": return cancel_state(message)
    user_id = message.from_user.id
    s_id = user_states[user_id]["service_id"]
    data = api_get_services()
    if not data or s_id not in data:
        bot.send_message(message.chat.id, "Provider error. Try later.", reply_markup=main_reply_keyboard())
        del user_states[user_id]
        return
    user_states[user_id].update({"state": "ordering_qty", "link": message.text, "rate": data[s_id]['rate'], "min": data[s_id]['min'], "max": data[s_id]['max']})
    bot.send_message(message.chat.id, f"🔢 Enter quantity ({data[s_id]['min']} - {data[s_id]['max']}):", parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.from_user.id in user_states and user_states[message.from_user.id].get("state") == "ordering_qty")
def process_order(message):
    if message.text == "❌ Cancel Action": return cancel_state(message)
    user_id = message.from_user.id
    sd = user_states[user_id]
    try: qty = int(message.text)
    except: return bot.send_message(message.chat.id, "Enter numbers only.")
    
    if qty < sd["min"] or qty > sd["max"]: return bot.send_message(message.chat.id, f"🚫 Keep it between {sd['min']} and {sd['max']}.")
    cost = (qty / 1000) * sd["rate"]
    
    user = get_user(user_id)
    if user[3] < cost:
        bot.send_message(message.chat.id, f"❌ Need `₹{cost:.2f}` but you have `₹{user[3]:.2f}`. Add funds.", parse_mode="Markdown", reply_markup=main_reply_keyboard())
        del user_states[user_id]
        return
        
    bot.send_message(message.chat.id, "⏳ Processing...")
    update_balance(user_id, -cost)
    api_res = api_place_order(sd["service_id"], sd["link"], qty)
    
    if api_res["status"] == "success":
        try:
            conn = sqlite3.connect('panel_enterprise.db', check_same_thread=False)
            conn.execute("INSERT INTO orders (user_id, api_order_id, service_id, link, quantity, cost) VALUES (?, ?, ?, ?, ?, ?)",
                         (user_id, api_res["order_id"], sd["service_id"], sd["link"], qty, cost))
            conn.commit()
            conn.close()
        except: pass
        increase_total_spent(user_id, cost)
        bot.send_message(message.chat.id, f"✅ *ORDER PLACED!*\n🧾 ID: `{api_res['order_id']}`\n💰 Cost: `₹{cost:.2f}`\n🚀 Starts in 30 mins.\n⚠️ Help? Contact {SUPPORT_HANDLE}", parse_mode="Markdown", reply_markup=main_reply_keyboard())
    else:
        update_balance(user_id, cost)
        bot.send_message(message.chat.id, f"❌ *FAILED*\nServer said: {api_res['message']}\nRefunded `₹{cost:.2f}`.", parse_mode="Markdown", reply_markup=main_reply_keyboard())
    del user_states[user_id]

# =======================================================================================
# 10. ESCROW QR DEPOSIT SYSTEM
# =======================================================================================
@bot.message_handler(func=lambda message: message.text == "💳 Add Funds (Wallet)")
def trigger_add_funds(message):
    user_states[message.from_user.id] = {"state": "awaiting_amount"}
    bot.send_message(message.chat.id, f"💸 How much ₹₹₹ to add? (Min ₹{MIN_DEPOSIT})", reply_markup=cancel_keyboard())

@bot.message_handler(func=lambda message: message.from_user.id in user_states and user_states[message.from_user.id].get("state") == "awaiting_amount")
def process_amount(message):
    if message.text == "❌ Cancel Action": return cancel_state(message)
    try:
        amt = float(message.text)
        if amt < MIN_DEPOSIT: return bot.send_message(message.chat.id, f"🚫 Minimum `₹{MIN_DEPOSIT}`.")
        user_states[message.from_user.id] = {"state": "awaiting_screenshot", "amount": amt}
        qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=400x400&data={urllib.parse.quote(f'upi://pay?pa={UPI_ID}&pn=Admin&am={amt}&cu=INR')}"
        bot.send_photo(message.chat.id, qr_url, caption=f"💳 Scan to pay ₹{amt} or use `{UPI_ID}`.\n📸 Then upload screenshot here.", parse_mode="Markdown")
    except: bot.send_message(message.chat.id, "Enter a valid number.")

@bot.message_handler(content_types=['photo'])
def handle_screenshot(message):
    u_id = message.from_user.id
    if u_id in user_states and user_states[u_id].get("state") == "awaiting_screenshot":
        amt = user_states[u_id]["amount"]
        conn = sqlite3.connect('panel_enterprise.db', check_same_thread=False)
        c = conn.cursor()
        c.execute("INSERT INTO transactions (user_id, amount, status) VALUES (?, ?, 'PENDING')", (u_id, amt))
        tx_id = c.lastrowid
        conn.commit()
        conn.close()
        
        bot.send_message(message.chat.id, "⏳ Sent to Admin. Wait for approval.", reply_markup=main_reply_keyboard())
        del user_states[u_id]
        
        markup = InlineKeyboardMarkup().add(InlineKeyboardButton("✅ Apprv", callback_data=f"apprv_{tx_id}_{u_id}_{amt}"), InlineKeyboardButton("❌ Rjct", callback_data=f"rjct_{tx_id}_{u_id}_{amt}"))
        bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=f"🚨 DEP REQ\nUser: `{u_id}`\nClaim: `₹{amt}`\nTXN: `TXN-{tx_id}`", parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("apprv_") or call.data.startswith("rjct_"))
def admin_decision(call):
    if call.from_user.id != ADMIN_ID: return
    action, tx_id, u_id, amt = call.data.split("_")[0], int(call.data.split("_")[1]), int(call.data.split("_")[2]), float(call.data.split("_")[3])
    
    conn = sqlite3.connect('panel_enterprise.db', check_same_thread=False)
    if action == "apprv":
        conn.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amt, u_id))
        conn.execute("UPDATE transactions SET status = 'APPROVED' WHERE tx_id = ?", (tx_id,))
        bot.edit_message_caption(caption=f"✅ APPRV TXN-{tx_id} | User: `{u_id}` | `₹{amt}` added.", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown")
        try: bot.send_message(u_id, f"🎉 Admin approved! `₹{amt}` added.", parse_mode="Markdown")
        except: pass
        
        ref = conn.execute("SELECT referred_by FROM users WHERE user_id=?", (u_id,)).fetchone()[0]
        if ref != 0 and conn.execute("SELECT COUNT(*) FROM transactions WHERE user_id=? AND status='APPROVED'", (u_id,)).fetchone()[0] == 1:
            conn.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (REFERRAL_BONUS, ref))
            try: bot.send_message(ref, f"🤑 Affiliate Payout! `₹{REFERRAL_BONUS}` added.", parse_mode="Markdown")
            except: pass
    else:
        conn.execute("UPDATE transactions SET status = 'REJECTED' WHERE tx_id = ?", (tx_id,))
        bot.edit_message_caption(caption=f"❌ RJCT TXN-{tx_id}", chat_id=call.message.chat.id, message_id=call.message.message_id)
        try: bot.send_message(u_id, "🚫 Deposit rejected.")
        except: pass
    conn.commit()
    conn.close()

# =======================================================================================
# 11. ADMIN DASHBOARD
# =======================================================================================
@bot.message_handler(commands=['admin'])
def admin_menu(message):
    if message.from_user.id == ADMIN_ID:
        bot.reply_to(message, "👑 *BOSS DASHBOARD*\n`/stats` - View stats\n`/addfunds [id] [amt]`\n`/makepromo [amt] [uses]`", parse_mode="Markdown")

# =======================================================================================
# 12. RENDER KEEP-ALIVE SERVER & THREADING EXECUTION
# =======================================================================================
app = Flask(__name__)

@app.route('/')
def home():
    return "🔥 CHEAP SMM PANEL BOT IS ONLINE 🔥"

def run_bot():
    print("--- [ INITIALIZING ENTERPRISE ENGINE ] ---")
    init_db()
    print("--- [ BOT V3 RUNNING - DIRECT API ENABLED ] ---")
    while True:
        try:
            bot.infinity_polling(timeout=20, long_polling_timeout=10)
        except Exception as e:
            logger.error(f"System Crash: {e}")
            time.sleep(5)

if __name__ == '__main__':
    # Starts the Telegram Bot logic in a background thread
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.start()
    
    # Starts the Flask Web Server in the main thread for Render
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
