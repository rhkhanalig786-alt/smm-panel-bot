"""
=========================================================================================
🔥 SMM PANEL BOT - ENTERPRISE V18 ULTIMATE 🔥
(Upgraded Smart Sync, Cheap Services Hub, Auto-Refunds, @csplogs Feed, Guided Ordering)
=========================================================================================
"""

import telebot, requests, sqlite3, logging, time, os, urllib.parse, threading, html, re
from io import BytesIO
from flask import Flask
from telebot.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton

# =======================================================================================
# 1. CONFIGURATION
# =======================================================================================
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

# ⚠️ REPLACE THESE WITH YOUR KEYS OR SET IN RENDER ENVIRONMENT VARIABLES!
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8228287584:AAHliU2PLRHZ-zzOoGcIqIpDhemZUTV2x0U')

bot = telebot.TeleBot(BOT_TOKEN, threaded=True, num_threads=10)

PROVIDERS = {
    "provider_primary": {
        "url": os.environ.get("API_URL_1", "https://iggrowbot.com/api/v2"),
        "key": os.environ.get("API_KEY_1", "8372d39d2613442c920270b8ce2e1a27")
    }
}

FREE_VIEWS_SERVICE_ID = int(os.environ.get('FREE_VIEWS_SERVICE_ID', 1753))
FREE_VIEWS_PROVIDER = "provider_primary"

ADMIN_ID = int(os.environ.get('ADMIN_ID', 6034840006))
UPI_ID = os.environ.get('UPI_ID', "rahikhann@fam")
SUPPORT_USERNAME = os.environ.get('SUPPORT_USERNAME', "@itzdevrahi")
PROOF_CHANNEL = os.environ.get('PROOF_CHANNEL', "@csplogs")
MIN_DEPOSIT = 15.0

user_states = {}
db_lock = threading.Lock()

app = Flask(__name__)
@app.route('/')
def home():
    return "🔥 SMM V18 ENTERPRISE ONLINE (SMART SYNC + AUTO REFUND + CSPLOGS) 🔥"

# =======================================================================================
# 2. DATABASE ENGINE
# =======================================================================================
def execute_db(query, params=(), fetch=False, fetch_all=False, return_id=False, many=False):
    with db_lock:
        try:
            with sqlite3.connect('panel_v17.db', check_same_thread=False, timeout=20) as conn:
                c = conn.cursor()
                if many:
                    c.executemany(query, params)
                else:
                    c.execute(query, params)
                if fetch: return c.fetchone()
                if fetch_all: return c.fetchall()
                if return_id:
                    conn.commit()
                    return c.lastrowid
                conn.commit()
                return True
        except Exception as e:
            logging.error(f"DB Error [{query}]: {e}")
            return False

def init_database():
    tables = [
        """CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT, balance REAL DEFAULT 0.0,
            total_spent REAL DEFAULT 0.0, free_views_credits INTEGER DEFAULT 0, referrer_id INTEGER,
            is_banned INTEGER DEFAULT 0, referral_code TEXT UNIQUE, joined_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS orders (
            db_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, provider TEXT, api_order_id TEXT,
            service_id INTEGER, quantity INTEGER, cost REAL, profit REAL DEFAULT 0.0, status TEXT DEFAULT 'pending',
            auto_refill INTEGER DEFAULT 1, last_refill_check TIMESTAMP DEFAULT CURRENT_TIMESTAMP, placed_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS managed_services (
            service_id INTEGER PRIMARY KEY, platform TEXT, category TEXT, name TEXT, provider TEXT DEFAULT 'provider_primary',
            provider_service_id INTEGER, rate REAL, min_qty INTEGER DEFAULT 10, max_qty INTEGER DEFAULT 100000,
            avg_time TEXT DEFAULT 'Instant - 1 Hour', margin REAL DEFAULT 1.50, disabled INTEGER DEFAULT 0,
            is_cheap INTEGER DEFAULT 0
        )""",
        "CREATE TABLE IF NOT EXISTS transactions (tx_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount REAL, status TEXT, date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
        "CREATE TABLE IF NOT EXISTS tickets (ticket_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, message TEXT, status TEXT DEFAULT 'OPEN', reply TEXT)",
        "CREATE TABLE IF NOT EXISTS referrals (referrer_id INTEGER, referred_id INTEGER, reward_claimed INTEGER DEFAULT 1, PRIMARY KEY(referrer_id, referred_id))",
        "CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)"
    ]
    for table in tables: execute_db(table)
    if not execute_db("SELECT value FROM settings WHERE key='global_margin'", fetch=True):
        execute_db("INSERT INTO settings (key, value) VALUES ('global_margin', '1.50')")
    
    # Safely retrofit columns if upgrading from an older DB version
    try: execute_db("ALTER TABLE orders ADD COLUMN profit REAL DEFAULT 0.0")
    except: pass
    try: execute_db("ALTER TABLE managed_services ADD COLUMN is_cheap INTEGER DEFAULT 0")
    except: pass

def is_banned(uid):
    u = execute_db("SELECT is_banned FROM users WHERE user_id=?", (uid,), fetch=True)
    return u and u[0] == 1

# =======================================================================================
# 3. UTILITIES, SMART DETECTOR, HEALTH & PROOF CHANNEL ENGINE
# =======================================================================================
def call_provider_api(provider_name, action, extra=None):
    prov = PROVIDERS.get(provider_name, PROVIDERS["provider_primary"])
    payload = {'key': prov['key'], 'action': action}
    if extra: payload.update(extra)
    try:
        res = requests.post(prov['url'], data=payload, timeout=20)
        return res.json(), provider_name
    except Exception as e:
        logging.error(f"Provider API Error: {e}")
        return None, provider_name

def detect_platform(category_str, name_str):
    """
    Strictly checks Category first using word boundaries so Telegram ('tg') 
    and Instagram ('ig') services never mix up!
    """
    cat = (category_str or "").lower()
    name = (name_str or "").lower()

    patterns = [
        ("📸 Instagram", r'\b(instagram|insta|ig|reels|igtv)\b'),
        ("✈️ Telegram", r'\b(telegram|tg|tele)\b'),
        ("🔴 YouTube", r'\b(youtube|yt|shorts)\b'),
        ("📘 Facebook", r'\b(facebook|fb)\b'),
        ("🎵 TikTok", r'\b(tiktok|tik tok|tt)\b'),
        ("🐦 Twitter / X", r'\b(twitter|tweet|x\.com)\b'),
        ("🟢 Spotify", r'\b(spotify)\b'),
        ("💬 WhatsApp", r'\b(whatsapp|wa)\b'),
    ]

    # Step 1: Check category name strictly first (most accurate)
    for platform, pat in patterns:
        if re.search(pat, cat):
            return platform

    # Step 2: Check service name if category was generic
    for platform, pat in patterns:
        if re.search(pat, name):
            return platform

    return "⚡ General Boost"

def clean_service_name(name, max_len=24):
    """
    Cleans long messy provider strings so the price on the right of the inline button
    NEVER gets cut off on mobile screens!
    """
    if not name: return "Service"
    # Remove provider brackets/junk to save space
    cleaned = re.sub(r'\[.*?\]|\(.*?\)', '', name)
    for word in ['instagram', 'telegram', 'youtube', 'facebook', 'tiktok', 'twitter', 'services', 'service', '-']:
        cleaned = re.sub(rf'\b{word}\b', '', cleaned, flags=re.IGNORECASE)
    cleaned = " ".join(cleaned.split())
    if not cleaned:
        cleaned = name.strip()
    if len(cleaned) > max_len:
        return cleaned[:max_len-2].strip() + ".."
    return cleaned

def get_service_health_and_speed(name_str, avg_time_str):
    """
    Safe, zero-crash Live Order Speedometer & Service Health Indicator.
    """
    try:
        n = f"{name_str} {avg_time_str}".lower()
        if any(k in n for k in ['instant', 'fast', '10-60', 'min', 'superfast']):
            return "🟢", "⚡ [█████████░] 92% (Instant/Fast)", "🟢 Healthy (Optimal)"
        elif any(k in n for k in ['refill', 'hq', 'real', 'non drop', 'guarantee']):
            return "🟢", "🚀 [████████░░] 80% (High Stability)", "🟢 Healthy (Stable)"
        else:
            return "🟡", "⏳ [██████░░░░] 65% (Normal Speed)", "🟡 Moderate Load"
    except:
        return "🟢", "⚡ [████████░░] 80% (Active)", "🟢 Healthy"

