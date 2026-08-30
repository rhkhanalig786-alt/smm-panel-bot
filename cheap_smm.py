import telebot, requests, sqlite3, logging, time, os, urllib.parse, threading, html
from io import BytesIO
from flask import Flask
from telebot.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

BOT_TOKEN = os.environ.get('BOT_TOKEN', '8228287584:AAEZIAnprSJ4SBchDb1UBwAED5gxwEeGvwU')
bot = telebot.TeleBot(BOT_TOKEN, threaded=True, num_threads=10)

PROVIDERS = {
    "provider_primary": {
        "url": os.environ.get("API_URL_1", "https://iggrowbot.com/api/v2"),
        "key": os.environ.get("API_KEY_1", "c1ff6a119106be59dab2829144bc413a")
    }
}

FREE_VIEWS_SERVICE_ID = int(os.environ.get('FREE_VIEWS_SERVICE_ID', 1753))
FREE_VIEWS_PROVIDER = "https://iggrowbot.com/api/v2"

ADMIN_ID = 6034840006
UPI_ID = "rahikhann@fam"
SUPPORT_USERNAME = "@itzdevrahi"
MIN_DEPOSIT = 15.0  

user_states = {}
db_lock = threading.Lock()

app = Flask(__name__)
@app.route('/')
def home(): return "🚀 SMM V14 ONLINE 🌟"

