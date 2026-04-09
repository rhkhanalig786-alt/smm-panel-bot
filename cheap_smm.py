"""
=========================================================================================
🔥 CHEAP SMM PANEL BOT - ENTERPRISE V7 (MASTER CONTROL EDITION) 🔥
=========================================================================================
Description: A fully autonomous, Render-safe Telegram SMM Panel Bot.
Features Included:
- Flask Web Server (Render Port-Binding Safe)
- Dynamic Admin Service Manager (Add/Remove services via API)
- God Mode Admin Dashboard (Add/Deduct Funds, Broadcast, DM)
- Live Order Tracking & Low Balance Alerts
- Support Ticket System (User to Admin communication)
- Escrow Payment Verification
- VIP Tier System & Referral Program
- Thread-safe SQLite Database Manager
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
import threading
from flask import Flask
from datetime import datetime, timedelta
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# =======================================================================================
# 1. SERVER, LOGGING & CONFIGURATION
# =======================================================================================
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Flask App for Render to bind to a port and keep the service alive
app = Flask(__name__)
@app.route('/')
def home(): 
    return "🔥 ENTERPRISE V7 MASTER CONTROL IS ONLINE AND OPERATIONAL 🔥"

# --- CREDENTIALS & TOKENS ---
# Always use environment variables on Render, fallback to hardcoded strings for testing
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8228287584:AAF0d6vp2OMQLSw445PJVTsp98JDdVDY7EY')
API_KEY = os.environ.get('API_KEY', 'w4NIpEsjLOWxMM87R0ZxiPeMgu2ri8ugJeYPmMa206aPmOhDu9NJSl13mvQvPUEZ')
bot = telebot.TeleBot(BOT_TOKEN)

API_URL = "https://indiansmmprovider.in/api/v2"
ADMIN_ID = 6034840006  
UPI_ID = "rahikhann@fam"

# --- BUSINESS LOGIC VARIABLES ---
DEFAULT_MARGIN = 1.45       # Default 45% profit margin on new services
MIN_DEPOSIT = 10.0          # Minimum ₹10 deposit
LOW_BAL_ALERT = 15.0        # Alert user if balance drops below ₹15
REFERRAL_BONUS = 5.0        # ₹5 bonus for referring a new paying user
DAILY_BONUS_AMT = 1.0       # ₹1 daily claim

user_states = {}            # Temporary memory for user conversation flows

# =======================================================================================
# 2. THREAD-SAFE DATABASE MANAGER
# =======================================================================================
def execute_db(query, params=(), fetch=False, fetch_all=False, return_id=False):
    """
    Safely opens, executes, and closes the SQLite database. 
    Prevents 'Database is locked' errors on cloud hosting like Render.
    """
    try:
        with sqlite3.connect('panel_enterprise.db', check_same_thread=False, timeout=20) as conn:
            c = conn.cursor()
            c.execute(query, params)
            if fetch: 
                return c.fetchone()
            if fetch_all: 
                return c.fetchall()
            if return_id:
                conn.commit()
                return c.lastrowid
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"Database Execution Error: {e} | Query: {query}")
        return False

def init_database():
    """Initializes all 7 tables required for the Enterprise Bot."""
    logger.info("Initializing Enterprise Database Architecture...")
    
    # 1. Users Table
    execute_db('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY, 
        username TEXT, 
        first_name TEXT, 
        balance REAL DEFAULT 0.0, 
        total_spent REAL DEFAULT 0.0, 
        last_daily TIMESTAMP DEFAULT '2000-01-01 00:00:00', 
        referred_by INTEGER DEFAULT 0, 
        join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # 2. Transactions Table (For Add Funds Escrow)
    execute_db('''CREATE TABLE IF NOT EXISTS transactions (
        tx_id INTEGER PRIMARY KEY AUTOINCREMENT, 
        user_id INTEGER, 
        amount REAL, 
        status TEXT, 
        date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # 3. Orders Table
    execute_db('''CREATE TABLE IF NOT EXISTS orders (
        db_id INTEGER PRIMARY KEY AUTOINCREMENT, 
        user_id INTEGER, 
        api_order_id TEXT, 
        service_id INTEGER, 
        quantity INTEGER, 
        cost REAL, 
        date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # 4. Managed Services Table (Admin dynamically controls this)
    execute_db('''CREATE TABLE IF NOT EXISTS managed_services (
        service_id INTEGER PRIMARY KEY, 
        name TEXT, 
        rate REAL, 
        margin REAL DEFAULT 1.45
    )''')
    
    # 5. Promo Codes Table
    execute_db('''CREATE TABLE IF NOT EXISTS promo_codes (
        code TEXT PRIMARY KEY, 
        amount REAL, 
        max_uses INTEGER DEFAULT 1, 
        current_uses INTEGER DEFAULT 0
    )''')
    
    # 6. Promo Redeems Table (Prevents double claiming)
    execute_db('''CREATE TABLE IF NOT EXISTS promo_redeems (
        user_id INTEGER, 
        code TEXT, 
        date TIMESTAMP DEFAULT CURRENT_TIMESTAMP, 
        PRIMARY KEY (user_id, code)
    )''')
    
    # 7. Support Tickets Table
    execute_db('''CREATE TABLE IF NOT EXISTS tickets (
        ticket_id INTEGER PRIMARY KEY AUTOINCREMENT, 
        user_id INTEGER, 
        message TEXT, 
        status TEXT DEFAULT 'OPEN', 
        date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    logger.info("Database Architecture Secured.")

# =======================================================================================
# 3. UTILITY FUNCTIONS & LOGIC
# =======================================================================================
def get_or_create_user(user_id, username=None, first_name=None, ref_by=0):
    """Fetches user data. Creates a new record if they don't exist."""
    user = execute_db("SELECT * FROM users WHERE user_id=?", (user_id,), fetch=True)
    if not user and username is not None:
        execute_db("INSERT INTO users (user_id, username, first_name, referred_by) VALUES (?, ?, ?, ?)", 
                   (user_id, username, first_name, ref_by))
        
        # Notify referrer if applicable
        if ref_by != 0 and ref_by != user_id:
            try:
                bot.send_message(ref_by, f"🎉 *New Referral!* {first_name} joined using your link!", parse_mode="Markdown")
            except Exception:
                pass # Prevent crash if referrer blocked the bot
                
        user = execute_db("SELECT * FROM users WHERE user_id=?", (user_id,), fetch=True)
    return user