def validate_order_link(platform, link):
    """
    Smart Auto-Link Validator & Preview helper.
    Ensures user doesn't paste a Telegram link for an Instagram service or forget http/https.
    """
    link = link.strip()
    l_low = link.lower()

    # Allow @username only for Telegram if they type it, otherwise require a link/domain
    if not (l_low.startswith("http://") or l_low.startswith("https://") or "." in l_low or l_low.startswith("@")):
        return False, (
            "❌ <b>Invalid Link Format!</b>\n\n"
            "🧭 <b>How to fix:</b> Please copy the full public link starting with <code>https://</code> "
            "(for example: <code>https://www.instagram.com/p/xxxx/</code>) and send it again."
        )

    mismatch = None
    if "Instagram" in platform and any(x in l_low for x in ["t.me/", "youtube.com", "youtu.be", "facebook.com", "tiktok.com"]):
        mismatch = "Instagram (instagram.com)"
    elif "Telegram" in platform and any(x in l_low for x in ["instagram.com", "youtube.com", "youtu.be", "facebook.com", "tiktok.com"]):
        mismatch = "Telegram (t.me)"
    elif "YouTube" in platform and any(x in l_low for x in ["instagram.com", "t.me/", "facebook.com", "tiktok.com"]):
        mismatch = "YouTube (youtube.com / youtu.be)"
    elif "Facebook" in platform and any(x in l_low for x in ["instagram.com", "t.me/", "youtube.com", "tiktok.com"]):
        mismatch = "Facebook (facebook.com)"
    elif "TikTok" in platform and any(x in l_low for x in ["instagram.com", "t.me/", "youtube.com", "facebook.com"]):
        mismatch = "TikTok (tiktok.com)"

    if mismatch:
        return False, (
            f"⚠️ <b>WRONG PLATFORM LINK DETECTED!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"You selected a <b>{platform}</b> service, but the link you pasted belongs to another app!\n\n"
            f"✅ <b>Required Link Type:</b> <code>{mismatch}</code>\n"
            f"🔗 <b>Please send the correct {platform} link below (or tap 🔙 Step Back):</b>"
        )

    return True, link

def mask_user(uid, first_name):
    s_uid = str(uid)
    masked_id = s_uid[:4] + "****" if len(s_uid) > 4 else s_uid + "**"
    clean_fn = html.escape((first_name or "User")[:3]) + "***"
    return f"{clean_fn} (<code>{masked_id}</code>)"

def send_proof_log(text):
    """
    Safely sends live order/deposit activity to @csplogs without ever crashing the bot.
    """
    if not PROOF_CHANNEL: return
    try:
        bot.send_message(PROOF_CHANNEL, text, parse_mode="HTML", disable_web_page_preview=True)
    except Exception as e:
        logging.warning(f"Could not post to proof channel {PROOF_CHANNEL}: {e}")

# =======================================================================================
# 4. KEYBOARDS
# =======================================================================================
def main_kb(uid):
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add("🛒 Browse Services 🚀", "🎁 Claim Free 1K Views 🌟")
    kb.add("💰 My Profile 👤", "💳 Add Funds 💸")
    kb.add("📦 Order History 📜", "🤝 Referral Program 👥")
    kb.add("📞 Support 🎫")
    if uid == ADMIN_ID:
        kb.add("🧠 Admin: Smart Sync", "👥 Admin: Manage Users")
        kb.add("📈 Admin: Margin", "📢 Admin: Broadcast")
        kb.add("📊 Admin: Stats", "🎫 Admin: Tickets")
        kb.add("💾 Admin: Backup DB", "🔄 Admin: Restore DB")
    return kb

def back_cancel_kb():
    return ReplyKeyboardMarkup(resize_keyboard=True, row_width=2).add("🔙 Step Back", "❌ Cancel to Menu")

# =======================================================================================
# 5. USER FLOW
# =======================================================================================
@bot.message_handler(commands=['start'])
def h_start(m):
    uid = m.from_user.id
    user_states.pop(uid, None)
    u = execute_db("SELECT * FROM users WHERE user_id=?", (uid,), fetch=True)
    if not u:
        referrer_id = None
        args = m.text.split()
        if len(args) > 1 and args[1].startswith('ref_'):
            try:
                if int(args[1].replace('ref_', '')) != uid: referrer_id = int(args[1].replace('ref_', ''))
            except: pass
        execute_db("INSERT INTO users (user_id, username, first_name, referrer_id, referral_code) VALUES (?,?,?,?,?)",
                   (uid, m.from_user.username, m.from_user.first_name, referrer_id, f"REF{uid}"))
        if referrer_id:
            execute_db("INSERT OR IGNORE INTO referrals (referrer_id, referred_id) VALUES (?,?)", (referrer_id, uid))
            execute_db("UPDATE users SET free_views_credits = free_views_credits + 1 WHERE user_id=?", (referrer_id,))
            try: bot.send_message(referrer_id, "🎊 <b>A friend joined!</b>\n🎁 <b>You received +1 Free 1K Views Credit!</b>", parse_mode="HTML")
            except: pass

    if is_banned(uid): return bot.send_message(m.chat.id, "🚫 <b>YOUR ACCOUNT HAS BEEN BANNED.</b>", parse_mode="HTML")

    msg = (
        f"👋 <b>Welcome to Cheap SMM Panel, {html.escape(m.from_user.first_name or 'User')}!</b> 🚀\n\n"
        f"👇 <b>HOW TO GET STARTED:</b>\n"
        f"1️⃣ Tap <b>'💳 Add Funds 💸'</b> to load your wallet\n"
        f"2️⃣ Tap <b>'🛒 Browse Services 🚀'</b> (Check out <b>🔥 Cheap Services</b>!)\n"
        f"3️⃣ Paste your public link and watch your account grow!\n\n"
        f"📢 <b>Live Order Proofs:</b> {PROOF_CHANNEL}"
    )
    bot.send_message(m.chat.id, msg, parse_mode="HTML", reply_markup=main_kb(uid))

@bot.message_handler(func=lambda m: m.text == "❌ Cancel to Menu")
def h_cancel(m):
    user_states.pop(m.from_user.id, None)
    bot.send_message(m.chat.id, "🚫 <b>Action Cancelled!</b>\n🏠 <i>Returned to the main menu.</i>", parse_mode="HTML", reply_markup=main_kb(m.from_user.id))

@bot.message_handler(func=lambda m: m.text == "🔙 Step Back")
def h_step_back(m):
    uid = m.from_user.id
    current_state = user_states.get(uid, {}).get("state")

    if current_state == "get_qty":
        user_states[uid]["state"] = "get_link"
        bot.send_message(
            m.chat.id,
            "🔙 <b>Went 1 step back!</b>\n\n"
            "🔗 <b>STEP 1 of 2: Send Your Target Link</b>\n"
            "<i>Paste the public post/profile URL below:</i>",
            parse_mode="HTML",
            reply_markup=back_cancel_kb()
        )
    elif current_state == "get_link":
        user_states.pop(uid, None)
        h_browse(m)
    elif current_state == "fund_ss":
        user_states[uid]["state"] = "fund_amt"
        bot.send_message(m.chat.id, "🔙 <b>Went 1 step back!</b>\n💸 <b>Enter deposit amount (₹):</b>", parse_mode="HTML", reply_markup=back_cancel_kb())
    else:
        user_states.pop(uid, None)
        bot.send_message(m.chat.id, "🏠 <b>Returned to Main Menu.</b>", parse_mode="HTML", reply_markup=main_kb(uid))

@bot.message_handler(func=lambda m: m.text == "💰 My Profile 👤")
def h_profile(m):
    u = execute_db("SELECT balance, total_spent, free_views_credits FROM users WHERE user_id=?", (m.from_user.id,), fetch=True)
    if not u: return
    ref_count = execute_db("SELECT COUNT(*) FROM referrals WHERE referrer_id=?", (m.from_user.id,), fetch=True)[0]
    msg = (
        f"👤 <b>YOUR ACCOUNT PROFILE</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 <b>User ID:</b> <code>{m.from_user.id}</code>\n"
        f"💳 <b>Wallet Balance:</b> <code>₹{u[0]:.2f}</code>\n"
        f"📈 <b>Total Spent:</b> <code>₹{u[1]:.2f}</code>\n"
        f"🎁 <b>Free Views Credits:</b> <code>{u[2]}</code>\n"
        f"👥 <b>Total Referrals:</b> <code>{ref_count}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"📢 <b>Live Proofs:</b> {PROOF_CHANNEL}"
    )
    bot.send_message(m.chat.id, msg, parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text == "📦 Order History 📜")
def h_order_history(m):
    orders = execute_db("SELECT api_order_id, quantity, cost, status, service_id FROM orders WHERE user_id=? ORDER BY placed_time DESC LIMIT 5", (m.from_user.id,), fetch_all=True)
    if not orders: return bot.send_message(m.chat.id, "📦 <b>You haven't placed any orders yet!</b>\nTap <b>'🛒 Browse Services 🚀'</b> to start.", parse_mode="HTML")
    msg = "📦 <b>YOUR LAST 5 ORDERS:</b>\n━━━━━━━━━━━━━━━━━━━\n"
    for o in orders:
        st_low = (o[3] or "").lower()
        if st_low == "completed": badge = "✅ Completed"
        elif st_low in ["canceled", "cancelled", "partial", "refunded"]: badge = "🔄 Refunded to Wallet"
        else: badge = f"⚡ {o[3].capitalize()}"
        msg += f"🧾 <b>Order ID:</b> <code>{o[0]}</code>\n🔢 <b>Qty:</b> <code>{o[1]:,}</code> | 💰 <b>Cost:</b> <code>₹{o[2]:.2f}</code>\n📊 <b>Status:</b> {badge}\n───────────────────\n"
    bot.send_message(m.chat.id, msg, parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text == "🤝 Referral Program 👥")