def execute_db(query, params=(), fetch=False, fetch_all=False, return_id=False):
    with db_lock:
        try:
            with sqlite3.connect('panel_v14.db', check_same_thread=False, timeout=20) as conn:
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
            service_id INTEGER, quantity INTEGER, cost REAL, status TEXT DEFAULT 'pending',
            auto_refill INTEGER DEFAULT 1, last_refill_check TIMESTAMP DEFAULT CURRENT_TIMESTAMP, placed_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS managed_services (
            service_id INTEGER PRIMARY KEY, category TEXT, name TEXT, provider TEXT DEFAULT 'provider_primary',
            provider_service_id INTEGER, rate REAL, min_qty INTEGER DEFAULT 10, max_qty INTEGER DEFAULT 100000,
            margin REAL DEFAULT 1.50, disabled INTEGER DEFAULT 0
        )""",
        "CREATE TABLE IF NOT EXISTS transactions (tx_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount REAL, status TEXT, date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
        "CREATE TABLE IF NOT EXISTS tickets (ticket_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, message TEXT, status TEXT DEFAULT 'OPEN', reply TEXT)",
        "CREATE TABLE IF NOT EXISTS referrals (referrer_id INTEGER, referred_id INTEGER, reward_claimed INTEGER DEFAULT 1, PRIMARY KEY(referrer_id, referred_id))",
        "CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)"
    ]
    for table in tables: execute_db(table)
    if not execute_db("SELECT value FROM settings WHERE key='global_margin'", fetch=True):
        execute_db("INSERT INTO settings (key, value) VALUES ('global_margin', '1.50')")

def call_provider_api(provider_name, action, extra=None):
    prov = PROVIDERS.get(provider_name, PROVIDERS["provider_primary"])
    payload = {'key': prov['key'], 'action': action}
    if extra: payload.update(extra)
    try:
        res = requests.post(prov['url'], data=payload, timeout=15)
        return res.json(), provider_name
    except Exception as e:
        logging.error(f"API Call Failed: {e}")
        return None, provider_name

def get_best_provider_for_service(service_id):
    svc = execute_db("SELECT provider, provider_service_id, rate, margin FROM managed_services WHERE service_id=?", (service_id,), fetch=True)
    if svc: return svc[0], svc[1], svc[2], svc[3]
    return "provider_primary", service_id, 10.0, 1.50

def main_kb(uid):
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add("🛒 Browse Services 🚀", "🎁 Claim Free 1K Views 🌟")
    kb.add("💰 My Profile 👤", "💳 Add Funds 💸")
    kb.add("📦 Order History 📜", "🤝 Referral Program 👥")
    kb.add("📞 Support 🎫")
    if uid == ADMIN_ID:
        kb.add("🧠 Admin: Smart Sync", "📈 Admin: Margin")
        kb.add("🎫 Admin: Tickets", "📢 Admin: Broadcast")
        kb.add("💾 Admin: Backup DB", "🔄 Admin: Restore DB")
    return kb

def cancel_kb(): return ReplyKeyboardMarkup(resize_keyboard=True).add("❌ Cancel")

@bot.message_handler(commands=['start'])
def h_start(m):
    uid = m.from_user.id
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
            try: bot.send_message(referrer_id, "🎊 <b>BOOM! A friend just joined using your link!</b> 🎊\n🎁 <b>You received +1 Free 1K Views Credit!</b> 🌟", parse_mode="HTML")
            except: pass

    safe_name = html.escape(m.from_user.first_name or "User")
    msg = (
        f"👋 <b>Welcome to the Ultimate SMM Panel, {safe_name}!</b> 🚀🔥\n\n"
        f"I am your fully automated social media growth assistant! 📈✨ Let's make you go viral today! 🌟\n\n"
        f"👇 <b>HOW TO USE ME IN 3 EASY STEPS:</b> 👇\n"
        f"1️⃣ Tap <b>'💳 Add Funds 💸'</b> to securely top up your wallet. 🏦\n"
        f"2️⃣ Tap <b>'🛒 Browse Services 🚀'</b> to pick what you want to grow! 📊\n"
        f"3️⃣ Paste your post link, type the exact quantity, and watch the magic happen! ✨🔮\n\n"
        f"<i>Ready? Use the buttons below to start!</i> 👇🚀"
    )
    bot.send_message(m.chat.id, msg, parse_mode="HTML", reply_markup=main_kb(uid))

@bot.message_handler(func=lambda m: m.text == "❌ Cancel")
def h_cancel(m):
    user_states.pop(m.from_user.id, None)
    bot.send_message(m.chat.id, "🚫 <b>Action Cancelled successfully!</b> 🛑\n\n🏠 <i>You are safely back at the main menu.</i> ✨", parse_mode="HTML", reply_markup=main_kb(m.from_user.id))

@bot.message_handler(func=lambda m: m.text == "💰 My Profile 👤")
def h_profile(m):
    u = execute_db("SELECT balance, total_spent, free_views_credits, referral_code FROM users WHERE user_id=?", (m.from_user.id,), fetch=True)
    if not u: return
    ref_count = execute_db("SELECT COUNT(*) FROM referrals WHERE referrer_id=?", (m.from_user.id,), fetch=True)[0]
    msg = (
        f"👤 <b>YOUR VIP PROFILE & STATS</b> 📊👑\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 <b>Account ID:</b> <code>{m.from_user.id}</code> 🔐\n"
        f"💳 <b>Wallet Balance:</b> <code>₹{u[0]:.2f}</code> 💵\n"
        f"📈 <b>Total Invested:</b> <code>₹{u[1]:.2f}</code> 🚀\n"
        f"🎁 <b>Free 1K Views Credits:</b> <code>{u[2]}</code> 🌟\n"
        f"👥 <b>Total Friends Referred:</b> <code>{ref_count}</code> 🤝\n\n"
        f"💡 <i>Pro Tip: Running low on balance? Tap '💳 Add Funds 💸' below!</i> ⚡️"
    )
    bot.send_message(m.chat.id, msg, parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text == "📦 Order History 📜")
def h_order_history(m):
    orders = execute_db("SELECT api_order_id, service_id, quantity, cost, status FROM orders WHERE user_id=? ORDER BY placed_time DESC LIMIT 5", (m.from_user.id,), fetch_all=True)
    if not orders: return bot.send_message(m.chat.id, "📦 <b>You haven't placed any orders yet!</b> 🛑\n\n🛒 <i>Tap 'Browse Services' to get started!</i> 🚀", parse_mode="HTML")
    msg = "📦 <b>YOUR RECENT ORDERS:</b> 📜✨\n━━━━━━━━━━━━━━━━━━━\n"
    for o in orders:
        status_emoji = "✅" if o[4].lower() == "completed" else ("⏳" if o[4].lower() in ["pending", "processing", "in progress"] else "⚠️")
        msg += f"🧾 <b>Order ID:</b> <code>{o[0]}</code> 🆔\n🔢 <b>Qty:</b> {o[2]} 📊 | 💰 <b>Cost:</b> ₹{o[3]:.2f} 💵\n{status_emoji} <b>Status:</b> <code>{o[4]}</code>\n───────────────────\n"
    bot.send_message(m.chat.id, msg, parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text == "📞 Support 🎫")
def h_support(m):
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("💬 Chat directly with Owner 👨‍💻", url=f"https://t.me/{SUPPORT_USERNAME.replace('@','')}"),
        InlineKeyboardButton("🎫 Create Support Ticket 📝", callback_data="make_ticket")
    )
    bot.send_message(m.chat.id, "📞 <b>24/7 CUSTOMER SUPPORT</b> 🛠️🆘\n\nGot a question, need a refill, or have a payment issue? We've got your back! 💪\n\n👇 <i>Choose an option below to reach us immediately:</i>", parse_mode="HTML", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data == "make_ticket")
def h_ticket_init(c):
    bot.answer_callback_query(c.id)
    user_states[c.from_user.id] = {"state": "waiting_ticket_text"}
    bot.send_message(c.message.chat.id, "📝 <b>CREATE A SUPPORT TICKET</b> 🎫\n\n👇 <i>Please type your issue, order ID, or question below and hit send. Be as detailed as possible!</i> ✍️", parse_mode="HTML", reply_markup=cancel_kb())

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get("state") == "waiting_ticket_text")
def h_ticket_save(m):
    uid = m.from_user.id
    tid = execute_db("INSERT INTO tickets (user_id, message) VALUES (?,?)", (uid, m.text), return_id=True)
    user_states.pop(uid, None)
    bot.send_message(m.chat.id, f"✅ <b>Ticket #{tid} successfully submitted!</b> 📨✨\n\n⏳ <i>Our admin team is reviewing it and will reply directly to this chat soon.</i> 👨‍💻", parse_mode="HTML", reply_markup=main_kb(uid))
    try: bot.send_message(ADMIN_ID, f"🚨 <b>NEW SUPPORT TICKET #{tid}</b> 🚨\nFrom <code>{uid}</code>:\n\n💬 {m.text}", parse_mode="HTML")
    except: pass

@bot.message_handler(func=lambda m: m.text == "🤝 Referral Program 👥")
def h_referral(m):
    uid = m.from_user.id
    u = execute_db("SELECT free_views_credits FROM users WHERE user_id=?", (uid,), fetch=True)
    ref_count = execute_db("SELECT COUNT(*) FROM referrals WHERE referrer_id=?", (uid,), fetch=True)[0]
    link = f"https://t.me/{bot.get_me().username}?start=ref_{uid}"
    msg = (
        f"🤝 <b>VIP REFERRAL REWARDS</b> 🎁💸\n━━━━━━━━━━━━━━━━━━━\n"
        f"Want to grow for completely FREE? Invite your friends! 🚀\n\n"
        f"🔗 <b>Copy & Share Your Unique Link:</b> 👇\n<code>{link}</code>\n\n"
        f"👥 <b>Friends Joined:</b> <code>{ref_count}</code> 🥳\n"
        f"🎁 <b>Free 1K Views Credits Earned:</b> <code>{u[0]}</code> 🌟\n\n"
        f"🚀 <b>HOW THE MAGIC WORKS:</b> 🔮\n"
        f"<i>Every single time a friend starts the bot using your link, you instantly earn a credit for 1,000 Free Views! Tap 'Claim Free 1K Views 🌟' in the menu to spend them!</i> 🔥"
    )
    bot.send_message(m.chat.id, msg, parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text == "🎁 Claim Free 1K Views 🌟")
def h_claim_free(m):
    uid = m.from_user.id
    credits = execute_db("SELECT free_views_credits FROM users WHERE user_id=?", (uid,), fetch=True)[0]
    if credits <= 0: return bot.send_message(m.chat.id, "❌ <b>Oh no! You have 0 Free Credits right now!</b> 😔💔\n\n👥 <i>Share your link from the 'Referral Program' menu with your friends to earn unlimited free views!</i> 🚀", parse_mode="HTML")
    user_states[uid] = {"state": "claim_free_link"}
    bot.send_message(m.chat.id, f"🎁 <b>AWESOME! You currently have {credits} free credit(s) ready to use!</b> 🎉✨\n\n🔗 <b>STEP 1:</b> <i>Paste the public post/video link below where you want to send your 1,000 free views!</i> 👇\n\n⚠️ <i>(Ensure the account is fully PUBLIC!)</i> 🌍", parse_mode="HTML", reply_markup=cancel_kb())

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get("state") == "claim_free_link")
def h_process_free_claim(m):
    uid = m.from_user.id
    credits = execute_db("SELECT free_views_credits FROM users WHERE user_id=?", (uid,), fetch=True)[0]
    if credits <= 0: return bot.send_message(m.chat.id, "❌ <b>No credits remaining.</b> 🛑", reply_markup=main_kb(uid), parse_mode="HTML")
    bot.send_message(m.chat.id, "⏳ <i>Processing your free VIP reward securely...</i> ⚙️🚀", parse_mode="HTML")
    api_res, prov_used = call_provider_api(FREE_VIEWS_PROVIDER, 'add', {'service': FREE_VIEWS_SERVICE_ID, 'link': m.text.strip(), 'quantity': 1000})
    if api_res and 'order' in api_res:
        execute_db("UPDATE users SET free_views_credits = free_views_credits - 1 WHERE user_id=?", (uid,))
        execute_db("INSERT INTO orders (user_id, provider, api_order_id, service_id, quantity, cost, auto_refill) VALUES (?,?,?,?,?,?,0)",
                   (uid, prov_used, api_res['order'], FREE_VIEWS_SERVICE_ID, 1000, 0.0))
        bot.send_message(m.chat.id, f"✅ <b>SUCCESS! 1,000 FREE VIEWS ORDERED!</b> 🎉🔥\n\n🧾 <b>Receipt ID:</b> <code>{api_res['order']}</code> 🆔\n🎁 <b>Credits left:</b> <code>{credits - 1}</code> 🌟\n\n<i>Sit back! Your views will start delivering shortly!</i> 🚀", parse_mode="HTML", reply_markup=main_kb(uid))
    else: bot.send_message(m.chat.id, "❌ <b>Oops! Order failed!</b> 💔\n<i>Please ensure your link is correct and public, then try again. Your credit was NOT deducted.</i> 🔄", parse_mode="HTML", reply_markup=main_kb(uid))
    user_states.pop(uid, None)

@bot.message_handler(func=lambda m: m.text == "🧠 Admin: Smart Sync" and m.from_user.id == ADMIN_ID)
def h_admin_smart_sync(m):
    bot.send_message(ADMIN_ID, "🧠 <i>Initializing Smart Sync... Scanning provider for the absolute best prices and highest-quality services...</i> ⚙️🔎", parse_mode="HTML")
    res, _ = call_provider_api("provider_primary", "services")
    if not res or not isinstance(res, list): return bot.send_message(ADMIN_ID, "❌ <b>CRITICAL: API Connection Failed.</b> 🛑", parse_mode="HTML")
    
    execute_db("DELETE FROM managed_services")
    margin = float(execute_db("SELECT value FROM settings WHERE key='global_margin'", fetch=True)[0])
    
    categories = {}
    for s in res:
        cat_name = s.get('category', 'General')
        if cat_name not in categories: categories[cat_name] = []
        categories[cat_name].append(s)
        
    added_count = 0
    for cat_name, svcs in categories.items():
        cat_lower = cat_name.lower()
        if any(x in cat_lower for x in ['like', 'view', 'share', 'repost', 'story', 'comment']):
            svcs.sort(key=lambda x: float(x.get('rate', 9999)))
            best_svcs = svcs[:2]
        elif any(x in cat_lower for x in ['follower', 'subscriber', 'member']):
            hq_svcs = [x for x in svcs if any(k in x.get('name', '').lower() for k in ['refill', 'guarantee', 'hq', 'real', 'non drop'])]
            if not hq_svcs: hq_svcs = svcs
            hq_svcs.sort(key=lambda x: float(x.get('rate', 0)), reverse=True)
            best_svcs = hq_svcs[-3:]
        else:
            svcs.sort(key=lambda x: float(x.get('rate', 9999)))
            best_svcs = svcs[:1]
            
        for s in best_svcs:
            try:
                execute_db("""INSERT OR REPLACE INTO managed_services 
                    (service_id, category, name, provider, provider_service_id, rate, min_qty, max_qty, margin, disabled) 
                    VALUES (?, ?, ?, 'provider_primary', ?, ?, ?, ?, ?, 0)""",
                    (int(s['service']), cat_name, s['name'], int(s['service']), float(s['rate']), int(s.get('min', 10)), int(s.get('max', 100000)), margin))
                added_count += 1
            except: continue

    bot.send_message(ADMIN_ID, f"✅ <b>SMART SYNC 100% COMPLETE!</b> 🚀🎉\nCleaned up clutter. Added <b>{added_count}</b> highly curated services (Cheapest for views/likes, High Quality for Followers). 📊", parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text == "📈 Admin: Margin" and m.from_user.id == ADMIN_ID)
def h_admin_margin(m):
    user_states[ADMIN_ID] = {"state": "wait_margin"}
    bot.send_message(ADMIN_ID, "📈 <b>ADJUST GLOBAL PROFIT MARGIN</b> 💰\n\nEnter the exact profit percentage you want to make.\n<i>Example: Type <b>50</b> to add exactly 50% profit to all base prices.</i> 🔢👇", parse_mode="HTML", reply_markup=cancel_kb())

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get("state") == "wait_margin" and m.from_user.id == ADMIN_ID)
def h_process_margin(m):
    try:
        pct = float(m.text)
        multiplier = 1.0 + (pct / 100.0)
        execute_db("UPDATE settings SET value=? WHERE key='global_margin'", (str(multiplier),))
        execute_db("UPDATE managed_services SET margin=?", (multiplier,))
        bot.send_message(ADMIN_ID, f"✅ <b>PROFIT MARGIN UPDATED!</b> 💸\nAll prices are now safely marked up by {pct}%. 📈", parse_mode="HTML", reply_markup=main_kb(ADMIN_ID))
    except: bot.send_message(ADMIN_ID, "❌ <b>Error!</b> Type numbers only (e.g. 20, 50). 🛑", parse_mode="HTML")
    user_states.pop(ADMIN_ID, None)

@bot.message_handler(func=lambda m: m.text == "📢 Admin: Broadcast" and m.from_user.id == ADMIN_ID)
def h_admin_broadcast(m):
    user_states[ADMIN_ID] = {"state": "wait_broadcast"}
    bot.send_message(ADMIN_ID, "📢 <b>MASS BROADCAST</b> 🌍\n\nType the message you want to instantly send to all users below: 👇", parse_mode="HTML", reply_markup=cancel_kb())

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get("state") == "wait_broadcast" and m.from_user.id == ADMIN_ID)
def h_process_broadcast(m):
    users = execute_db("SELECT user_id FROM users WHERE is_banned=0", fetch_all=True)
    sent, failed = 0, 0
    for u in users:
        try: bot.send_message(u[0], f"📢 <b>IMPORTANT ANNOUNCEMENT:</b> 🔔\n\n{m.text}", parse_mode="HTML"); sent += 1
        except: failed += 1
    user_states.pop(ADMIN_ID, None)
    bot.send_message(ADMIN_ID, f"✅ <b>Broadcast Complete!</b> 🚀\nSent to {sent} users successfully. ({failed} failed).", parse_mode="HTML", reply_markup=main_kb(ADMIN_ID))

@bot.message_handler(func=lambda m: m.text == "🎫 Admin: Tickets" and m.from_user.id == ADMIN_ID)
def h_admin_view_tickets(m):
    tickets = execute_db("SELECT ticket_id, user_id, message FROM tickets WHERE status='OPEN' LIMIT 5", fetch_all=True)
    if not tickets: return bot.send_message(ADMIN_ID, "✅ <b>Inbox Zero! No open tickets right now.</b> 🎉", parse_mode="HTML")
    for t in tickets: bot.send_message(ADMIN_ID, f"🎫 <b>Ticket #{t[0]}</b> 🚨\nFrom: <code>{t[1]}</code>\n\n💬 {t[2]}", parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text == "💾 Admin: Backup DB" and m.from_user.id == ADMIN_ID)
def handle_admin_backup(m):
    uid = m.from_user.id
    bot.send_message(uid, "⏳ <i>Generating secure, live database snapshot... Please wait...</i> 🔐📁", parse_mode="HTML")
    backup_file = f"backup_{int(time.time())}.db"
    try:
        with db_lock:
            with sqlite3.connect('panel_v14.db') as src, sqlite3.connect(backup_file) as dst: src.backup(dst)
        with open(backup_file, 'rb') as doc:
            bot.send_document(uid, doc, caption="💾 <b>Encrypted Database Backup</b> 🔐✅\n<i>Keep this file safe!</i>", parse_mode="HTML")
    except Exception as e: bot.send_message(uid, f"❌ <b>CRITICAL Backup Failed:</b> <code>{e}</code> 🛑", parse_mode="HTML")
    finally:
        if os.path.exists(backup_file): os.remove(backup_file)

@bot.message_handler(func=lambda m: m.text == "🔄 Admin: Restore DB" and m.from_user.id == ADMIN_ID)
def handle_admin_restore_prompt(m):
    user_states[ADMIN_ID] = {"state": "wait_for_db_upload"}
    bot.send_message(ADMIN_ID, "⚠️ <b>DANGER: DATABASE RESTORE INITIATED</b> ⚠️\n\nPlease upload your valid <code>.db</code> backup file as a document below. 👇", parse_mode="HTML", reply_markup=cancel_kb())

@bot.message_handler(content_types=['document'])
def handle_document_upload(m):
    uid = m.from_user.id
    if uid == ADMIN_ID and user_states.get(uid, {}).get("state") == "wait_for_db_upload":
        if not m.document.file_name.endswith('.db'): return bot.send_message(uid, "❌ <b>Invalid File!</b> Please upload a `.db` file only. 🛑", parse_mode="HTML", reply_markup=main_kb(uid))
        temp_file = f"restore_{int(time.time())}.db"
        bot.send_message(uid, "⏳ <i>Restoring database and overwriting all current data...</i> ⚙️🔄", parse_mode="HTML")
        try:
            downloaded = bot.download_file(bot.get_file(m.document.file_id).file_path)
            with open(temp_file, 'wb') as f: f.write(downloaded)
            with db_lock:
                with sqlite3.connect(temp_file) as src, sqlite3.connect('panel_v14.db') as dst: src.backup(dst)
            bot.send_message(uid, "✅ <b>DATABASE RESTORED SUCCESSFULLY!</b> 🚀🎉\nEverything is back to normal.", parse_mode="HTML", reply_markup=main_kb(uid))
        except Exception as e: bot.send_message(uid, f"❌ <b>CRITICAL Restore Failed:</b> {e} 🛑", parse_mode="HTML", reply_markup=main_kb(uid))
        finally:
            user_states.pop(uid, None)
            if os.path.exists(temp_file): os.remove(temp_file)

@bot.message_handler(func=lambda m: m.text == "🛒 Browse Services 🚀")
def h_browse(m):
    cats = execute_db("SELECT DISTINCT category FROM managed_services WHERE disabled=0", fetch_all=True)
    if not cats: return bot.send_message(m.chat.id, "⚠️ <b>Hold tight! No services are available right now.</b> ⏳\n<i>(Admin needs to click '🧠 Admin: Smart Sync' first!)</i> 🛠️", parse_mode="HTML")
    kb = InlineKeyboardMarkup(row_width=2)
    for idx, c in enumerate(cats): kb.add(InlineKeyboardButton(f"📁 {c[0]}", callback_data=f"c_{idx}"))
    msg = (
        f"🛒 <b>LET'S FIND EXACTLY WHAT YOU NEED!</b> 🔎✨\n\n"
        f"👇 <i>Tap on any category folder below to open our highly curated services menu!</i> 📂"
    )
    bot.send_message(m.chat.id, msg, parse_mode="HTML", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("c_"))
def h_cat_view(c):
    bot.answer_callback_query(c.id)
    idx = int(c.data.split("_")[1])
    cats = execute_db("SELECT DISTINCT category FROM managed_services WHERE disabled=0", fetch_all=True)
    if idx >= len(cats): return bot.send_message(c.message.chat.id, "❌ Category expired.", parse_mode="HTML")
    cat = cats[idx][0]
    svcs = execute_db("SELECT service_id, name, rate, margin FROM managed_services WHERE category=? AND disabled=0", (cat,), fetch_all=True)
    kb = InlineKeyboardMarkup(row_width=1)
    for s in svcs: kb.add(InlineKeyboardButton(f"⭐ {s[1]} - ₹{s[2]*s[3]:.2f}/1k", callback_data=f"b_{s[0]}"))
    kb.add(InlineKeyboardButton("🔙 Back to Main Categories 📂", callback_data="back_cats"))
    msg = (
        f"📂 <b>{html.escape(cat.upper())} SERVICES</b> ✨\n\n"
        f"💰 <i>All prices shown are per 1,000 quantity.</i>\n"
        f"👇 <i>Tap the specific service you want to order right now!</i> 🚀"
    )
    bot.edit_message_text(msg, c.message.chat.id, c.message.message_id, parse_mode="HTML", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data == "back_cats")
def h_back_cats(c):
    bot.answer_callback_query(c.id)
    cats = execute_db("SELECT DISTINCT category FROM managed_services WHERE disabled=0", fetch_all=True)
    kb = InlineKeyboardMarkup(row_width=2)
    for idx, cat in enumerate(cats): kb.add(InlineKeyboardButton(f"📁 {cat[0]}", callback_data=f"c_{idx}"))
    bot.edit_message_text("🛒 <b>LET'S FIND EXACTLY WHAT YOU NEED!</b> 🔎✨\n\n👇 <i>Tap on any category folder below:</i> 📂", c.message.chat.id, c.message.message_id, parse_mode="HTML", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("b_"))
def h_buyinit(c):
    bot.answer_callback_query(c.id)
    sid = int(c.data.split("_")[1])
    user_states[c.from_user.id] = {"state": "get_link", "sid": sid}
    msg = (
        f"🚀 <b>FANTASTIC CHOICE! LET'S DO THIS!</b> 🔥\n\n"
        f"🔗 <b>STEP 1: Send the Target Link</b> 📌\n\n"
        f"💡 <i>Pro Tip: Just paste the exact URL (link to the post/profile/video) below and hit send!</i> 👇\n"
        f"⚠️ <b>WARNING:</b> <i>Make sure the target account is completely PUBLIC!</i> 🌍"
    )
    bot.send_message(c.message.chat.id, msg, parse_mode="HTML", reply_markup=cancel_kb())

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get("state") == "get_link")
def h_link_input(m):
    user_states[m.from_user.id].update({"state": "get_qty", "link": m.text.strip()})
    msg = (
        f"✅ <b>Perfect! Link Captured Securely!</b> 🔗📸\n\n"
        f"🔢 <b>STEP 2: Enter the Quantity</b> 📊\n\n"
        f"💡 <i>Tip: Type a simple number (like 500, 1000, 5000) and press send! No commas or text!</i> 👇"
    )
    bot.send_message(m.chat.id, msg, parse_mode="HTML")

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get("state") == "get_qty")
def h_qty_input(m):
    uid = m.from_user.id
    state = user_states[uid]
    try: qty = int(m.text)
    except: return bot.send_message(m.chat.id, "❌ <b>Oops! Please type a valid NUMBER only!</b> 🔢🛑", parse_mode="HTML")

    prov_name, prov_sid, rate, margin = get_best_provider_for_service(state["sid"])
    cost = (qty / 1000.0) * (rate * margin)

    u_bal = execute_db("SELECT balance FROM users WHERE user_id=?", (uid,), fetch=True)[0]
    if u_bal < cost: 
        return bot.send_message(m.chat.id, f"❌ <b>INSUFFICIENT FUNDS!</b> 😔💔\n\n💰 <b>Required:</b> <code>₹{cost:.2f}</code>\n💵 <b>Your Balance:</b> <code>₹{u_bal:.2f}</code>\n\n👇 <i>Don't worry! Just tap '💳 Add Funds 💸' below to top up instantly!</i> ⚡️", parse_mode="HTML", reply_markup=main_kb(uid))

    bot.send_message(m.chat.id, "⏳ <i>Processing your order securely with the provider... Please hold on...</i> ⚙️🚀", parse_mode="HTML")
    api_res, prov_used = call_provider_api(prov_name, 'add', {'service': prov_sid, 'link': state['link'], 'quantity': qty})
    
    if api_res and 'order' in api_res:
        execute_db("UPDATE users SET balance=balance-?, total_spent=total_spent+? WHERE user_id=?", (cost, cost, uid))
        execute_db("INSERT INTO orders (user_id, provider, api_order_id, service_id, quantity, cost, auto_refill) VALUES (?,?,?,?,?,?,1)",
                   (uid, prov_used, api_res['order'], state["sid"], qty, cost))
        msg = (
            f"✅ <b>BOOM! ORDER SUCCESSFULLY PLACED!</b> 🎉🔥\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"🧾 <b>Provider Receipt ID:</b> <code>{api_res['order']}</code> 🆔\n"
            f"💰 <b>Total Deducted:</b> ₹{cost:.2f} 💵\n"
            f"♻️ <b>Auto-Refill:</b> Enabled & Active 🔄\n\n"
            f"<i>Thank you for choosing us! You can track live status in the '📦 Order History 📜' tab!</i> 🚀"
        )
        bot.send_message(m.chat.id, msg, parse_mode="HTML", reply_markup=main_kb(uid))
    else: 
        bot.send_message(m.chat.id, "❌ <b>Provider Error!</b> 🛑\nThe service might be temporarily busy or down. No money was deducted from your wallet! Please try selecting a different service. 🔄", parse_mode="HTML", reply_markup=main_kb(uid))
    user_states.pop(uid, None)

@bot.message_handler(func=lambda m: m.text == "💳 Add Funds 💸")
def h_add_funds(m):
    user_states[m.from_user.id] = {"state": "fund_amt"}
    msg = (
        f"💸 <b>LET'S TOP UP YOUR WALLET!</b> 🏦✨\n\n"
        f"🔢 <b>STEP 1:</b> <i>Type the exact amount in INR (₹) you want to deposit and press send!</i> 👇\n\n"
        f"⚠️ <i>(Minimum Deposit allowed is:</i> <code>₹{MIN_DEPOSIT}</code><i>)</i>\n"
        f"💡 <i>Example: Just type <b>50</b> and hit send to deposit ₹50!</i> 💵"
    )
    bot.send_message(m.chat.id, msg, parse_mode="HTML", reply_markup=cancel_kb())

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get("state") == "fund_amt")
def h_fund_qr(m):
    try:
        amt = float(m.text)
        if amt < MIN_DEPOSIT: return bot.send_message(m.chat.id, f"🚫 <b>Minimum deposit is <code>₹{MIN_DEPOSIT}</code>! Please try a higher amount.</b> 🛑", parse_mode="HTML")
        user_states[m.from_user.id] = {"state": "fund_ss", "amt": amt}
        qr = f"https://api.qrserver.com/v1/create-qr-code/?size=400x400&data={urllib.parse.quote(f'upi://pay?pa={UPI_ID}&am={amt}&cu=INR')}"
        res = requests.get(qr, timeout=10)
        msg = (
            f"💳 <b>SECURE PAYMENT INSTRUCTIONS</b> 💳🔒\n\n"
            f"📱 <b>STEP 2:</b> <i>Pay EXACTLY</i> <code>₹{amt}</code> <i>using the QR Code above OR copy this UPI ID:</i>\n"
            f"👉 <code>{UPI_ID}</code> 📋\n\n"
            f"📸 <b>STEP 3: Upload Screenshot!</b> 🖼️\n"
            f"<i>After successfully paying, take a clear screenshot of your transaction and send the photo right here in this chat!</i> 👇\n\n"
            f"⏳ <i>I am waiting for your photo...</i> ⏱️"
        )
        bot.send_photo(m.chat.id, BytesIO(res.content), caption=msg, parse_mode="HTML", reply_markup=cancel_kb())
    except: bot.send_message(m.chat.id, "❌ <b>Oops! Please enter a valid number only.</b> 🔢🛑", parse_mode="HTML")

@bot.message_handler(content_types=['photo'])
def h_payment_ss(m):
    uid = m.from_user.id
    if user_states.get(uid, {}).get("state") == "fund_ss":
        amt = user_states[uid]["amt"]
        tx = execute_db("INSERT INTO transactions (user_id, amount, status) VALUES (?, ?, 'PENDING')", (uid, amt), return_id=True)
        kb = InlineKeyboardMarkup().add(
            InlineKeyboardButton("✅ Approve Payment", callback_data=f"ap_{tx}_{uid}_{amt}"),
            InlineKeyboardButton("❌ Reject Fake", callback_data=f"rj_{tx}_{uid}")
        )
        bot.send_photo(ADMIN_ID, m.photo[-1].file_id, caption=f"🚨 <b>NEW DEPOSIT REQUEST!</b> 🚨\n\n👤 <b>User ID:</b> <code>{uid}</code>\n💵 <b>Amount:</b> <code>₹{amt}</code>\n🧾 <b>TXN ID:</b> <code>{tx}</code>", parse_mode="HTML", reply_markup=kb)
        msg = (
            f"✅ <b>SCREENSHOT RECEIVED SUCCESSFULLY!</b> 📸🎉\n\n"
            f"⏳ <i>Please wait a few minutes while our admin team verifies the payment. Your wallet will be updated automatically!</i> 🏦✨"
        )
        bot.send_message(m.chat.id, msg, parse_mode="HTML", reply_markup=main_kb(uid))
        user_states.pop(uid, None)

@bot.callback_query_handler(func=lambda c: c.data.startswith(("ap_", "rj_")))
def h_admin_approval(c):
    bot.answer_callback_query(c.id)
    if c.from_user.id != ADMIN_ID: return
    p = c.data.split("_")
    action, tx, uid = p[0], p[1], p[2]
    if action == "ap":
        amt = float(p[3])
        execute_db("UPDATE users SET balance=balance+? WHERE user_id=?", (amt, uid))
        execute_db("UPDATE transactions SET status='APPROVED' WHERE tx_id=?", (tx,))
        bot.edit_message_caption(f"✅ <b>APPROVED TXN-{tx}</b> | Added ₹{amt} successfully! 💸", c.message.chat.id, c.message.message_id, parse_mode="HTML")
        try: bot.send_message(uid, f"🎉 <b>DEPOSIT APPROVED!</b> 💳🔥\n\n<code>₹{amt}</code> <i>has been successfully added to your wallet! Happy ordering!</i> 🚀", parse_mode="HTML")
        except: pass
    else:
        execute_db("UPDATE transactions SET status='REJECTED' WHERE tx_id=?", (tx,))
        bot.edit_message_caption(f"❌ <b>REJECTED TXN-{tx}</b> 🛑", c.message.chat.id, c.message.message_id, parse_mode="HTML")
        try: bot.send_message(uid, f"❌ <b>DEPOSIT REJECTED!</b> 🛑\n\n<i>Your payment screenshot was rejected by the admin. If you believe this is a mistake, please contact support via the main menu!</i> 📞", parse_mode="HTML")
        except: pass

def auto_refill_and_status_monitor():
    while True:
        try:
            orders = execute_db("SELECT db_id, provider, api_order_id, user_id FROM orders WHERE status IN ('pending', 'In progress', 'Processing')", fetch_all=True)
            if orders:
                for o in orders:
                    res, _ = call_provider_api(o[1], 'status', {'order': o[2]})
                    if res and 'status' in res: execute_db("UPDATE orders SET status=? WHERE db_id=?", (res['status'].capitalize(), o[0]))
            
            refillable = execute_db("SELECT db_id, provider, api_order_id, user_id FROM orders WHERE auto_refill=1 AND status IN ('Completed', 'Partial')", fetch_all=True)
            if refillable:
                for ro in refillable:
                    res, _ = call_provider_api(ro[1], 'refill', {'order': ro[2]})
                    if res and 'refill' in res: execute_db("UPDATE orders SET last_refill_check=CURRENT_TIMESTAMP WHERE db_id=?", (ro[0],))
        except: pass
        time.sleep(300)

if __name__ == '__main__':
    init_database()
    try: bot.remove_webhook(); time.sleep(1)
    except: pass
    threading.Thread(target=lambda: bot.infinity_polling(skip_pending=True, timeout=60), daemon=True).start()
    threading.Thread(target=auto_refill_and_status_monitor, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