def get_vip_tier(total_spent):
    """Determines user rank based on lifetime spending."""
    if total_spent >= 10000: return "🌌 Cosmic Whale"
    if total_spent >= 5000: return "💎 Diamond Boss"
    if total_spent >= 1000: return "🥇 Gold Member"
    if total_spent >= 500: return "🥈 Silver Hustler"
    return "🥉 Bronze Starter"

def call_smm_api(action, extra_data=None):
    """Generic wrapper to communicate with the SMM Provider."""
    payload = {'key': API_KEY, 'action': action}
    if extra_data:
        payload.update(extra_data)
    try:
        response = requests.post(API_URL, data=payload, timeout=20)
        return response.json()
    except Exception as e:
        logger.error(f"API Connection Error: {e}")
        return None

# =======================================================================================
# 4. DYNAMIC UI KEYBOARDS
# =======================================================================================
def generate_main_keyboard(user_id):
    """Generates the main menu. Shows God Mode buttons only to the Admin."""
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(KeyboardButton("🛒 Browse Services 🚀"), KeyboardButton("💰 My Drip (Profile)"))
    kb.add(KeyboardButton("💳 Add Funds (Wallet)"), KeyboardButton("📦 Order History"))
    kb.add(KeyboardButton("🎁 Daily Bonus"), KeyboardButton("🎫 Promo Code"))
    kb.add(KeyboardButton("📞 Support / Tickets"))
    
    if user_id == ADMIN_ID:
        kb.add(KeyboardButton("👑 --- ADMIN ZONE --- 👑"))
        kb.add(KeyboardButton("⚙️ Manage Services"), KeyboardButton("💰 God Mode Funds"))
        kb.add(KeyboardButton("📢 Broadcast"), KeyboardButton("📩 Direct Msg"))
        kb.add(KeyboardButton("🎟️ View Open Tickets"))
    return kb

def cancel_keyboard():
    """Universal cancel button to escape state loops."""
    return ReplyKeyboardMarkup(resize_keyboard=True).add(KeyboardButton("❌ Cancel Action"))

# =======================================================================================
# 5. CORE BOT HANDLERS
# =======================================================================================
@bot.message_handler(commands=['start'])
def handle_start(message):
    """Entry point. Handles referral logic and creates user."""
    user_id = message.from_user.id
    
    # Extract referral code if present
    ref_by = 0
    if len(message.text.split()) > 1 and message.text.split()[1].startswith('ref'):
        try: 
            ref_by = int(message.text.split()[1].replace('ref', ''))
            if ref_by == user_id: ref_by = 0 # Prevent self-referral
        except ValueError: 
            pass

    # Clear any stuck state
    user_states.pop(user_id, None) 
    
    user = get_or_create_user(user_id, message.from_user.username, message.from_user.first_name, ref_by)
    
    welcome_text = (
        f"⚡ *WELCOME TO THE ENTERPRISE PANEL* ⚡\n\n"
        f"👋 Yo {message.from_user.first_name}, you're officially in.\n"
        f"💰 *Wallet:* `₹{user[3]:.2f}`\n"
        f"👑 *Rank:* {get_vip_tier(user[4])}\n\n"
        f"Use the menu below to navigate the system."
    )
    bot.send_message(message.chat.id, welcome_text, parse_mode="Markdown", reply_markup=generate_main_keyboard(user_id))

@bot.message_handler(func=lambda m: m.text in ["❌ Cancel Action", "👑 --- ADMIN ZONE --- 👑"])
def handle_cancel_or_dummy(message):
    """Clears user state and returns to main menu."""
    user_states.pop(message.from_user.id, None)
    if message.text == "❌ Cancel Action":
        bot.send_message(message.chat.id, "🚫 Action Cancelled. Returning to lobby.", reply_markup=generate_main_keyboard(message.from_user.id))