def h_referral(m):
    u = execute_db("SELECT free_views_credits FROM users WHERE user_id=?", (m.from_user.id,), fetch=True)
    if not u: return
    ref_count = execute_db("SELECT COUNT(*) FROM referrals WHERE referrer_id=?", (m.from_user.id,), fetch=True)[0]
    link = f"https://t.me/{bot.get_me().username}?start=ref_{m.from_user.id}"
    msg = (
        f"🤝 <b>REFERRAL REWARDS PROGRAM</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"🔗 <b>Your Invite Link:</b>\n<code>{link}</code>\n\n"
        f"👥 <b>Friends Joined:</b> <code>{ref_count}</code>\n"
        f"🎁 <b>Free View Credits:</b> <code>{u[0]}</code>\n\n"
        f"<i>Share your link! You get 1,000 Free Views for every friend who starts the bot!</i>"
    )
    bot.send_message(m.chat.id, msg, parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text == "🎁 Claim Free 1K Views 🌟")
def h_claim_free(m):
    u = execute_db("SELECT free_views_credits FROM users WHERE user_id=?", (m.from_user.id,), fetch=True)
    credits = u[0] if u else 0
    if credits <= 0:
        return bot.send_message(m.chat.id, "❌ <b>You have 0 Free Credits!</b>\nTap <b>'🤝 Referral Program 👥'</b> to invite friends and earn free views.", parse_mode="HTML")
    user_states[m.from_user.id] = {"state": "claim_free_link"}
    bot.send_message(
        m.chat.id,
        f"🎁 <b>You have {credits} Free Credit(s)!</b>\n\n"
        f"🧭 <b>GUIDE:</b> Make sure your account is <b>Public</b>.\n"
        f"🔗 <b>Paste your Reel / Video link below for 1,000 Free Views:</b>",
        parse_mode="HTML",
        reply_markup=back_cancel_kb()
    )

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get("state") == "claim_free_link")
def h_process_free_claim(m):
    uid = m.from_user.id
    u = execute_db("SELECT free_views_credits FROM users WHERE user_id=?", (uid,), fetch=True)
    if not u or u[0] <= 0: return
    link = m.text.strip()
    if not (link.startswith("http://") or link.startswith("https://")):
        return bot.send_message(m.chat.id, "❌ <b>Invalid Link!</b> Please send a valid URL starting with <code>https://</code>", parse_mode="HTML", reply_markup=back_cancel_kb())

    bot.send_message(m.chat.id, "⏳ <i>Dispatching your 1,000 Free Views...</i>", parse_mode="HTML")
    api_res, prov_used = call_provider_api(FREE_VIEWS_PROVIDER, 'add', {'service': FREE_VIEWS_SERVICE_ID, 'link': link, 'quantity': 1000})
    if api_res and 'order' in api_res:
        execute_db("UPDATE users SET free_views_credits = free_views_credits - 1 WHERE user_id=?", (uid,))
        execute_db("INSERT INTO orders (user_id, provider, api_order_id, service_id, quantity, cost, profit, auto_refill) VALUES (?,?,?,?,?,?,?,0)", 
                   (uid, prov_used, api_res['order'], FREE_VIEWS_SERVICE_ID, 1000, 0.0, 0.0))
        bot.send_message(m.chat.id, f"✅ <b>SUCCESS! 1,000 FREE VIEWS ORDERED!</b>\n🧾 <b>Order ID:</b> <code>{api_res['order']}</code>", parse_mode="HTML", reply_markup=main_kb(uid))
        send_proof_log(
            f"🎁 <b>FREE 1,000 VIEWS CLAIMED!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"👤 <b>User:</b> {mask_user(uid, m.from_user.first_name)}\n"
            f"🧾 <b>Order ID:</b> <code>#{api_res['order']}</code>\n"
            f"💰 <b>Cost:</b> <code>₹0.00 (Referral Reward)</code>\n"
            f"🤖 <b>Bot:</b> @{bot.get_me().username}"
        )
    else:
        bot.send_message(m.chat.id, "❌ <b>Failed to place free order!</b> Please check your link and try again.", parse_mode="HTML", reply_markup=main_kb(uid))
    user_states.pop(uid, None)

# =======================================================================================
# 6. SUPPORT & TICKETS (NO GEMINI BLOAT)
# =======================================================================================
@bot.message_handler(func=lambda m: m.text == "📞 Support 🎫")
def h_support(m):
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("💬 Direct Chat with Admin", url=f"https://t.me/{SUPPORT_USERNAME.replace('@','')}"),
        InlineKeyboardButton("🎫 Open Support Ticket", callback_data="make_ticket")
    )
    bot.send_message(
        m.chat.id,
        "📞 <b>CUSTOMER SUPPORT DESK</b>\n━━━━━━━━━━━━━━━━━━━\n"
        "Have an issue with an order or payment? Contact us directly or open a ticket below:",
        parse_mode="HTML",
        reply_markup=kb
    )

@bot.callback_query_handler(func=lambda c: c.data == "make_ticket")
def h_ticket_init(c):
    bot.answer_callback_query(c.id)
    user_states[c.from_user.id] = {"state": "waiting_ticket_text"}
    bot.send_message(
        c.message.chat.id,
        "📝 <b>Describe your issue below (include Order ID or TXN ID if applicable):</b>",
        parse_mode="HTML",
        reply_markup=back_cancel_kb()
    )

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get("state") == "waiting_ticket_text")
def h_ticket_save(m):
    uid = m.from_user.id
    tid = execute_db("INSERT INTO tickets (user_id, message) VALUES (?,?)", (uid, m.text), return_id=True)
    bot.send_message(m.chat.id, f"✅ <b>Ticket #{tid} Submitted!</b>\nOur admin team will review it shortly.", parse_mode="HTML", reply_markup=main_kb(uid))
    try:
        bot.send_message(ADMIN_ID, f"🚨 <b>NEW SUPPORT TICKET #{tid}</b>\nFrom: <code>{uid}</code> (@{m.from_user.username})\n💬 {html.escape(m.text)}", parse_mode="HTML")
    except: pass
    user_states.pop(uid, None)

# =======================================================================================
# 7. ADD FUNDS FLOW (WITH SCREENSHOT & DOUBLE-APPROVAL PROTECTION)
# =======================================================================================
@bot.message_handler(func=lambda m: m.text == "💳 Add Funds 💸")
def h_add_funds(m):
    if is_banned(m.from_user.id): return bot.send_message(m.chat.id, "🚫 You are banned.", parse_mode="HTML")
    user_states[m.from_user.id] = {"state": "fund_amt"}
    bot.send_message(
        m.chat.id,
        f"💸 <b>STEP 1 of 2: Enter Deposit Amount (₹)</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"🔹 <b>Minimum Deposit:</b> <code>₹{MIN_DEPOSIT:.0f}</code>\n"
        f"🔢 <i>Type the amount in numbers only (e.g., 20, 50, 100):</i>",
        parse_mode="HTML",
        reply_markup=back_cancel_kb()
    )

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get("state") == "fund_amt")
def h_fund_qr(m):
    try:
        amt = float(m.text.strip())
        if amt < MIN_DEPOSIT:
            return bot.send_message(m.chat.id, f"🚫 <b>Minimum deposit is ₹{MIN_DEPOSIT:.0f}!</b> Please enter ₹{MIN_DEPOSIT:.0f} or more:", parse_mode="HTML", reply_markup=back_cancel_kb())
        user_states[m.from_user.id] = {"state": "fund_ss", "amt": amt}
        qr = f"https://api.qrserver.com/v1/create-qr-code/?size=400x400&data={urllib.parse.quote(f'upi://pay?pa={UPI_ID}&am={amt}&cu=INR')}"
        res = requests.get(qr, timeout=10)
        caption = (
            f"💳 <b>STEP 2 of 2: Complete Payment</b>\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"💰 <b>Pay Exactly:</b> <code>₹{amt:.2f}</code>\n"
            f"🏦 <b>UPI ID:</b> <code>{UPI_ID}</code> <i>(Tap to copy)</i>\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"📸 <b>IMPORTANT:</b> After paying via FamPay/PhonePe/GPay, <b>send the payment screenshot right here</b> to add your funds!"
        )
        bot.send_photo(m.chat.id, BytesIO(res.content), caption=caption, parse_mode="HTML", reply_markup=back_cancel_kb())
    except:
        bot.send_message(m.chat.id, "❌ <b>Invalid input!</b> Please enter numbers only (e.g. <code>50</code>).", parse_mode="HTML")

