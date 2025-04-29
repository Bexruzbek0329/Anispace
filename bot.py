import asyncio
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters
)
from data.config import CHANNEL_ID, BOT_TOKEN, ADMIN_IDS, DB_NAME

from database import Database

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize database
db = Database("anime_bot.db")

# Conversation states
(ANIME_NAME, ANIME_SEASON, ANIME_EPISODES, ANIME_GENRE, ANIME_LANGUAGE, ANIME_THUMBNAIL,
 SELECT_ANIME_FOR_EPISODE, EPISODE_NUMBER, EPISODE_TITLE, EPISODE_VIDEO) = range(10)

# Subscription check cache with 5-minute expiration
subscription_cache = {}
CACHE_EXPIRY = 300  # 5 minutes in seconds

async def check_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Check if user is subscribed to all required channels"""
    user_id = update.effective_user.id
    current_time = datetime.now().timestamp()
    
    # Check cache
    if user_id in subscription_cache:
        last_check_time, is_subscribed = subscription_cache[user_id]
        if current_time - last_check_time < CACHE_EXPIRY:
            return is_subscribed
    
    try:
        for channel_id in CHANNEL_IDS:
            try:
                member = await context.bot.get_chat_member(chat_id=f"@{channel_id}", user_id=user_id)
                if member.status not in ['member', 'administrator', 'creator']:
                    subscription_cache[user_id] = (current_time, False)
                    return False
            except Exception as e:
                logger.error(f"Error checking subscription for channel {channel_id}: {e}")
                return False
        
        subscription_cache[user_id] = (current_time, True)
        return True
    except Exception as e:
        logger.error(f"Subscription check error: {e}")
        return False

async def subscription_check_middleware(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Middleware to check subscription before processing any command"""
    if update.effective_user.id in ADMIN_IDS:
        return True
        
    is_subscribed = await check_subscription(update, context)
    if not is_subscribed:
        await send_subscription_message(update, context)
        return False
    return True

async def send_subscription_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send subscription requirement message with channel links"""
    keyboard = []
    
    # Add button for each channel
    for channel_id in CHANNEL_IDS:
        keyboard.append([
            InlineKeyboardButton(
                f"📢 {channel_id}",
                url=f"https://t.me/{channel_id}"
            )
        ])
    
    # Add check button
    keyboard.append([
        InlineKeyboardButton("✅ Tekshirish", callback_data="check_subscription")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message = (
        "❗️ Bot funksiyalaridan foydalanish uchun quyidagi kanallarga a'zo bo'ling:\n\n"
        "👉 A'zo bo'lgach \"Tekshirish\" tugmasini bosing!"
    )
    
    if update.callback_query:
        await update.callback_query.message.edit_text(
            message,
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            message,
            reply_markup=reply_markup
        )

async def check_subscription_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle subscription check callback"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    subscription_cache.pop(user_id, None)  # Clear cache for fresh check
    
    is_subscribed = await check_subscription(update, context)
    if is_subscribed:
        await start(update, context)
    else:
        await send_subscription_message(update, context)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command handler"""
    # Add user to database
    user = update.effective_user
    await db.add_user(user.id, user.username, user.first_name, user.last_name)
    
    # Check subscription
    if not await subscription_check_middleware(update, context):
        return
    
    keyboard = [
        ["🎬 Animelar ro'yxati", "🔍 Anime qidirish"],
        ["🌟 VIP", "ℹ️ Bot haqida"]
    ]
    
    if user.id in ADMIN_IDS:
        keyboard.append(["👑 Admin Panel"])
    
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    welcome_text = (
        f"Assalomu alaykum, {user.first_name}!\n\n"
        "🎬 Anime botimizga xush kelibsiz!\n\n"
        "📱 Bot imkoniyatlari:\n"
        "• HD sifatli animelar\n"
        "• O'zbek tilidagi professional tarjimalar\n"
        "• Tezkor yangilanishlar\n"
        "• Qulay interfeys\n\n"
        "🔥 Botdan foydalanish uchun quyidagi tugmalardan foydalaning!"
    )
    
    if update.callback_query:
        await update.callback_query.message.edit_text(
            welcome_text,
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            welcome_text,
            reply_markup=reply_markup
        )

# Error handler
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log errors and send message to user"""
    logger.error(f"Error: {context.error}")
    
    error_message = (
        "❌ Xatolik yuz berdi!\n\n"
        "Iltimos, keyinroq qayta urinib ko'ring yoki admin bilan bog'laning."
    )
    
    try:
        if update.callback_query:
            await update.callback_query.message.reply_text(error_message)
        elif update:
            await update.message.reply_text(error_message)
    except:
        pass

def main():
    """Start the bot"""
    # Create application
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(check_subscription_callback, pattern="^check_subscription$"))
    
    # Add error handler
    application.add_error_handler(error_handler)
    
    # Initialize database and start bot
    async def start_bot():
        await db.init()
        await application.run_polling()
    
    asyncio.run(start_bot())

if __name__ == '__main__':
    main()