# =======================================================================================
# 6. USER PROFILE & REWARDS
# =======================================================================================
@bot.message_handler(func=lambda m: m.text == "💰 My Drip (Profile)")
def handle_profile(message):
    user_id = message.from_user.id
    user = get_or_create_user(user_id)
    ref_link = f"https://t.me/{bot.get_me().username}?start=ref{user_id}"
    
    profile_text = (
        f"💧 *USER PROFILE* 💧\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 *ID:* `{user[0]}`\n"
        f"👤 *Username:* {user[1]}\n"
        f"💰 *Balance:* `₹{user[3]:.2f}`\n"
        f"📈 *Total Spent:* `₹{user[4]:.2f}`\n"
        f"👑 *VIP Tier:* {get_vip_tier(user[4])}\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"🤝 *REFERRAL PROGRAM*\n"
        f"Share this link. If your friend joins and makes a deposit, you get `₹{REFERRAL_BONUS}`!\n"
        f"🔗 `{ref_link}`"
    )
    bot.send_message(message.chat.id, profile_text, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🎁 Daily Bonus")
def handle_daily_bonus(message):
    user_id = message.from_user.id
    user = get_or_create_user(user_id)
    last_claim = datetime.strptime(user[5], '%Y-%m-%d %H:%M:%S')
    
    if datetime.now() - last_claim > timedelta(days=1):
        execute_db("UPDATE users SET balance = balance + ?, last_daily = CURRENT_TIMESTAMP WHERE user_id = ?", (DAILY_BONUS_AMT, user_id))
        bot.send_message(message.chat.id, f"🎉 *Claimed!* `₹{DAILY_BONUS_AMT:.2f}` added to your wallet.", parse_mode="Markdown")
    else:
        # Calculate time remaining
        next_claim = last_claim + timedelta(days=1)
        remaining = next_claim - datetime.now()
        hours, remainder = divmod(remaining.seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        bot.send_message(message.chat.id, f"🛑 *Too early!* Come back in `{hours}h {minutes}m`.", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🎫 Promo Code")
def handle_promo_start(message):
    user_states[message.from_user.id] = {"state": "promo"}
    bot.send_message(message.chat.id, "🎫 *Enter your Promo Code:*", parse_mode="Markdown", reply_markup=cancel_keyboard())

@bot.message_handler(func=lambda m: m.from_user.id in user_states and user_states[m.from_user.id].get("state") == "promo")
def handle_promo_redeem(message):
    if message.text == "❌ Cancel Action": return handle_cancel_or_dummy(message)
    user_id = message.from_user.id
    code = message.text.strip().upper()
    
    # Check if already redeemed
    if execute_db("SELECT * FROM promo_redeems WHERE user_id=? AND code=?", (user_id, code), fetch=True):
        bot.send_message(message.chat.id, "🚫 You have already used this code.", reply_markup=generate_main_keyboard(user_id))
    else:
        # Check if code is valid and has uses left
        promo = execute_db("SELECT amount, max_uses, current_uses FROM promo_codes WHERE code=?", (code,), fetch=True)
        if promo and promo[2] < promo[1]:
            execute_db("UPDATE promo_codes SET current_uses = current_uses + 1 WHERE code=?", (code,))
            execute_db("INSERT INTO promo_redeems (user_id, code) VALUES (?, ?)", (user_id, code))
            execute_db("UPDATE users SET balance = balance + ? WHERE user_id=?", (promo[0], user_id))
            bot.send_message(message.chat.id, f"🎉 *SUCCESS!* `₹{promo[0]:.2f}` added to your wallet!", parse_mode="Markdown", reply_markup=generate_main_keyboard(user_id))
        else:
            bot.send_message(message.chat.id, "🚫 Invalid, expired, or fully used promo code.", reply_markup=generate_main_keyboard(user_id))
    
    user_states.pop(user_id, None)

# =======================================================================================
# 7. SERVICE BROWSING & ORDERING FLOW
# =======================================================================================
@bot.message_handler(func=lambda m: m.text == "🛒 Browse Services 🚀")
def handle_browse(message):
    """Dynamically fetches services from the Admin's managed_services table."""
    services = execute_db("SELECT service_id, name, rate, margin FROM managed_services", fetch_all=True)
    
    if not services:
        return bot.send_message(message.chat.id, "⚠️ The store is currently empty or under maintenance. Check back later!")
    
    kb = InlineKeyboardMarkup(row_width=1)
    for s in services:
        # Calculate final price = Provider Rate * Admin Margin
        final_rate = s[2] * s[3]
        kb.add(InlineKeyboardButton(f"🔥 {s[1]} - ₹{final_rate:.2f}/1k", callback_data=f"buy_{s[0]}"))
        
    bot.send_message(message.chat.id, "🛒 *SELECT A SERVICE TO ORDER:*", parse_mode="Markdown", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("buy_"))
def handle_buy_callback(call):
    """Starts the ordering process for a specific service."""
    service_id = int(call.data.split("_")[1])
    user_states[call.from_user.id] = {"state": "order_link", "service_id": service_id}
    
    # Clean up UI
    try: bot.delete_message(call.message.chat.id, call.message.message_id)
    except: pass
    
    bot.send_message(call.message.chat.id, "🔗 *STEP 1: Send Target Link*\n(Ensure the account/post is PUBLIC)", parse_mode="Markdown", reply_markup=cancel_keyboard())

@bot.message_handler(func=lambda m: m.from_user.id in user_states and user_states[m.from_user.id].get("state") == "order_link")
def handle_order_link(message):
    if message.text == "❌ Cancel Action": return handle_cancel_or_dummy(message)
    
    user_id = message.from_user.id
    target_link = message.text
    service_id = user_states[user_id]["service_id"]
    
    # We need min/max from API to guide the user
    api_res = call_smm_api('services')
    if not api_res:
        user_states.pop(user_id, None)
        return bot.send_message(message.chat.id, "❌ API Connection Error.", reply_markup=generate_main_keyboard(user_id))
        
    try:
        # Find limits
        s_data = next(i for i in api_res if int(i['service']) == service_id)
        min_q = int(s_data['min'])
        max_q = int(s_data['max'])
        
        user_states[user_id].update({
            "state": "order_qty", 
            "link": target_link, 
            "min": min_q, 
            "max": max_q
        })
        bot.send_message(message.chat.id, f"🔢 *STEP 2: Enter Quantity*\n📉 Min: `{min_q}` | 📈 Max: `{max_q}`", parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Service Data Error: {e}")
        user_states.pop(user_id, None)
        bot.send_message(message.chat.id, "❌ Service data unavailable.", reply_markup=generate_main_keyboard(user_id))

@bot.message_handler(func=lambda m: m.from_user.id in user_states and user_states[m.from_user.id].get("state") == "order_qty")
def handle_order_qty(message):
    if message.text == "❌ Cancel Action": return handle_cancel_or_dummy(message)
    user_id = message.from_user.id
    state = user_states[user_id]
    
    try:
        qty = int(message.text)
    except ValueError:
        return bot.send_message(message.chat.id, "🤨 Please enter numbers only (e.g. 1000).")
        
    if qty < state["min"] or qty > state["max"]:
        return bot.send_message(message.chat.id, f"🚫 Quantity must be between {state['min']} and {state['max']}.")
        
    # Get custom margin from DB
    s_db = execute_db("SELECT rate, margin FROM managed_services WHERE service_id=?", (state["service_id"],), fetch=True)
    if not s_db:
        user_states.pop(user_id, None)
        return bot.send_message(message.chat.id, "❌ Service no longer exists.", reply_markup=generate_main_keyboard(user_id))
        
    cost = (qty / 1000.0) * (s_db[0] * s_db[1])
    
    # Check Balance
    user = get_or_create_user(user_id)
    if user[3] < cost:
        user_states.pop(user_id, None)
        return bot.send_message(message.chat.id, f"❌ *Insufficient Funds*\nOrder Cost: `₹{cost:.2f}`\nYour Balance: `₹{user[3]:.2f}`", parse_mode="Markdown", reply_markup=generate_main_keyboard(user_id))
        
    # Process Order UI
    bot.send_chat_action(message.chat.id, 'typing')
    msg_wait = bot.send_message(message.chat.id, "⏳ *Connecting to Server...*", parse_mode="Markdown", reply_markup=generate_main_keyboard(user_id))
    
    # Call SMM API
    api_res = call_smm_api('add', {'service': state["service_id"], 'link': state["link"], 'quantity': qty})
    
    try: bot.delete_message(message.chat.id, msg_wait.message_id)
    except: pass

    if api_res and 'order' in api_res:
        new_balance = user[3] - cost
        order_id = api_res['order']
        
        # Deduct Balance & Record Order safely
        execute_db("UPDATE users SET balance = balance - ?, total_spent = total_spent + ? WHERE user_id=?", (cost, cost, user_id))
        execute_db("INSERT INTO orders (user_id, api_order_id, service_id, quantity, cost) VALUES (?,?,?,?,?)", 
                   (user_id, order_id, state["service_id"], qty, cost))
        
        bot.send_message(message.chat.id, f"✅ *ORDER PLACED SUCCESSFULLY*\n\n🧾 *ID:* `{order_id}`\n💰 *Cost:* `₹{cost:.2f}`\n💳 *Remaining:* `₹{new_balance:.2f}`", parse_mode="Markdown")
        
        # Low Balance Alert Feature
        if new_balance < LOW_BAL_ALERT:
            bot.send_message(message.chat.id, f"⚠️ *Low Balance Alert:*\nYou only have `₹{new_balance:.2f}` left. Don't forget to top up your wallet!", parse_mode="Markdown")
            
    else:
        error_msg = api_res.get('error', 'Unknown Error') if api_res else "API Unreachable"
        bot.send_message(message.chat.id, f"❌ *Order Failed at Provider:*\n`{error_msg}`", parse_mode="Markdown")

    user_states.pop(user_id, None)

# =======================================================================================
# 8. ORDER HISTORY & LIVE TRACKING
# =======================================================================================
@bot.message_handler(func=lambda m: m.text == "📦 Order History")
def handle_history(message):
    orders = execute_db("SELECT api_order_id, service_id, quantity, cost, date FROM orders WHERE user_id=? ORDER BY date DESC LIMIT 4", (message.from_user.id,), fetch_all=True)
    
    if not orders:
        return bot.send_message(message.chat.id, "You haven't placed any orders yet.")
        
    history_text = "📦 *RECENT ORDERS (LAST 4)* 📦\n\n"
    kb = InlineKeyboardMarkup(row_width=2)
    track_buttons = []
    
    for o in orders:
        o_date = o[4].split()[0] # Get just the date part
        history_text += f"🧾 *ID:* `{o[0]}` | 📅 {o_date}\n"
        history_text += f"   Qty: {o[2]} | Cost: `₹{o[3]:.2f}`\n\n"
        # Add a Live Tracking button for each order
        track_buttons.append(InlineKeyboardButton(f"🔄 Track {o[0]}", callback_data=f"track_{o[0]}"))
        
    kb.add(*track_buttons)
    bot.send_message(message.chat.id, history_text, parse_mode="Markdown", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("track_"))
def handle_live_tracking(call):
    order_id = call.data.split("_")[1]
    
    res = call_smm_api('status', {'order': order_id})
    if res and 'status' in res:
        status_text = (
            f"📊 *LIVE ORDER DATA*\n\n"
            f"🧾 *Order ID:* `{order_id}`\n"
            f"🚥 *Status:* `{res['status'].upper()}`\n"
            f"📈 *Start Count:* `{res.get('start_count', 'N/A')}`\n"
            f"📉 *Remains:* `{res.get('remains', 'N/A')}`\n"
            f"💰 *Charge:* `{res.get('charge', 'N/A')}`"
        )
        bot.send_message(call.message.chat.id, status_text, parse_mode="Markdown")
    else:
        bot.answer_callback_query(call.id, "Status currently unavailable from provider.", show_alert=True)

# =======================================================================================
# 9. ADD FUNDS & ESCROW SYSTEM (Render-Safe Text Version)
# =======================================================================================
@bot.message_handler(func=lambda m: m.text == "💳 Add Funds (Wallet)")
def handle_add_funds(message):
    user_states[message.from_user.id] = {"state": "fund_amount"}
    bot.send_message(message.chat.id, f"💸 *How much ₹ do you want to add?*\n(Minimum deposit: `₹{MIN_DEPOSIT}`)", parse_mode="Markdown", reply_markup=cancel_keyboard())

@bot.message_handler(func=lambda m: m.from_user.id in user_states and user_states[m.from_user.id].get("state") == "fund_amount")
def handle_fund_amount(message):
    if message.text == "❌ Cancel Action": return handle_cancel_or_dummy(message)
    user_id = message.from_user.id
    
    try:
        amount = float(message.text)
        if amount < MIN_DEPOSIT:
            return bot.send_message(message.chat.id, f"🚫 Deposit must be at least `₹{MIN_DEPOSIT}`.")
            
        user_states[user_id] = {"state": "fund_screenshot", "amount": amount}
        
        # TEXT ONLY INSTRUCTIONS (Prevents QR API hanging the bot on Render)
        instructions = (
            f"💳 *PAYMENT INSTRUCTIONS* 💳\n\n"
            f"1️⃣ Copy this UPI ID: `{UPI_ID}`\n"
            f"2️⃣ Open PhonePe/GPay/Paytm and send exactly `₹{amount}`.\n"
            f"3️⃣ **Take a screenshot** of the successful payment.\n"
            f"4️⃣ **Send that screenshot here** in this chat.\n\n"
            f"⚠️ _Your funds will be added as soon as the Admin verifies the screenshot._"
        )
        bot.send_message(message.chat.id, instructions, parse_mode="Markdown")
    except ValueError:
        bot.send_message(message.chat.id, "🤨 Please enter a valid number.")

@bot.message_handler(content_types=['photo'])
def handle_payment_screenshot(message):
    user_id = message.from_user.id
    if user_id in user_states and user_states[user_id].get("state") == "fund_screenshot":
        amount = user_states[user_id]["amount"]
        
        # Log Transaction as PENDING
        tx_id = execute_db("INSERT INTO transactions (user_id, amount, status) VALUES (?, ?, 'PENDING')", (user_id, amount), return_id=True)
        
        if tx_id:
            # Send to Admin Escrow
            kb = InlineKeyboardMarkup()
            kb.add(
                InlineKeyboardButton("✅ Approve", callback_data=f"escrow_ap_{tx_id}_{user_id}_{amount}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"escrow_rj_{tx_id}_{user_id}")
            )
            
            admin_caption = f"🚨 *NEW DEPOSIT REQUEST*\n🆔 User ID: `{user_id}`\n💰 Amount: `₹{amount}`\n🧾 TXN: `{tx_id}`"
            bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=admin_caption, parse_mode="Markdown", reply_markup=kb)
            
            bot.send_message(message.chat.id, "⏳ *Screenshot Received!*\nIt has been forwarded to the Admin for approval.", parse_mode="Markdown", reply_markup=generate_main_keyboard(user_id))
            user_states.pop(user_id, None)

@bot.callback_query_handler(func=lambda c: c.data.startswith("escrow_"))
def handle_escrow_decision(call):
    if call.from_user.id != ADMIN_ID: return
    
    parts = call.data.split("_")
    action = parts[1]
    tx_id = int(parts[2])
    user_id = int(parts[3])
    
    if action == "ap":
        amount = float(parts[4])
        # Update Balance and TX Status safely
        execute_db("UPDATE users SET balance = balance + ? WHERE user_id=?", (amount, user_id))
        execute_db("UPDATE transactions SET status = 'APPROVED' WHERE tx_id=?", (tx_id,))
        
        bot.edit_message_caption(f"✅ *APPROVED* TXN-{tx_id}\nUser `{user_id}` received `₹{amount}`.", call.message.chat.id, call.message.message_id, parse_mode="Markdown")
        try: 
            bot.send_message(user_id, f"🎉 *DEPOSIT APPROVED!*\nAdmin has added `₹{amount}` to your wallet.", parse_mode="Markdown")
        except: pass # User might have blocked bot
            
    elif action == "rj":
        execute_db("UPDATE transactions SET status = 'REJECTED' WHERE tx_id=?", (tx_id,))
        bot.edit_message_caption(f"❌ *REJECTED* TXN-{tx_id}\nUser `{user_id}` request denied.", call.message.chat.id, call.message.message_id, parse_mode="Markdown")
        try:
            bot.send_message(user_id, f"❌ *DEPOSIT REJECTED*\nYour recent payment screenshot was declined by the Admin.", parse_mode="Markdown")
        except: pass

# =======================================================================================
# 10. SUPPORT TICKET SYSTEM
# =======================================================================================
@bot.message_handler(func=lambda m: m.text == "📞 Support / Tickets")
def handle_support_menu(message):
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("📝 Open New Ticket", callback_data="ticket_new"))
    text = (
        f"🛠️ *SUPPORT DESK*\n\n"
        f"Need help with an order? Open a ticket and the Admin will reply here."
    )
    bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data == "ticket_new")
def handle_new_ticket(call):
    user_states[call.from_user.id] = {"state": "ticket_msg"}
    bot.send_message(call.message.chat.id, "📝 *Type your issue or question below:*\n(Include Order ID if applicable)", parse_mode="Markdown", reply_markup=cancel_keyboard())

@bot.message_handler(func=lambda m: m.from_user.id in user_states and user_states[m.from_user.id].get("state") == "ticket_msg")
def handle_save_ticket(message):
    if message.text == "❌ Cancel Action": return handle_cancel_or_dummy(message)
    user_id = message.from_user.id
    issue = message.text
    
    t_id = execute_db("INSERT INTO tickets (user_id, message) VALUES (?, ?)", (user_id, issue), return_id=True)
    
    # Notify Admin
    admin_kb = InlineKeyboardMarkup().add(InlineKeyboardButton(f"Reply to Ticket {t_id}", callback_data=f"reply_ticket_{t_id}_{user_id}"))
    bot.send_message(ADMIN_ID, f"🚨 *NEW TICKET #{t_id}*\nFrom: `{user_id}`\n\n💬 {issue}", parse_mode="Markdown", reply_markup=admin_kb)
    
    bot.send_message(message.chat.id, f"✅ *Ticket #{t_id} Submitted!*\nThe Admin will reply as soon as possible.", parse_mode="Markdown", reply_markup=generate_main_keyboard(user_id))
    user_states.pop(user_id, None)

@bot.callback_query_handler(func=lambda c: c.data.startswith("reply_ticket_"))
def handle_admin_ticket_reply(call):
    if call.from_user.id != ADMIN_ID: return
    parts = call.data.split("_")
    t_id, u_id = parts[2], parts[3]
    
    user_states[ADMIN_ID] = {"state": "admin_reply", "t_id": t_id, "u_id": int(u_id)}
    bot.send_message(ADMIN_ID, f"✍️ *Type your reply for Ticket #{t_id}:*", parse_mode="Markdown", reply_markup=cancel_keyboard())

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and user_states.get(ADMIN_ID, {}).get("state") == "admin_reply")
def handle_send_admin_reply(message):
    if message.text == "❌ Cancel Action": return handle_cancel_or_dummy(message)
    t_id = user_states[ADMIN_ID]["t_id"]
    u_id = user_states[ADMIN_ID]["u_id"]
    reply_text = message.text
    
    execute_db("UPDATE tickets SET status = 'CLOSED' WHERE ticket_id=?", (t_id,))
    
    try:
        bot.send_message(u_id, f"📩 *SUPPORT REPLY (Ticket #{t_id})*\n\n{reply_text}", parse_mode="Markdown")
        bot.send_message(ADMIN_ID, f"✅ Reply sent to {u_id}. Ticket Closed.", reply_markup=generate_main_keyboard(ADMIN_ID))
    except:
        bot.send_message(ADMIN_ID, "❌ Failed to send. User may have blocked bot.", reply_markup=generate_main_keyboard(ADMIN_ID))
        
    user_states.pop(ADMIN_ID, None)

# =======================================================================================
# 11. ADMIN ZONE - DYNAMIC SERVICE MANAGER
# =======================================================================================
@bot.message_handler(func=lambda m: m.text == "⚙️ Manage Services" and m.from_user.id == ADMIN_ID)
def handle_manage_services(message):
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("➕ Add New Service (By ID)", callback_data="svc_add"))
    kb.add(InlineKeyboardButton("❌ Remove Active Service", callback_data="svc_remove"))
    bot.send_message(message.chat.id, "⚙️ *SERVICE CONTROL CENTER*\nManage what your users can buy.", parse_mode="Markdown", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data == "svc_add")