@bot.message_handler(content_types=['photo'])
def h_payment_ss(m):
    uid = m.from_user.id
    if user_states.get(uid, {}).get("state") == "fund_ss":
        amt = user_states[uid]["amt"]
        tx = execute_db("INSERT INTO transactions (user_id, amount, status) VALUES (?, ?, 'PENDING')", (uid, amt), return_id=True)
        kb = InlineKeyboardMarkup(row_width=2).add(
            InlineKeyboardButton("✅ Approve", callback_data=f"ap_{tx}_{uid}_{amt}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"rj_{tx}_{uid}")
        )
        u_info = f"@{m.from_user.username}" if m.from_user.username else html.escape(m.from_user.first_name or "User")
        bot.send_photo(
            ADMIN_ID,
            m.photo[-1].file_id,
            caption=f"🚨 <b>NEW DEPOSIT REQUEST</b>\n👤 <b>User:</b> {u_info} (<code>{uid}</code>)\n💰 <b>Amount:</b> <code>₹{amt:.2f}</code>\n🧾 <b>TXN ID:</b> <code>{tx}</code>",
            parse_mode="HTML",
            reply_markup=kb
        )
        bot.send_message(
            m.chat.id,
            f"✅ <b>Screenshot Received! (TXN #{tx})</b>\n⏳ Waiting for admin approval. Your wallet will be credited shortly!",
            parse_mode="HTML",
            reply_markup=main_kb(uid)
        )
        user_states.pop(uid, None)

@bot.callback_query_handler(func=lambda c: c.data.startswith(("ap_", "rj_")))
def h_admin_approval(c):
    if c.from_user.id != ADMIN_ID: return
    bot.answer_callback_query(c.id)
    p = c.data.split("_")
    action, tx, uid = p[0], int(p[1]), int(p[2])

    # Double-click safety check
    tx_row = execute_db("SELECT status FROM transactions WHERE tx_id=?", (tx,), fetch=True)
    if not tx_row or tx_row[0] != 'PENDING':
        return bot.edit_message_caption(f"⚠️ <b>TXN-{tx} Already Processed ({tx_row[0] if tx_row else 'Done'})</b>", c.message.chat.id, c.message.message_id, parse_mode="HTML")

    if action == "ap":
        amt = float(p[3])
        execute_db("UPDATE users SET balance=balance+? WHERE user_id=?", (amt, uid))
        execute_db("UPDATE transactions SET status='APPROVED' WHERE tx_id=?", (tx,))
        bot.edit_message_caption(f"✅ <b>APPROVED TXN-{tx}</b> | Added ₹{amt:.2f} to {uid}", c.message.chat.id, c.message.message_id, parse_mode="HTML")
        try:
            bot.send_message(uid, f"🎉 <b>PAYMENT APPROVED!</b>\n💰 <code>₹{amt:.2f}</code> has been added to your wallet!", parse_mode="HTML")
        except: pass

        u_row = execute_db("SELECT first_name FROM users WHERE user_id=?", (uid,), fetch=True)
        fname = u_row[0] if u_row else "User"
        send_proof_log(
            f"💳 <b>WALLET DEPOSIT VERIFIED</b> ⚡\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"👤 <b>User:</b> {mask_user(uid, fname)}\n"
            f"💰 <b>Added Funds:</b> <code>₹{amt:.2f}</code>\n"
            f"🏦 <b>Method:</b> <code>UPI QR Instant</code>\n"
            f"✅ <b>Status:</b> <code>Credited to Wallet</code>"
        )
    else:
        execute_db("UPDATE transactions SET status='REJECTED' WHERE tx_id=?", (tx,))
        bot.edit_message_caption(f"❌ <b>REJECTED TXN-{tx}</b>", c.message.chat.id, c.message.message_id, parse_mode="HTML")
        try:
            bot.send_message(uid, "❌ <b>DEPOSIT REJECTED!</b>\nYour payment screenshot could not be verified. Please contact Support if you need help.", parse_mode="HTML")
        except: pass

# =======================================================================================
# 8. ADMIN DASHBOARD & ENHANCED SMART SYNC
# =======================================================================================
@bot.message_handler(func=lambda m: m.text == "📊 Admin: Stats" or m.text == "/stats")
def h_admin_stats(m):
    if m.from_user.id != ADMIN_ID: return
    
    profit_row = execute_db("SELECT SUM(profit) FROM orders WHERE date(placed_time) = date('now') AND status NOT IN ('Canceled', 'Partial', 'Refunded')", fetch=True)
    profit_today = profit_row[0] if profit_row and profit_row[0] else 0.0
    
    active_users = execute_db("SELECT COUNT(*) FROM users WHERE is_banned=0", fetch=True)[0]
    wallet_funds = execute_db("SELECT SUM(balance) FROM users", fetch=True)[0] or 0.0
    orders_today = execute_db("SELECT COUNT(*) FROM orders WHERE date(placed_time) = date('now')", fetch=True)[0]
    cheap_count = execute_db("SELECT COUNT(*) FROM managed_services WHERE is_cheap=1 AND disabled=0", fetch=True)[0]
    
    msg = (
        f"📊 <b>ADMIN ANALYTICS DASHBOARD</b> 📊\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"💵 <b>Net Profit Today:</b> <code>₹{profit_today:.2f}</code>\n"
        f"👥 <b>Total Active Users:</b> <code>{active_users}</code>\n"
        f"💰 <b>Funds Sitting in Wallets:</b> <code>₹{wallet_funds:.2f}</code>\n"
        f"📦 <b>Orders Placed Today:</b> <code>{orders_today}</code>\n"
        f"🔥 <b>Ultra-Cheap Services Active:</b> <code>{cheap_count}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━"
    )
    bot.send_message(ADMIN_ID, msg, parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text == "👥 Admin: Manage Users" and m.from_user.id == ADMIN_ID)
def h_admin_manage_users(m):
    user_states[ADMIN_ID] = {"state": "wait_manage_uid"}
    bot.send_message(ADMIN_ID, "🔍 Enter the <b>User ID</b>:", parse_mode="HTML", reply_markup=back_cancel_kb())

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get("state") == "wait_manage_uid" and m.from_user.id == ADMIN_ID)
def h_admin_manage_uid(m):
    try: target_uid = int(m.text.strip())
    except: return bot.send_message(ADMIN_ID, "❌ User ID must be numbers.", reply_markup=back_cancel_kb())
    user = execute_db("SELECT username, first_name, balance, total_spent, is_banned FROM users WHERE user_id=?", (target_uid,), fetch=True)
    if not user: return bot.send_message(ADMIN_ID, "❌ User not found.")
    
    status = "🔴 BANNED" if user[4] else "🟢 ACTIVE"
    msg = f"👤 <b>USER</b> <code>{target_uid}</code> (@{user[0]})\n💰 <b>Wallet:</b> ₹{user[2]:.2f}\n📈 <b>Spent:</b> ₹{user[3]:.2f}\n🛡️ <b>Status:</b> {status}\n\n👇 <i>Select action:</i>"
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(InlineKeyboardButton("➕ Add Balance", callback_data=f"adm_add_{target_uid}"), InlineKeyboardButton("➖ Deduct Balance", callback_data=f"adm_sub_{target_uid}"))
    if user[4]: kb.add(InlineKeyboardButton("✅ Unban User", callback_data=f"adm_unban_{target_uid}"))
    else: kb.add(InlineKeyboardButton("🚫 Ban User", callback_data=f"adm_ban_{target_uid}"))
    
    user_states.pop(ADMIN_ID, None)
    bot.send_message(ADMIN_ID, msg, parse_mode="HTML", reply_markup=main_kb(ADMIN_ID))
    bot.send_message(ADMIN_ID, "⚙️ <b>Actions:</b>", parse_mode="HTML", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("adm_"))
def h_admin_user_actions(c):
    if c.from_user.id != ADMIN_ID: return
    bot.answer_callback_query(c.id)
    parts = c.data.split("_")
    action, target_uid = parts[1], int(parts[2])
    
    if action == "add":
        user_states[ADMIN_ID] = {"state": "wait_adm_add", "uid": target_uid}
        bot.send_message(ADMIN_ID, f"➕ Enter amount to <b>ADD</b> to User <code>{target_uid}</code>:", parse_mode="HTML", reply_markup=back_cancel_kb())
    elif action == "sub":
        user_states[ADMIN_ID] = {"state": "wait_adm_sub", "uid": target_uid}
        bot.send_message(ADMIN_ID, f"➖ Enter amount to <b>DEDUCT</b> from User <code>{target_uid}</code>:", parse_mode="HTML", reply_markup=back_cancel_kb())
    elif action == "ban":
        execute_db("UPDATE users SET is_banned=1 WHERE user_id=?", (target_uid,))
        bot.edit_message_text(f"🚫 <b>User {target_uid} BANNED.</b>", c.message.chat.id, c.message.message_id, parse_mode="HTML")
    elif action == "unban":
        execute_db("UPDATE users SET is_banned=0 WHERE user_id=?", (target_uid,))
        bot.edit_message_text(f"✅ <b>User {target_uid} UNBANNED.</b>", c.message.chat.id, c.message.message_id, parse_mode="HTML")

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get("state") in ["wait_adm_add", "wait_adm_sub"] and m.from_user.id == ADMIN_ID)
def h_admin_bal_adjust(m):
    state_data = user_states[ADMIN_ID]
    action, target_uid = state_data["state"], state_data["uid"]
    try: amt = float(m.text.strip())
    except: return bot.send_message(ADMIN_ID, "❌ Numbers only.", reply_markup=back_cancel_kb())
    
    if action == "wait_adm_add":
        execute_db("UPDATE users SET balance=balance+? WHERE user_id=?", (amt, target_uid))
        bot.send_message(ADMIN_ID, f"✅ <b>Added ₹{amt:.2f}</b> to <code>{target_uid}</code>.", parse_mode="HTML", reply_markup=main_kb(ADMIN_ID))
        try: bot.send_message(target_uid, f"🎁 <b>₹{amt:.2f}</b> has been added to your wallet balance by Admin!", parse_mode="HTML")
        except: pass
    else:
        user = execute_db("SELECT balance FROM users WHERE user_id=?", (target_uid,), fetch=True)
        new_bal = max(0.0, user[0] - amt)
        execute_db("UPDATE users SET balance=? WHERE user_id=?", (new_bal, target_uid))
        bot.send_message(ADMIN_ID, f"✅ <b>Deducted ₹{amt:.2f}</b> from <code>{target_uid}</code>.", parse_mode="HTML", reply_markup=main_kb(ADMIN_ID))
    user_states.pop(ADMIN_ID, None)

