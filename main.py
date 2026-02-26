import os
import time
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove, ChatMember
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
from db import record_payment, get_expired_users, mark_notified, get_user_package, add_group_db, get_all_groups

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
SOLANA_WALLET = os.getenv('SOLANA_WALLET')
FAP_PRICE_API = os.getenv('FAP_PRICE_API')
PRICE_CACHE_DURATION = int(os.getenv('PRICE_CACHE_DURATION', '60'))
REFERENCE_PREFIX = os.getenv('REFERENCE_PREFIX', 'WAP')
SLIPPAGE_TOLERANCE = float(os.getenv('SLIPPAGE_TOLERANCE', '0.01'))

# Membership packages and prices from readme
PACKAGES = {
    'starter': {'usd': 100, 'duration': '6 Months', 'days': 180},
    'pro': {'usd': 150, 'duration': '1 Year', 'days': 365},
    'elite': {'usd': 200, 'duration': '2 Years', 'days': 730},
    'lifetime': {'usd': 500, 'duration': 'Lifetime', 'days': 36500}
}

GROUP_IDS = set()

async def add_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat.type in ['group', 'supergroup']:
        add_group_db(chat.id)
        await update.message.reply_text("✅ Group registered for membership management.", reply_markup=main_menu())
    else:
        await update.message.reply_text("❌ This command must be used in a group.", reply_markup=main_menu())

# Button UI for all commands

def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Membership", callback_data='membership')],
        [InlineKeyboardButton("Verify Payment", callback_data='verify')],
        [InlineKeyboardButton("Help", callback_data='help')],
        [InlineKeyboardButton("Cancel", callback_data='cancel')]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome to WAPClub!\n\nSelect an option:",
        reply_markup=main_menu()
    )

async def membership_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("Starter 💎 ($100, 6 Months)", callback_data='starter')],
        [InlineKeyboardButton("Pro 🚀 ($150, 1 Year)", callback_data='pro')],
        [InlineKeyboardButton("Elite 🏆 ($200, 2 Years)", callback_data='elite')],
        [InlineKeyboardButton("Lifetime 👑 ($500, Lifetime)", callback_data='lifetime')],
        [InlineKeyboardButton("⬅️ Back", callback_data='back')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("Select your membership tier:", reply_markup=reply_markup)

async def back_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Main menu:", reply_markup=main_menu())

async def package_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    tier = query.data
    package = PACKAGES[tier]
    fap_price = get_fap_price()
    fap_amount = calculate_fap_amount(package['usd'], fap_price)
    if not fap_amount:
        await query.edit_message_text("❌ Unable to fetch FAP price. Please try again later.")
        return
    reference_id = f"{REFERENCE_PREFIX}-{int(time.time())}-{tier}"
    user_sessions[query.from_user.id] = {
        'tier': tier,
        'reference_id': reference_id,
        'fap_amount': fap_amount
    }
    msg = (
        f"Membership: {tier.capitalize()}\n"
        f"USD Price: ${package['usd']}\n"
        f"Duration: {package['duration']}\n"
        f"Current FAP/USD: ${fap_price:.4f}\n"
        f"Required FAP: {fap_amount}\n"
        f"\nSend FAP to: {SOLANA_WALLET}\n"
        f"Reference ID: {reference_id}\n"
        f"\nAfter payment, click 'Verify Payment' and enter your transaction hash."
    )
    verify_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔎 Verify Payment", callback_data='verify')],
        [InlineKeyboardButton("❓ Help", callback_data='help')],
        [InlineKeyboardButton("❌ Cancel", callback_data='cancel')]
    ])
    await query.edit_message_text(msg, reply_markup=verify_keyboard)

async def verify_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Please send your transaction hash:")
    context.user_data['awaiting_hash'] = True

async def help_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "ℹ️ Help:\n\n1. Select a membership tier.\n2. Send the required FAP to the wallet.\n3. Click 'Verify Payment' and enter your transaction hash.\n4. Bot will verify and grant access.\n\nIf you need support, contact @admin."
    )

async def cancel_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("❌ Transaction cancelled. Start again with /start.")
    context.user_data.clear()

async def handle_hash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('awaiting_hash'):
        return
    tx_hash = update.message.text.strip()
    user_id = update.message.from_user.id
    session = user_sessions.get(user_id)
    if not session:
        await update.message.reply_text("Session expired. Please start again with /start.")
        return
    solana_api = f"https://api.solana.com/transaction/{tx_hash}"  # Replace with actual endpoint
    try:
        resp = requests.get(solana_api)
        tx_data = resp.json()
        paid = False
        amount = 0
        for instr in tx_data.get('instructions', []):
            if instr.get('destination') == SOLANA_WALLET:
                amount = float(instr.get('amount', 0))
                paid = True
                break
        if paid and amount >= session['fap_amount']:
            await update.message.reply_text("✅ Payment verified! Membership activated.")
            package = session['tier']
            duration_days = PACKAGES[package]['days']
            record_payment(user_id, package, tx_hash, duration_days)
            try:
                await update.message.reply_text("You are being added to the club group(s).")
                for group_id in GROUP_IDS:
                    await update.message.bot.unban_chat_member(group_id, user_id)
            except Exception:
                pass
        else:
            await update.message.reply_text("❌ Payment not found or incorrect. Please check your transaction.")
    except Exception:
        await update.message.reply_text("❌ Could not verify payment. Please try again later.")
    context.user_data['awaiting_hash'] = False

async def check_expiry(context: ContextTypes.DEFAULT_TYPE):
    users = get_expired_users()
    now = datetime.utcnow()
    for user_id, package, expires_at, notified in users:
        expires_dt = datetime.fromisoformat(expires_at)
        if notified == 0 and now >= expires_dt:
            try:
                await context.bot.send_message(user_id, f"⏰ Your membership for {package} has expired! You have 1 day grace period before removal. Renew now to stay in the club.")
                mark_notified(user_id)
            except Exception:
                pass
        elif notified == 1 and now >= expires_dt + timedelta(days=1):
            try:
                await context.bot.send_message(user_id, f"❌ Your membership grace period is over. You have been removed from the club.")
                for group_id in GROUP_IDS:
                    await context.bot.ban_chat_member(group_id, user_id)
            except Exception:
                pass

# Schedule expiry check every hour
app.job_queue.run_repeating(check_expiry, interval=3600, first=10)

app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
app.add_handler(CommandHandler('start', start))
app.add_handler(CommandHandler('registergroup', add_group))
app.add_handler(CallbackQueryHandler(membership_button, pattern='^membership$'))
app.add_handler(CallbackQueryHandler(package_selected, pattern='^(starter|pro|elite|lifetime)$'))
app.add_handler(CallbackQueryHandler(verify_button, pattern='^verify$'))
app.add_handler(CallbackQueryHandler(help_button, pattern='^help$'))
app.add_handler(CallbackQueryHandler(cancel_button, pattern='^cancel$'))
app.add_handler(CallbackQueryHandler(back_button, pattern='^back$'))
app.add_handler(MessageHandler(filters.TEXT & filters.ALL, handle_hash))

if __name__ == '__main__':
    app.run_polling()