def handle_svc_add_start(call):
    user_states[ADMIN_ID] = {"state": "wait_api_id"}
    bot.send_message(ADMIN_ID, "🔢 *Send the Service ID from your SMM Provider:*", parse_mode="Markdown", reply_markup=cancel_keyboard())

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and user_states.get(ADMIN_ID, {}).get("state") == "wait_api_id")
def handle_svc_add_process(message):
    if message.text == "❌ Cancel Action": return handle_cancel_or_dummy(message)
    s_id = message.text.strip()
    
    bot.send_chat_action(ADMIN_ID, 'typing')
    api_res = call_smm_api('services')
    
    if not api_res:
        return bot.send_message(ADMIN_ID, "❌ Failed to connect to SMM Provider API.")
        
    try:
        # Search for the ID in the provider's list
        target_service = next(i for i in api_res if str(i['service']) == s_id)
        name = target_service['name']
        rate = float(target_service['rate'])
        
        # Add to local DB
        execute_db("INSERT OR REPLACE INTO managed_services (service_id, name, rate, margin) VALUES (?, ?, ?, ?)",
                   (int(s_id), name, rate, DEFAULT_MARGIN))
                   
        success_msg = (
            f"✅ *SERVICE ADDED SAFELY*\n\n"
            f"🏷️ *Name:* {name}\n"
            f"🆔 *ID:* `{s_id}`\n"
            f"🏭 *Provider Cost:* `₹{rate:.2f}`\n"
            f"💰 *Your Selling Price:* `₹{rate * DEFAULT_MARGIN:.2f}`"
        )
        bot.send_message(ADMIN_ID, success_msg, parse_mode="Markdown", reply_markup=generate_main_keyboard(ADMIN_ID))
    except StopIteration:
        bot.send_message(ADMIN_ID, f"❌ ID `{s_id}` not found on provider's list.", parse_mode="Markdown", reply_markup=generate_main_keyboard(ADMIN_ID))
        
    user_states.pop(ADMIN_ID, None)