@bot.message_handler(func=lambda m: m.text == "🧠 Admin: Smart Sync" and m.from_user.id == ADMIN_ID)
def h_admin_smart_sync(m):
    bot.send_message(ADMIN_ID, "🧠 <i>Upgraded Smart Sync v2.0 running... Categorizing platforms & building 🔥 Cheap Services hub...</i>", parse_mode="HTML")
    res, _ = call_provider_api("provider_primary", "services")
    if not res or not isinstance(res, list):
        return bot.send_message(ADMIN_ID, "❌ Provider API Failed or returned invalid data.")

    margin_row = execute_db("SELECT value FROM settings WHERE key='global_margin'", fetch=True)
    margin = float(margin_row[0]) if margin_row else 1.50

    categories = {}
    platform_all_candidates = {}

    for s in res:
        try:
            rate = float(s.get('rate', 0))
            if rate <= 0: continue
            cat_name = s.get('category', 'General').strip()
            svc_name = s.get('name', 'Service').strip()
            # Strict category-first platform detection
            platform = detect_platform(cat_name, svc_name)
            s['_platform'] = platform
            s['_rate'] = rate

            if cat_name not in categories: categories[cat_name] = []
            categories[cat_name].append(s)

            if platform not in platform_all_candidates: platform_all_candidates[platform] = []
            platform_all_candidates[platform].append(s)
        except:
            continue

    selected_services = {}

    # 1. Select best services per category for standard browsing
    for cat_name, svcs in categories.items():
        cat_lower = cat_name.lower()
        if any(x in cat_lower for x in ['like', 'view', 'share', 'impression', 'reach']):
            svcs.sort(key=lambda x: x['_rate'])
            best = svcs[:3]
        elif any(x in cat_lower for x in ['follower', 'subscriber', 'member']):
            hq = [x for x in svcs if any(k in x.get('name', '').lower() for k in ['refill', 'guarantee', 'hq', 'non drop', 'real'])]
            if not hq: hq = svcs
            hq.sort(key=lambda x: x['_rate'])
            best = hq[:3]
        else:
            svcs.sort(key=lambda x: x['_rate'])
            best = svcs[:2]

        for s in best:
            sid = int(s['service'])
            selected_services[sid] = (s, 0) # 0 = standard, will upgrade to 1 if ultra cheap

    # 2. Pick the Top 10 ULTRA CHEAPEST services per social media platform for the "🔥 Cheap Services" hub
    cheap_total = 0
    for plat, svcs in platform_all_candidates.items():
        svcs.sort(key=lambda x: x['_rate'])
        cheapest_for_plat = svcs[:10]
        for s in cheapest_for_plat:
            sid = int(s['service'])
            selected_services[sid] = (s, 1) # Mark is_cheap = 1!
            cheap_total += 1

    # 3. Batch insert everything cleanly
    rows_to_insert = []
    for sid, (s, is_cheap_flag) in selected_services.items():
        try:
            platform = s['_platform']
            cat_name = s.get('category', 'General').strip()
            name = s.get('name', 'Service').strip()
            rate = s['_rate']
            min_q = int(s.get('min', 10))
            max_q = int(s.get('max', 100000))
            avg = "10-30 Mins" if any(w in name.lower() for w in ["instant", "fast"]) else "1-6 Hours"
            rows_to_insert.append((sid, platform, cat_name, name, 'provider_primary', sid, rate, min_q, max_q, avg, margin, 0, is_cheap_flag))
        except:
            continue

    execute_db("DELETE FROM managed_services")
    execute_db(
        """INSERT OR REPLACE INTO managed_services 
        (service_id, platform, category, name, provider, provider_service_id, rate, min_qty, max_qty, avg_time, margin, disabled, is_cheap) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        rows_to_insert,
        many=True
    )

    bot.send_message(
        ADMIN_ID,
        f"✅ <b>Smart Sync v2.0 Complete!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"📦 <b>Total Curated Services:</b> <code>{len(rows_to_insert)}</code>\n"
        f"🔥 <b>Ultra-Cheap Hub Services:</b> <code>{cheap_total}</code>\n"
        f"🎯 <b>Platform Separation:</b> Strict Category-First Active",
        parse_mode="HTML"
    )

@bot.message_handler(func=lambda m: m.text == "📈 Admin: Margin" and m.from_user.id == ADMIN_ID)
def h_admin_margin(m):
    user_states[ADMIN_ID] = {"state": "wait_margin"}
    bot.send_message(ADMIN_ID, "📈 <b>Enter profit % (e.g. 50):</b>", parse_mode="HTML", reply_markup=back_cancel_kb())

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get("state") == "wait_margin" and m.from_user.id == ADMIN_ID)
def h_process_margin(m):
    try:
        pct = float(m.text.strip())
        multiplier = 1.0 + (pct / 100.0)
        execute_db("UPDATE settings SET value=? WHERE key='global_margin'", (str(multiplier),))
        execute_db("UPDATE managed_services SET margin=?", (multiplier,))
        bot.send_message(ADMIN_ID, f"✅ Margin updated to {pct}% markup.", parse_mode="HTML", reply_markup=main_kb(ADMIN_ID))
    except: bot.send_message(ADMIN_ID, "❌ Numbers only.")
    user_states.pop(ADMIN_ID, None)

@bot.message_handler(func=lambda m: m.text == "📢 Admin: Broadcast" and m.from_user.id == ADMIN_ID)
def h_admin_broadcast(m):
    user_states[ADMIN_ID] = {"state": "wait_broadcast"}
    bot.send_message(ADMIN_ID, "📢 <b>Enter broadcast message:</b>", parse_mode="HTML", reply_markup=back_cancel_kb())

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get("state") == "wait_broadcast" and m.from_user.id == ADMIN_ID)
def h_process_broadcast(m):
    users = execute_db("SELECT user_id FROM users WHERE is_banned=0", fetch_all=True)
    sent = 0
    for u in users:
        try:
            bot.send_message(u[0], f"📢 <b>ANNOUNCEMENT:</b>\n\n{m.text}", parse_mode="HTML")
            sent += 1
            time.sleep(0.04)
        except: pass
    bot.send_message(ADMIN_ID, f"✅ Broadcast sent to {sent} users.", parse_mode="HTML", reply_markup=main_kb(ADMIN_ID))
    user_states.pop(ADMIN_ID, None)

@bot.message_handler(func=lambda m: m.text == "🎫 Admin: Tickets" and m.from_user.id == ADMIN_ID)
def h_admin_view_tickets(m):
    tickets = execute_db("SELECT ticket_id, user_id, message FROM tickets WHERE status='OPEN' LIMIT 5", fetch_all=True)
    if not tickets: return bot.send_message(ADMIN_ID, "✅ No open tickets.")
    for t in tickets:
        bot.send_message(ADMIN_ID, f"🎫 <b>Ticket #{t[0]}</b>\nUser: <code>{t[1]}</code>\n💬 {html.escape(t[2])}", parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text == "💾 Admin: Backup DB" and m.from_user.id == ADMIN_ID)
def handle_admin_backup(m):
    uid = m.from_user.id
    bot.send_message(uid, "⏳ <i>Generating snapshot...</i>", parse_mode="HTML")
    backup_file = f"backup_{int(time.time())}.db"
    try:
        with db_lock:
            with sqlite3.connect('panel_v17.db') as src, sqlite3.connect(backup_file) as dst: src.backup(dst)
        with open(backup_file, 'rb') as doc:
            bot.send_document(uid, doc, caption="💾 <b>Database Backup</b> ✅", parse_mode="HTML")
    except Exception as e: bot.send_message(uid, f"❌ Backup Failed: <code>{e}</code>", parse_mode="HTML")
    finally:
        if os.path.exists(backup_file): os.remove(backup_file)

@bot.message_handler(func=lambda m: m.text == "🔄 Admin: Restore DB" and m.from_user.id == ADMIN_ID)
def handle_admin_restore_prompt(m):
    user_states[ADMIN_ID] = {"state": "wait_for_db_upload"}
    bot.send_message(ADMIN_ID, "⚠️ Upload <code>.db</code> file below:", parse_mode="HTML", reply_markup=back_cancel_kb())

@bot.message_handler(content_types=['document'])
def handle_document_upload(m):
    uid = m.from_user.id
    if uid == ADMIN_ID and user_states.get(uid, {}).get("state") == "wait_for_db_upload":
        if not m.document.file_name.endswith('.db'): return bot.send_message(uid, "❌ .db file only.", reply_markup=main_kb(uid))
        temp_file = f"restore_{int(time.time())}.db"
        try:
            bot.send_message(uid, "⏳ <i>Restoring...</i>", parse_mode="HTML")
            downloaded = bot.download_file(bot.get_file(m.document.file_id).file_path)
            with open(temp_file, 'wb') as f: f.write(downloaded)
            with db_lock:
                with sqlite3.connect(temp_file) as src, sqlite3.connect('panel_v17.db') as dst: src.backup(dst)
            init_database()
            bot.send_message(uid, "✅ <b>RESTORED SUCCESSFULLY!</b>", parse_mode="HTML", reply_markup=main_kb(uid))
        except Exception as e: bot.send_message(uid, f"❌ Failed: {e}", reply_markup=main_kb(uid))
        finally:
            user_states.pop(uid, None)
            if os.path.exists(temp_file): os.remove(temp_file)

# =======================================================================================
# 9. PLATFORM BROWSING, 🔥 CHEAP SERVICES HUB & GUIDED BUYING
# =======================================================================================
def build_platforms_kb():
    platforms = execute_db("SELECT DISTINCT platform FROM managed_services WHERE disabled=0 ORDER BY platform ASC", fetch_all=True)
    kb = InlineKeyboardMarkup(row_width=2)
    # Dedicated Cheap Services Column at the very top!
    kb.row(InlineKeyboardButton("🔥 Cheap Services (Ultra Low Price) 💸", callback_data="cheap_hub"))
    btns = [InlineKeyboardButton(f"{p[0]}", callback_data=f"plt_{idx}") for idx, p in enumerate(platforms)]
    kb.add(*btns)
    return kb, len(platforms) > 0

@bot.message_handler(func=lambda m: m.text == "🛒 Browse Services 🚀")
def h_browse(m):
    if is_banned(m.from_user.id): return bot.send_message(m.chat.id, "🚫 You are banned.")
    user_states.pop(m.from_user.id, None)
    kb, has_platforms = build_platforms_kb()
    if not has_platforms:
        return bot.send_message(m.chat.id, "⚠️ No services loaded! Admin needs to run Smart Sync.")
    msg = (
        "🛒 <b>CHOOSE YOUR PLATFORM OR CHEAP HUB:</b> 🌐✨\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "🔥 <b>Tip:</b> Tap <b>'🔥 Cheap Services'</b> for our lowest wholesale rates sorted by social media app!\n"
        "👇 <i>Select an option below:</i>"
    )
    bot.send_message(m.chat.id, msg, parse_mode="HTML", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data == "back_platforms")
def h_back_platforms(c):
    bot.answer_callback_query(c.id)
    kb, _ = build_platforms_kb()
    msg = (
        "🛒 <b>CHOOSE YOUR PLATFORM OR CHEAP HUB:</b> 🌐✨\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "🔥 <b>Tip:</b> Tap <b>'🔥 Cheap Services'</b> for our lowest wholesale rates!\n"
        "👇 <i>Select an option below:</i>"
    )
    bot.edit_message_text(msg, c.message.chat.id, c.message.message_id, parse_mode="HTML", reply_markup=kb)

# ---------------- 🔥 CHEAP SERVICES FLOW ----------------
@bot.callback_query_handler(func=lambda c: c.data == "cheap_hub")
def h_cheap_hub(c):
    bot.answer_callback_query(c.id)
    platforms = execute_db("SELECT DISTINCT platform FROM managed_services WHERE disabled=0 AND is_cheap=1 ORDER BY platform ASC", fetch_all=True)
    if not platforms:
        platforms = execute_db("SELECT DISTINCT platform FROM managed_services WHERE disabled=0 ORDER BY platform ASC", fetch_all=True)
    kb = InlineKeyboardMarkup(row_width=2)
    btns = [InlineKeyboardButton(f"🔥 {p[0]}", callback_data=f"cplt_{idx}") for idx, p in enumerate(platforms)]
    kb.add(*btns)
    kb.row(InlineKeyboardButton("🔙 Back to Main Services", callback_data="back_platforms"))
    msg = (
        "🔥 <b>ULTRA CHEAP SERVICES HUB</b> 💸\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "Welcome to the budget zone! Here you get the <b>absolute lowest-priced services</b> separated cleanly by social media platform.\n\n"
        "👇 <i>Choose your social media platform:</i>"
    )
    bot.edit_message_text(msg, c.message.chat.id, c.message.message_id, parse_mode="HTML", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("cplt_"))
def h_cheap_platform_services(c):
    bot.answer_callback_query(c.id)
    p_idx = int(c.data.split("_")[1])
    platforms = execute_db("SELECT DISTINCT platform FROM managed_services WHERE disabled=0 AND is_cheap=1 ORDER BY platform ASC", fetch_all=True)
    if not platforms:
        platforms = execute_db("SELECT DISTINCT platform FROM managed_services WHERE disabled=0 ORDER BY platform ASC", fetch_all=True)
    if p_idx >= len(platforms): return
    platform_name = platforms[p_idx][0]

    svcs = execute_db(
        "SELECT service_id, name, rate, margin, avg_time FROM managed_services WHERE platform=? AND disabled=0 ORDER BY (rate * margin) ASC LIMIT 12",
        (platform_name,), fetch_all=True
    )
    kb = InlineKeyboardMarkup(row_width=1)
    for s in svcs:
        price = s[2] * s[3]
        dot, _, _ = get_service_health_and_speed(s[1], s[4])
        short_name = clean_service_name(s[1], max_len=23)
        kb.add(InlineKeyboardButton(f"{dot} ₹{price:.2f}/1K | {short_name}", callback_data=f"ccard_{s[0]}_{p_idx}"))
    kb.add(InlineKeyboardButton("🔙 Back to Cheap Platforms", callback_data="cheap_hub"))

    msg = (
        f"🔥 <b>CHEAPEST {html.escape(platform_name.upper())} SERVICES</b> 💸\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"🟢 = Optimal Speed | 🟡 = Normal Load\n"
        f"<i>Prices are shown first so you never miss the rate!</i>\n\n"
        f"👇 <i>Tap any service to view full details & order:</i>"
    )
    bot.edit_message_text(msg, c.message.chat.id, c.message.message_id, parse_mode="HTML", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("ccard_"))
def h_cheap_card_view(c):
    bot.answer_callback_query(c.id)
    _, sid, p_idx = c.data.split("_")
    svc = execute_db("SELECT service_id, platform, name, rate, min_qty, max_qty, avg_time, margin, category FROM managed_services WHERE service_id=?", (int(sid),), fetch=True)
    if not svc: return
    final_price = svc[3] * svc[7]
    _, speed_bar, health_txt = get_service_health_and_speed(svc[2], svc[6])

    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("🚀 Order This Cheap Service Now", callback_data=f"buy_{svc[0]}"))
    kb.add(InlineKeyboardButton("🔙 Back to Cheap List", callback_data=f"cplt_{p_idx}"))

    msg = (
        f"🔥 <b>ULTRA CHEAP SERVICE CARD</b> 📋\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"🌐 <b>Platform:</b> {html.escape(svc[1])}\n"
        f"📁 <b>Category:</b> {html.escape(svc[8])}\n"
        f"📌 <b>Full Name:</b> {html.escape(svc[2])}\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"💰 <b>Price:</b> <code>₹{final_price:.2f}</code> per 1,000\n"
        f"📊 <b>Limits:</b> Min <code>{svc[4]:,}</code> — Max <code>{svc[5]:,}</code>\n"
        f"🩺 <b>Service Health:</b> <code>{health_txt}</code>\n"
        f"⏱️ <b>Live Speedometer:</b>\n<code>{speed_bar}</code>\n"
        f"🛡️ <b>Safe Auto-Refund:</b> <code>100% Protected</code>"
    )
    bot.edit_message_text(msg, c.message.chat.id, c.message.message_id, parse_mode="HTML", reply_markup=kb)

# ---------------- STANDARD PLATFORM FLOW ----------------
@bot.callback_query_handler(func=lambda c: c.data.startswith("plt_"))
def h_platform_view(c):
    bot.answer_callback_query(c.id)
    idx = int(c.data.split("_")[1])
    platforms = execute_db("SELECT DISTINCT platform FROM managed_services WHERE disabled=0 ORDER BY platform ASC", fetch_all=True)
    if idx >= len(platforms): return
    platform_name = platforms[idx][0]
    cats = execute_db("SELECT DISTINCT category FROM managed_services WHERE platform=? AND disabled=0", (platform_name,), fetch_all=True)
    kb = InlineKeyboardMarkup(row_width=1)
    for c_idx, cat in enumerate(cats):
        short_cat = cat[0][:38] + ".." if len(cat[0]) > 40 else cat[0]
        kb.add(InlineKeyboardButton(f"📁 {short_cat}", callback_data=f"cat_{idx}_{c_idx}"))
    kb.add(InlineKeyboardButton("🔙 Back to Platforms", callback_data="back_platforms"))
    bot.edit_message_text(f"📂 <b>{html.escape(platform_name.upper())} CATEGORIES</b> 🚀\n━━━━━━━━━━━━━━━━━━━\n👇 <i>Select a category:</i>", c.message.chat.id, c.message.message_id, parse_mode="HTML", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("cat_"))
def h_category_services(c):
    bot.answer_callback_query(c.id)
    _, p_idx, c_idx = c.data.split("_")
    p_idx, c_idx = int(p_idx), int(c_idx)
    platforms = execute_db("SELECT DISTINCT platform FROM managed_services WHERE disabled=0 ORDER BY platform ASC", fetch_all=True)
    if p_idx >= len(platforms): return
    platform_name = platforms[p_idx][0]
    cats = execute_db("SELECT DISTINCT category FROM managed_services WHERE platform=? AND disabled=0", (platform_name,), fetch_all=True)
    if c_idx >= len(cats): return
    category_name = cats[c_idx][0]
    svcs = execute_db("SELECT service_id, name, rate, margin, avg_time FROM managed_services WHERE platform=? AND category=? AND disabled=0 ORDER BY (rate * margin) ASC", (platform_name, category_name), fetch_all=True)
    kb = InlineKeyboardMarkup(row_width=1)
    for s in svcs:
        price = s[2] * s[3]
        dot, _, _ = get_service_health_and_speed(s[1], s[4])
        short_name = clean_service_name(s[1], max_len=23)
        kb.add(InlineKeyboardButton(f"{dot} ₹{price:.2f}/1K | {short_name}", callback_data=f"card_{s[0]}_{p_idx}_{c_idx}"))
    kb.add(InlineKeyboardButton(f"🔙 Back to {platform_name}", callback_data=f"plt_{p_idx}"))
    bot.edit_message_text(
        f"📂 <b>{html.escape(category_name.upper())}</b> 📊\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"🟢 = Optimal Speed | 🟡 = Normal Load\n"
        f"👇 <i>Tap a service to view full name, speedometer & order:</i>",
        c.message.chat.id, c.message.message_id, parse_mode="HTML", reply_markup=kb
    )

@bot.callback_query_handler(func=lambda c: c.data.startswith("card_"))
def h_card_view(c):
    bot.answer_callback_query(c.id)
    _, sid, p_idx, c_idx = c.data.split("_")
    svc = execute_db("SELECT service_id, platform, name, rate, min_qty, max_qty, avg_time, margin FROM managed_services WHERE service_id=?", (int(sid),), fetch=True)
    if not svc: return
    final_price = svc[3] * svc[7]
    _, speed_bar, health_txt = get_service_health_and_speed(svc[2], svc[6])

    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("🚀 Order This Service Now", callback_data=f"buy_{svc[0]}"))
    kb.add(InlineKeyboardButton("🔙 Back to Services", callback_data=f"cat_{p_idx}_{c_idx}"))
    msg = (
        f"🏷️ <b>SERVICE DETAILS & HEALTH</b> 📋\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"📌 <b>Full Name:</b> {html.escape(svc[2])}\n"
        f"💰 <b>Price:</b> <code>₹{final_price:.2f}</code> per 1,000\n"
        f"📊 <b>Limits:</b> Min <code>{svc[4]:,}</code> — Max <code>{svc[5]:,}</code>\n"
        f"🩺 <b>Service Health:</b> <code>{health_txt}</code>\n"
        f"⏱️ <b>Live Speedometer:</b>\n<code>{speed_bar}</code>\n"
        f"♻️ <b>Protection:</b> <code>Auto-Refund Active</code> 🛡️"
    )
    bot.edit_message_text(msg, c.message.chat.id, c.message.message_id, parse_mode="HTML", reply_markup=kb)

# ---------------- GUIDED ORDERING & SMART LINK VALIDATOR ----------------
@bot.callback_query_handler(func=lambda c: c.data.startswith("buy_"))
def h_buy_service(c):
    bot.answer_callback_query(c.id)
    if is_banned(c.from_user.id): return bot.send_message(c.message.chat.id, "🚫 You are banned.")
    sid = int(c.data.split("_")[1])
    svc = execute_db("SELECT platform, name, min_qty, max_qty, rate, margin FROM managed_services WHERE service_id=?", (sid,), fetch=True)
    if not svc: return
    user_states[c.from_user.id] = {"state": "get_link", "sid": sid}

    plat = svc[0]
    if "Instagram" in plat: ex = "https://www.instagram.com/p/Cxxxx/ or profile link"
    elif "Telegram" in plat: ex = "https://t.me/yourchannel or post link"
    elif "YouTube" in plat: ex = "https://youtu.be/xxxx or channel link"
    else: ex = "https://... (Full public link)"

    guide_msg = (
        f"🧭 <b>ORDER GUIDE — STEP 1 of 2 (TARGET LINK)</b> 🔗\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"📌 <b>Selected:</b> {html.escape(svc[1][:55])}\n"
        f"🌐 <b>Platform:</b> {html.escape(plat)}\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"⚠️ <b>CHECKLIST BEFORE SENDING LINK:</b>\n"
        f"1️⃣ Your account/channel/post <b>MUST BE PUBLIC</b> (Not Private!).\n"
        f"2️⃣ Send a valid <b>{html.escape(plat)}</b> link.\n"
        f"3️⃣ Example: <code>{ex}</code>\n\n"
        f"👇 <b>Paste your target link below:</b>"
    )
    bot.send_message(c.message.chat.id, guide_msg, parse_mode="HTML", reply_markup=back_cancel_kb())

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get("state") == "get_link")
def h_link_input(m):
    uid = m.from_user.id
    sid = user_states[uid]["sid"]
    svc = execute_db("SELECT platform, name, min_qty, max_qty, rate, margin FROM managed_services WHERE service_id=?", (sid,), fetch=True)
    if not svc:
        user_states.pop(uid, None)
        return bot.send_message(m.chat.id, "❌ Service no longer available.", reply_markup=main_kb(uid))

    # Smart Auto-Link Validator check
    is_valid, result_or_err = validate_order_link(svc[0], m.text)
    if not is_valid:
        return bot.send_message(m.chat.id, result_or_err, parse_mode="HTML", reply_markup=back_cancel_kb())

    unit_price = svc[4] * svc[5]
    min_q, max_q = svc[2], svc[3]
    sample_qty = max(min_q, 100) if 100 <= max_q else min_q
    sample_cost = (sample_qty / 1000.0) * unit_price

    user_states[uid].update({"state": "get_qty", "link": result_or_err})
    msg = (
        f"✅ <b>Link Verified & Locked!</b> 🔗\n"
        f"🔍 <b>Preview:</b> <code>{html.escape(result_or_err)}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"🧭 <b>ORDER GUIDE — STEP 2 of 2 (QUANTITY)</b> 🔢\n"
        f"📊 <b>Allowed Range:</b> Min <code>{min_q:,}</code> — Max <code>{max_q:,}</code>\n"
        f"💰 <b>Rate:</b> <code>₹{unit_price:.2f}</code> per 1,000\n"
        f"💡 <i>Example: Typing <code>{sample_qty}</code> will cost <code>₹{sample_cost:.2f}</code></i>\n\n"
        f"👇 <b>Type the quantity in numbers only (e.g. {sample_qty}):</b>"
    )
    bot.send_message(m.chat.id, msg, parse_mode="HTML", reply_markup=back_cancel_kb(), disable_web_page_preview=True)

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get("state") == "get_qty")
def h_qty_input(m):
    uid = m.from_user.id
    state = user_states[uid]
    try:
        qty = int(m.text.strip().replace(",", ""))
    except:
        return bot.send_message(m.chat.id, "❌ <b>Invalid Quantity!</b> Please type numbers only (e.g. <code>500</code> or <code>1000</code>).", parse_mode="HTML", reply_markup=back_cancel_kb())

    svc = execute_db("SELECT provider, provider_service_id, rate, margin, min_qty, max_qty, name, platform FROM managed_services WHERE service_id=?", (state["sid"],), fetch=True)
    if not svc: return
    if qty < svc[4] or qty > svc[5]:
        return bot.send_message(
            m.chat.id,
            f"🚫 <b>Quantity Out of Range!</b>\n"
            f"Please enter a number between <code>{svc[4]:,}</code> (Minimum) and <code>{svc[5]:,}</code> (Maximum):",
            parse_mode="HTML",
            reply_markup=back_cancel_kb()
        )

    cost = (qty / 1000.0) * (svc[2] * svc[3])
    base_cost = (qty / 1000.0) * svc[2]
    profit = cost - base_cost
    
    u_bal = execute_db("SELECT balance FROM users WHERE user_id=?", (uid,), fetch=True)[0]
    
    if u_bal < cost: 
        user_states.pop(uid, None)
        needed = cost - u_bal
        return bot.send_message(
            m.chat.id,
            f"❌ <b>INSUFFICIENT WALLET BALANCE!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"💰 <b>Order Cost:</b> <code>₹{cost:.2f}</code>\n"
            f"💳 <b>Your Wallet:</b> <code>₹{u_bal:.2f}</code>\n"
            f"➕ <b>Need Extra:</b> <code>₹{needed:.2f}</code>\n\n"
            f"💡 <i>Tap <b>'💳 Add Funds 💸'</b> below to top up your wallet!</i>",
            parse_mode="HTML",
            reply_markup=main_kb(uid)
        )

    bot.send_message(m.chat.id, "⏳ <i>Connecting to server & dispatching your order...</i>", parse_mode="HTML")
    api_res, prov_used = call_provider_api(svc[0], 'add', {'service': svc[1], 'link': state['link'], 'quantity': qty})
    
    if api_res and 'order' in api_res:
        execute_db("UPDATE users SET balance=balance-?, total_spent=total_spent+? WHERE user_id=?", (cost, cost, uid))
        execute_db("INSERT INTO orders (user_id, provider, api_order_id, service_id, quantity, cost, profit, auto_refill) VALUES (?,?,?,?,?,?,?,1)",
                   (uid, prov_used, api_res['order'], state["sid"], qty, cost, profit))
        bot.send_message(
            m.chat.id,
            f"✅ <b>ORDER SUCCESSFULLY DISPATCHED!</b> 🎉\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"🧾 <b>Order ID:</b> <code>{api_res['order']}</code>\n"
            f"📌 <b>Service:</b> {html.escape(clean_service_name(svc[6], 35))}\n"
            f"🔢 <b>Quantity:</b> <code>{qty:,}</code>\n"
            f"💰 <b>Deducted:</b> <code>₹{cost:.2f}</code>\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"🔔 <i>You will receive a live automatic DM here as soon as your order completes!</i>",
            parse_mode="HTML",
            reply_markup=main_kb(uid)
        )

        # Forward anonymized live proof to @csplogs
        send_proof_log(
            f"🚀 <b>NEW ORDER DISPATCHED</b> ⚡\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"👤 <b>Buyer:</b> {mask_user(uid, m.from_user.first_name)}\n"
            f"🌐 <b>Platform:</b> {html.escape(svc[7])}\n"
            f"📦 <b>Service:</b> {html.escape(clean_service_name(svc[6], 32))}\n"
            f"🔢 <b>Quantity:</b> <code>{qty:,}</code>\n"
            f"💰 <b>Amount Paid:</b> <code>₹{cost:.2f}</code>\n"
            f"🧾 <b>Order ID:</b> <code>#{api_res['order']}</code>\n"
            f"🤖 <b>Order via:</b> @{bot.get_me().username}"
        )
    else:
        err_detail = api_res.get('error', 'Server busy') if isinstance(api_res, dict) else 'Server busy'
        bot.send_message(
            m.chat.id,
            f"⚠️ <b>Order Not Placed (₹0 Deducted)!</b>\n"
            f"Reason: <code>{html.escape(str(err_detail))}</code>\n\n"
            f"🛡️ <i>Your wallet balance is untouched. Please check that your link is public and valid!</i>",
            parse_mode="HTML",
            reply_markup=main_kb(uid)
        )
    user_states.pop(uid, None)

# =======================================================================================
# 10. BACKGROUND MONITOR: AUTO-REFUNDS, LIVE DMs & @CSPLOGS COMPLETION PROOFS
# =======================================================================================
def auto_refill_and_status_monitor():
    while True:
        try:
            orders = execute_db(
                "SELECT db_id, provider, api_order_id, status, user_id, quantity, service_id, cost FROM orders WHERE status IN ('pending', 'In progress', 'Processing', 'Pending')",
                fetch_all=True
            )
            if orders:
                for o in orders:
                    db_id, prov, api_oid, old_status, uid, qty, sid, cost = o
                    res, _ = call_provider_api(prov, 'status', {'order': api_oid})
                    if res and 'status' in res:
                        raw_status = str(res['status']).strip()
                        new_status = raw_status.capitalize()

                        if new_status != old_status:
                            svc = execute_db("SELECT name, platform FROM managed_services WHERE service_id=?", (sid,), fetch=True)
                            svc_name = svc[0] if svc else "SMM Service"
                            plat_name = svc[1] if svc else "Social Media"

                            # 1. AUTOMATIC FULL REFUND ON CANCELED OR PARTIAL ORDERS
                            if new_status in ['Canceled', 'Cancelled', 'Partial']:
                                execute_db("UPDATE orders SET status='Refunded', profit=0.0 WHERE db_id=?", (db_id,))
                                if cost > 0:
                                    execute_db("UPDATE users SET balance = balance + ?, total_spent = MAX(0.0, total_spent - ?) WHERE user_id=?", (cost, cost, uid))
                                    execute_db("INSERT INTO transactions (user_id, amount, status) VALUES (?, ?, ?)", (uid, cost, f"AUTO_REFUND_#{api_oid}"))

                                refund_msg = (
                                    f"🛡️ <b>100% AUTOMATIC WALLET REFUND</b> 🔄\n"
                                    f"━━━━━━━━━━━━━━━━━━━\n"
                                    f"🧾 <b>Order ID:</b> <code>#{api_oid}</code>\n"
                                    f"📌 <b>Service:</b> {html.escape(clean_service_name(svc_name, 35))}\n"
                                    f"💰 <b>Refunded Amount:</b> <code>+₹{cost:.2f}</code> (Full Amount)\n"
                                    f"━━━━━━━━━━━━━━━━━━━\n"
                                    f"ℹ️ <b>Why did this happen?</b>\n"
                                    f"The upstream delivery server experienced a temporary sync overload or link restriction. "
                                    f"To protect your money, our automated safety system immediately returned <b>100% of your ₹{cost:.2f}</b> back to your wallet!\n\n"
                                    f"🚀 <i>You can re-order anytime or try an alternative server from <b>🛒 Browse Services</b>!</i>"
                                )
                                try: bot.send_message(uid, refund_msg, parse_mode="HTML")
                                except: pass

                            # 2. COMPLETED ORDER NOTIFICATION & @CSPLOGS PROOF
                            elif new_status == 'Completed':
                                execute_db("UPDATE orders SET status='Completed' WHERE db_id=?", (db_id,))
                                done_msg = (
                                    f"✅ <b>ORDER COMPLETED SUCCESSFULLY!</b> 🎉\n"
                                    f"━━━━━━━━━━━━━━━━━━━\n"
                                    f"🧾 <b>Order ID:</b> <code>#{api_oid}</code>\n"
                                    f"📦 <b>Service:</b> {html.escape(clean_service_name(svc_name, 35))}\n"
                                    f"🔢 <b>Delivered:</b> <code>{qty:,}</code>\n"
                                    f"🛡️ <b>Status:</b> <code>100% Completed</code>\n\n"
                                    f"❤️ <i>Thank you for trusting Cheap SMM Panel!</i>"
                                )
                                try: bot.send_message(uid, done_msg, parse_mode="HTML")
                                except: pass

                                u_row = execute_db("SELECT first_name FROM users WHERE user_id=?", (uid,), fetch=True)
                                fname = u_row[0] if u_row else "User"
                                send_proof_log(
                                    f"✅ <b>ORDER COMPLETED PROOF</b> 🎉\n"
                                    f"━━━━━━━━━━━━━━━━━━━\n"
                                    f"👤 <b>Client:</b> {mask_user(uid, fname)}\n"
                                    f"🌐 <b>Platform:</b> {html.escape(plat_name)}\n"
                                    f"📦 <b>Service:</b> {html.escape(clean_service_name(svc_name, 32))}\n"
                                    f"🔢 <b>Delivered:</b> <code>{qty:,}</code>\n"
                                    f"🧾 <b>Order ID:</b> <code>#{api_oid}</code>\n"
                                    f"⚡ <b>Status:</b> <code>100% Delivered ✅</code>"
                                )
                            else:
                                execute_db("UPDATE orders SET status=? WHERE db_id=?", (new_status, db_id))
        except Exception as e:
            logging.error(f"Monitor error: {e}")
        time.sleep(180) # Checks every 3 minutes

if __name__ == '__main__':
    init_database()
    try:
        bot.remove_webhook()
        time.sleep(1)
    except:
        pass
    threading.Thread(target=lambda: bot.infinity_polling(skip_pending=True, timeout=60), daemon=True).start()
    threading.Thread(target=auto_refill_and_status_monitor, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