@bot.callback_query_handler(func=lambda c: c.data == "svc_remove")
def handle_svc_remove_list(call):
    services = execute_db("SELECT service_id, name FROM managed_services", fetch_all=True)
    if not services:
        return bot.answer_callback_query(call.id, "No active services to remove.")
        
    kb = InlineKeyboardMarkup(row_width=1)
    for s in services:
        kb.add(InlineKeyboardButton(f"🗑️ Delete: {s[1][:25]}...", callback_data=f"del_svc_{s[0]}"))
        
    bot.send_message(call.message.chat.id, "❌ *Click a service below to remove it from the bot:*", parse_mode="Markdown", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("del_svc_"))
def handle_svc_delete_action(call):
    s_id = call.data.split("_")[2]
    execute_db("DELETE FROM managed_services WHERE service_id=?", (s_id,))
    
    bot.answer_callback_query(call.id, f"Service {s_id} Removed successfully.", show_alert=True)
    try: bot.delete_message(call.message.chat.id, call.message.message_id)
    except: pass

# =======================================================================================
# 12. ADMIN ZONE - GOD MODE DASHBOARD
# =======================================================================================
@bot.message_handler(func=lambda m: m.text == "💰 God Mode Funds" and m.from_user.id == ADMIN_ID)
def handle_god_funds(message):
    user_states[ADMIN_ID] = {"state": "god_id"}
    bot.send_message(ADMIN_ID, "👑 *GOD MODE: FUNDING*\nSend the Target *User ID*:", parse_mode="Markdown", reply_markup=cancel_keyboard())

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and user_states.get(ADMIN_ID, {}).get("state") == "god_id")
def handle_god_funds_id(message):
    if message.text == "❌ Cancel Action": return handle_cancel_or_dummy(message)
    user_states[ADMIN_ID].update({"state": "god_amt", "uid": int(message.text)})
    bot.send_message(ADMIN_ID, f"ID `{message.text}` saved.\n\n💸 *Send Amount:*\n(Send `100` to Add, or `-50` to Deduct)", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and user_states.get(ADMIN_ID, {}).get("state") == "god_amt")
def handle_god_funds_action(message):
    if message.text == "❌ Cancel Action": return handle_cancel_or_dummy(message)
    try:
        amt = float(message.text)
        uid = user_states[ADMIN_ID]["uid"]
        execute_db("UPDATE users SET balance = balance + ? WHERE user_id=?", (amt, uid))
        
        # User notification
        if amt > 0: 
            try: bot.send_message(uid, f"🎉 *WALLET UPDATE*\nAdmin added `₹{amt}` to your wallet!", parse_mode="Markdown")
            except: pass
        else: 
            try: bot.send_message(uid, f"⚠️ *WALLET UPDATE*\nAdmin deducted `₹{abs(amt)}` from your wallet.", parse_mode="Markdown")
            except: pass
            
        bot.send_message(ADMIN_ID, f"✅ God Mode Success. Adjusted `{uid}` by `₹{amt}`.", parse_mode="Markdown", reply_markup=generate_main_keyboard(ADMIN_ID))
    except: 
        bot.send_message(ADMIN_ID, "Error. Ensure ID and amounts are valid numbers.", reply_markup=generate_main_keyboard(ADMIN_ID))
    user_states.pop(ADMIN_ID, None)

@bot.message_handler(func=lambda m: m.text == "📩 Direct Msg" and m.from_user.id == ADMIN_ID)
def handle_admin_dm(message):
    user_states[ADMIN_ID] = {"state": "dm_id"}
    bot.send_message(ADMIN_ID, "📩 *DIRECT MESSAGE*\nSend the Target *User ID*:", parse_mode="Markdown", reply_markup=cancel_keyboard())

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and user_states.get(ADMIN_ID, {}).get("state") == "dm_id")
def handle_admin_dm_id(message):
    if message.text == "❌ Cancel Action": return handle_cancel_or_dummy(message)
    user_states[ADMIN_ID].update({"state": "dm_msg", "uid": int(message.text)})
    bot.send_message(ADMIN_ID, f"ID `{message.text}` saved. \n\n✍️ *Type your message:*", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and user_states.get(ADMIN_ID, {}).get("state") == "dm_msg")
def handle_admin_dm_send(message):
    if message.text == "❌ Cancel Action": return handle_cancel_or_dummy(message)
    uid = user_states[ADMIN_ID]["uid"]
    try:
        bot.send_message(uid, f"📩 *Message from Admin:*\n\n{message.text}", parse_mode="Markdown")
        bot.send_message(ADMIN_ID, "✅ Message Delivered.", reply_markup=generate_main_keyboard(ADMIN_ID))
    except: 
        bot.send_message(ADMIN_ID, "❌ Delivery failed. User blocked the bot.", reply_markup=generate_main_keyboard(ADMIN_ID))
    user_states.pop(ADMIN_ID, None)

@bot.message_handler(func=lambda m: m.text == "📢 Broadcast" and m.from_user.id == ADMIN_ID)
def handle_admin_broadcast(message):
    user_states[ADMIN_ID] = {"state": "broad_msg"}
    bot.send_message(ADMIN_ID, "📢 *BROADCAST SYSTEM*\nType the message you want to send to ALL users:", parse_mode="Markdown", reply_markup=cancel_keyboard())

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and user_states.get(ADMIN_ID, {}).get("state") == "broad_msg")
def handle_admin_broadcast_send(message):
    if message.text == "❌ Cancel Action": return handle_cancel_or_dummy(message)
    msg_text = message.text
    
    bot.send_message(ADMIN_ID, "⏳ Broadcasting... This may take a moment.", reply_markup=generate_main_keyboard(ADMIN_ID))
    
    users = execute_db("SELECT user_id FROM users", fetch_all=True)
    sent_count = 0
    
    # Broadcast with an action button to drive sales
    kb = InlineKeyboardMarkup().add(InlineKeyboardButton("🛒 Go to Services", callback_data="dummy_btn")) 
    # (Note: Inline button callback would need a handler if it does something specific, 
    # but here it's just a visual CTA. We can leave it simple).
    
    for u in users:
        try:
            bot.send_message(u[0], f"📢 *OFFICIAL ANNOUNCEMENT*\n\n{msg_text}", parse_mode="Markdown")
            sent_count += 1
            time.sleep(0.05) # Prevent Telegram Rate Limit Ban
        except Exception:
            pass # Ignore users who blocked the bot
            
    bot.send_message(ADMIN_ID, f"✅ Broadcast finished! Delivered to {sent_count} users.")
    user_states.pop(ADMIN_ID, None)

# =======================================================================================
# 13. ADMIN COMMANDS (For quick CLI-style actions)
# =======================================================================================
@bot.message_handler(commands=['stats'])
def handle_stats(message):
    """Shows global panel statistics."""
    if message.from_user.id != ADMIN_ID: return
    
    u_stats = execute_db("SELECT COUNT(*), SUM(balance), SUM(total_spent) FROM users", fetch=True)
    o_stats = execute_db("SELECT COUNT(*), SUM(cost) FROM orders", fetch=True)
    
    text = (
        f"📊 *GLOBAL PANEL STATS*\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"👥 Total Users: `{u_stats[0]}`\n"
        f"💰 Total User Balances: `₹{u_stats[1] or 0:.2f}`\n"
        f"📈 Total Revenue (Spent): `₹{u_stats[2] or 0:.2f}`\n"
        f"📦 Total Orders Placed: `{o_stats[0]}`\n"
        f"━━━━━━━━━━━━━━━━"
    )
    bot.send_message(ADMIN_ID, text, parse_mode="Markdown")

@bot.message_handler(commands=['makepromo'])
def handle_make_promo(message):
    """Creates a new promo code: /makepromo [Amount] [Uses]"""
    if message.from_user.id != ADMIN_ID: return
    try:
        args = message.text.split()
        amount = float(args[1])
        uses = int(args[2])
        
        # Generate random 8 char code
        code = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(8))
        
        execute_db("INSERT INTO promo_codes (code, amount, max_uses) VALUES (?, ?, ?)", (code, amount, uses))
        bot.send_message(ADMIN_ID, f"✅ *PROMO CREATED*\nCode: `{code}`\nValue: `₹{amount}`\nUses: `{uses}`", parse_mode="Markdown")
    except Exception:
        bot.send_message(ADMIN_ID, "❌ Usage: `/makepromo [amount] [max_uses]`", parse_mode="Markdown")

# =======================================================================================
# 14. EXECUTION RUNNER
# =======================================================================================
def run_telegram_bot():
    """Runs the bot polling with extreme error handling for Render."""
    init_database()
    logger.info("Bot Engine Started. Beginning Polling...")
    while True:
        try:
            # timeout=20 prevents socket hang, long_polling_timeout keeps the connection alive
            bot.infinity_polling(timeout=20, long_polling_timeout=15)
        except Exception as e:
            logger.error(f"Polling crashed: {e}. Restarting in 5 seconds...")
            time.sleep(5)

if __name__ == '__main__':
    # 1. Start the Telegram Bot in a background thread
    bot_thread = threading.Thread(target=run_telegram_bot, daemon=True)
    bot_thread.start()
    
    # 2. Start the Flask Web Server on the main thread (Satisfies Render Port Binding)
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
