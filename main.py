import asyncio
import types
import aiosqlite
import nest_asyncio
import logging
import logging
import sys
import warnings
from middlewares.my_middleware import CheckSubCallback
from ..data.config import CHANNEL_ID, BOT_TOKEN, ADMIN_IDS, DB_NAME

from keep_alive import keep_alive
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters
)
from apscheduler.schedulers.background import BackgroundScheduler
import pytz
from data.config import BOT_TOKEN, CHANNEL_ID, ADMIN_IDS # type: ignore # type: ignore
from database import Database

# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()


# Initialize scheduler
scheduler = BackgroundScheduler(timezone=pytz.timezone('Asia/Tashkent'))
scheduler.start()

logging.info("Bot ishga tushdi")
logger = logging.getLogger(__name__)
logger.error("Nomalum xatolik yuz berdi")
# Initialize database
db = Database("anime_bot.db")

# Subscription check cache with 5-minute expiration
subscription_cache = {}
CACHE_EXPIRY = 5  # 5 minutes in seconds

# Conversation states
(ANIME_NAME, ANIME_SEASON, ANIME_EPISODES, ANIME_GENRE, ANIME_LANGUAGE, ANIME_THUMBNAIL,
 SELECT_ANIME_FOR_EPISODE, EPISODE_NUMBER, EPISODE_TITLE, EPISODE_VIDEO,
 SELECT_ANIME_TO_EDIT, EDIT_FIELD_CHOICE, EDIT_FIELD_VALUE,
 SELECT_ANIME_TO_DELETE, CONFIRM_DELETE, GIVE_VIP_ID, SEND_AD_MESSAGE,
 SEARCH_ANIME) = range(18)

async def custom_warning_handler(message, category, filename, lineno, file=None, line=None):
    logging.warning(f'{filename}:{lineno}: {category.__name__}: {message}')

warnings.showwarning = custom_warning_handler

@dp.callback_query(CheckSubCallback.filter()) # type: ignore
async def check_query(call: types.CallbackQuery):
    print(call, 'call', call.data, 'call data')
    await call.answer(cache_time=0)
    user = call.from_user
    final_status = True
    btn = InlineKeyboardBuilder() # type: ignore

    # Eski xabarni o‘chiramiz
    await call.message.delete()

    if CHANNELS:
        for channel in CHANNELS:
            try:
                status = await check_subscription(user_id=user.id, channel=channel)
                final_status = final_status and status
                chat = await bot.get_chat(chat_id=channel)
                invite_link = await chat.export_invite_link()  # Har safar yangi link yaratamiz
                btn.button(
                    text=f"{'✅' if status else '❌'} {chat.title}",
                    url=invite_link
                )
            except Exception as e:
                print(f"Kanalga kirish yoki linkni olishda xato: {e}")

        if final_status:
            await call.message.answer(
                f"Assalomu alaykum {user.full_name}!\n\n✍🏻 Kino kodini yuboring."
            )
        else:
            btn.button(
                text="🔄 Tekshirish",
                callback_data=CheckSubCallback(check=False)
            )
            btn.adjust(1)
            await call.message.answer(
                text="Iltimos avval barcha kanallarga a’zo bo‘ling!",
                reply_markup=btn.as_markup()
            )
        
async def top_animes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /top command - shows top viewed animes"""
    try:
        if not await subscription_check_middleware(update, context):
            return
            
        top_animes = await db.get_top_animes(10)  # Get top 10 animes
        
        if not top_animes:
            await update.message.reply_text(
                "📭 Hozircha animelar mavjud emas.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_main")
                ]])
            )
            return
            
        message = "🏆 Eng ko'p ko'rilgan TOP 10 animelar:\n\n"
        keyboard = []
        
        for i, anime in enumerate(top_animes, 1):
            message += f"{i}. {anime[1]} - {anime[7]} marta ko'rilgan\n"
            keyboard.append([InlineKeyboardButton(
                f"{anime[1]}",
                callback_data=f"anime_{anime[0]}"
            )])
            
        keyboard.append([InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_main")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(message, reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Error in top animes: {e}")
        await update.message.reply_text(
            "Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_main")
            ]])
        )

async def last_animes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /last command - shows latest added animes"""
    try:
        if not await subscription_check_middleware(update, context):
            return
            
        latest_animes = await db.get_latest_animes(10)  # Get latest 10 animes
        
        if not latest_animes:
            await update.message.reply_text(
                "📭 Hozircha animelar mavjud emas.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_main")
                ]])
            )
            return
            
        message = "🆕 Oxirgi qo'shilgan 10 ta anime:\n\n"
        keyboard = []
        
        for i, anime in enumerate(latest_animes, 1):
            added_date = datetime.strptime(anime[8], '%Y-%m-%d %H:%M:%S')
            date_str = added_date.strftime('%d.%m.%Y')
            message += f"{i}. {anime[1]} - {date_str}\n"
            keyboard.append([InlineKeyboardButton(
                f"{anime[1]}",
                callback_data=f"anime_{anime[0]}"
            )])
            
        keyboard.append([InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_main")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(message, reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Error in last animes: {e}")
        await update.message.reply_text(
            "Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_main")
            ]])
        )

async def random_anime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /rand command - shows a random anime"""
    try:
        if not await subscription_check_middleware(update, context):
            return
            
        anime = await db.get_random_anime()
        
        if not anime:
            await update.message.reply_text(
                "📭 Hozircha animelar mavjud emas.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_main")
                ]])
            )
            return
            
        message = (
            f"🎲 Tasodifiy anime:\n\n"
            f"🎬 {anime[1]}\n"
            f"🔢 Fasli: {anime[2]}\n"
            f"📺 Epizodlar: {anime[3]}\n"
            f"🎭 Janr: {anime[4]}\n"
            f"🗣 Tili: {anime[5]}\n"
            f"👁 Ko'rilgan: {anime[7]} marta"
        )
        
        keyboard = [
            [InlineKeyboardButton("📺 Ko'rish", callback_data=f"anime_{anime[0]}")],
            [InlineKeyboardButton("🎲 Boshqa anime", callback_data="random_anime")],
            [InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=anime[6],
            caption=message,
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Error in random anime: {e}")
        await update.message.reply_text(
            "Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_main")
            ]])
        )       
        
async def process_update(self, update: Update):
        """Override process_update to add middleware"""
        if update.effective_user is None:
            return await super().process_update(update)
            
        # Get the original handler
        handlers = self.handlers.get(update.effective_chat.type, [])
        for handler in handlers:
            check = handler.check_update(update)
            if check is not None and check is not False:
                # Wrap the handler with subscription middleware
                original_handler = handler.callback
                async def wrapped_handler(update, context):
                    return await subscription_middleware(update, context, original_handler) # type: ignore
                handler.callback = wrapped_handler
                break
                
        return await super().process_update(update)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command handler"""
    try:
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
            f"✌️ Yoow Assalomu alaykum, {user.first_name}!\n\n"
            "🎬 Anime botimizga xush kelibsiz!\n\n"
            "📱 Bot imkoniyatlari:\n"
            "• HD sifatli animelar\n"
            "• O'zbek tilidagi professional Dublyajlar\n"
            "• Oʻzbek tilidagi Manga va Manhwalar\n"
            "• Tezkor yangilanishlar\n"
            "• Qulay interfeys\n\n"
            "🔥 Botdan foydalanish uchun quyidagi tugmalardan foydalaning!"
        )
        
        if update.callback_query:
            await update.callback_query.message.delete()
            await update.callback_query.message.chat.send_message(
                welcome_text,
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(
                welcome_text,
                reply_markup=reply_markup
            )
    except Exception as e:
        logger.error(f"Error in start handler: {e}")
        await update.message.reply_text("Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin panel handler"""
    try:
        user_id = update.effective_user.id
        if user_id not in ADMIN_IDS:
            if update.message:
                await update.message.reply_text("⛔️ Bu buyruq faqat adminlar uchun!")
            elif update.callback_query:
                await update.callback_query.message.reply_text("⛔️ Bu buyruq faqat adminlar uchun!")
            return

        keyboard = [
            [InlineKeyboardButton("👥 Foydalanuvchilar", callback_data="users_count"),
             InlineKeyboardButton("🌟 VIP berish", callback_data="give_vip")],
            [InlineKeyboardButton("📢 Reklama yuborish", callback_data="send_ad"),
             InlineKeyboardButton("📊 Statistika", callback_data="stats")],
            [InlineKeyboardButton("➕ Anime qo'shish", callback_data="add_anime"),
             InlineKeyboardButton("📝 Anime tahrirlash", callback_data="edit_anime")],
            [InlineKeyboardButton("🎬 Epizod qo'shish", callback_data="add_episode"),
             InlineKeyboardButton("🗑 Anime o'chirish", callback_data="delete_anime")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        if update.message:
            await update.message.reply_text("🎛 Admin panel:", reply_markup=reply_markup)
        elif update.callback_query:
            await update.callback_query.message.edit_text("🎛 Admin panel:", reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Error in admin panel: {e}")
        if update.message:
            await update.message.reply_text("Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")
        elif update.callback_query:
            await update.callback_query.message.edit_text("Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")

async def users_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Users count handler"""
    try:
        query = update.callback_query
        await query.answer()
        
        count = await db.get_users_count()
        today_count = await db.get_today_users_count()
        
        message = (
            f"👥 Jami foydalanuvchilar: {count}\n"
            f"📅 Bugun qo'shilganlar: {today_count}"
        )
        
        back_button = [[InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_admin")]]
        reply_markup = InlineKeyboardMarkup(back_button)
        
        await query.message.edit_text(message, reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Error in users count: {e}")
        await query.message.edit_text(
            "Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_admin")
            ]])
        )

async def is_user_blocked(user_id):
    # Bloklangan foydalanuvchilar ro‘yxatini tekshirish
    blocked_users = get_blocked_users_from_db()  # type: ignore # yoki boshqa joydan
    return user_id in blocked_users

async def give_vip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Give VIP handler"""
    try:
        query = update.callback_query
        await query.answer()
        
        await query.message.edit_text(
            "🌟 VIP berish uchun foydalanuvchi ID sini kiriting:\n\n"
            "Masalan: 123456789",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_admin")
            ]])
        )
        return GIVE_VIP_ID
    except Exception as e:
        logger.error(f"Error in give VIP: {e}")
        await query.message.edit_text(
            "Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_admin")
            ]])
        )
        return ConversationHandler.END

async def process_vip_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process VIP ID handler"""
    try:
        user_id = int(update.message.text)
        user = await db.get_user(user_id)
        
        if not user:
            await update.message.reply_text(
                "❌ Foydalanuvchi topilmadi!\n\n"
                "Foydalanuvchi avval botdan foydalangan bo'lishi kerak.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_admin")
                ]])
            )
            return ConversationHandler.END
        
        await db.set_vip_status(user_id, True)
        
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text="🎉 Tabriklaymiz! Sizga VIP status berildi!"
            )
        except Exception as e:
            logger.error(f"Error sending VIP notification: {e}")
        
        await update.message.reply_text(
            "✅ VIP status muvaffaqiyatli berildi!",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_admin")
            ]])
        )
    except ValueError:
        await update.message.reply_text(
            "❌ Noto'g'ri ID format! Raqam kiriting.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_admin")
            ]])
        )
    except Exception as e:
        logger.error(f"Error in process VIP ID: {e}")
        await update.message.reply_text(
            "Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_admin")
            ]])
        )
    
    return ConversationHandler.END

async def send_ad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send advertisement handler"""
    try:
        query = update.callback_query
        await query.answer()
        
        # Edit message to prompt for ad content
        await query.message.edit_text(
            "📢 Reklama xabarini yuboring:\n\n"
            "• Matn\n"
            "• Rasm\n"
            "• Video\n"
            "• Havola\n\n"
            "Bo'lishi mumkin!",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_admin")
            ]])
        )
        return SEND_AD_MESSAGE
    except Exception as e:
        logger.error(f"Error in send ad: {e}")
        await query.message.edit_text(
            "Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_admin")
            ]])
        )
        return ConversationHandler.END

async def process_ad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process advertisement handler"""
    try:
        users = await db.get_all_users()
        
        # Log the number of users found
        logger.info(f"Found {len(users)} users in database")
        
        if not users:
            await update.message.reply_text(
                "❌ Foydalanuvchilar ro'yxati bo'sh! Reklama yuborilmadi.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_admin")
                ]])
            )
            return ConversationHandler.END
            
        success = 0
        failed = 0
        blocked = 0
        skipped = 0
        
        # Send initial progress message
        progress_msg = await update.message.reply_text("📤 Reklama yuborilmoqda...")

        blocked_users = []
        failed_users = []
        invalid_users = []

        # Loop over all users
        for user in users:
            # IMPORTANT: Use index 1 for user_id, not index 0
            user_id = user[1]  # This is the correct index for user_id
            
            # Skip obviously invalid user IDs
            if user_id < 10000:
                skipped += 1
                invalid_users.append(str(user_id))
                logger.warning(f"Skipping invalid user ID: {user_id}")
                continue
                
            logger.info(f"Attempting to send message to user {user_id}")
            
            try:
                if update.message.photo:
                    # Send photo
                    await context.bot.send_photo(
                        chat_id=user_id,
                        photo=update.message.photo[-1].file_id,
                        caption=update.message.caption
                    )
                elif update.message.video:
                    # Send video
                    await context.bot.send_video(
                        chat_id=user_id,
                        video=update.message.video.file_id,
                        caption=update.message.caption
                    )
                else:
                    # Send text message
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=update.message.text
                    )
                success += 1
                logger.info(f"Successfully sent message to user {user_id}")

            except Exception as e:
                failed += 1
                error_str = str(e)
                logger.error(f"Failed to send message to user {user_id}: {error_str}")
                
                failed_users.append(f"{user_id}: {error_str}")
                
                if "blocked" in error_str.lower() or "bot was blocked" in error_str.lower():
                    blocked += 1
                    blocked_users.append(str(user_id))
                    logger.warning(f"User {user_id} has blocked the bot")

            # Update progress
            if (success + failed + skipped) % 10 == 0:
                await progress_msg.edit_text(
                    f"📤 Reklama yuborilmoqda...\n\n"
                    f"✅ Yuborildi: {success}\n"
                    f"❌ Xatolik: {failed} (bloklangan: {blocked})\n"
                    f"⏭️ O'tkazib yuborildi: {skipped}\n"
                    f"📊 Progress: {((success + failed + skipped) / len(users) * 100):.1f}%"
                )

        # Final message with stats
        await progress_msg.edit_text(
            f"📊 Reklama yuborish yakunlandi:\n\n"
            f"✅ Muvaffaqiyatli: {success}\n"
            f"❌ Xatolik: {failed}\n"
            f"🚫 Bloklagan foydalanuvchilar: {blocked}\n"
            f"⏭️ O'tkazib yuborildi: {skipped}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_admin")
            ]])
        )

    except Exception as e:
        logger.error(f"Error in process_ad: {e}")
        await update.message.reply_text(
            f"Reklama yuborishda xatolik yuz berdi: {str(e)}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_admin")
            ]])
        )

    return ConversationHandler.END

async def get_all_users(self):
    async with aiosqlite.connect(self.db_name) as db:
        async with db.execute('SELECT user_id, username, first_name FROM users ORDER BY joined_date DESC') as cursor:
            return await cursor.fetchall()

async def test_send_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Test sending a message to a specific user"""
    try:
        # Get the user ID from the command arguments
        args = context.args
        if not args:
            await update.message.reply_text("Please provide a user ID: /test_send USER_ID")
            return
            
        user_id = int(args[0])
        
        # Try to send a test message
        await context.bot.send_message(
            chat_id=user_id,
            text="This is a test message from the admin."
        )
        
        await update.message.reply_text(f"✅ Test message sent successfully to user {user_id}")
    except Exception as e:
        await update.message.reply_text(f"❌ Failed to send test message: {str(e)}")
        
async def get_all_users(self):
    """Get all users from the database"""
    try:
        # Make sure we're getting the user_id field
        result = await self.execute("SELECT user_id FROM users", ())
        
        # Log the result for debugging
        logger.info(f"Retrieved {len(result)} users from database")
        
        # Return the result only if it's not empty
        return result if result else []
    except Exception as e:
        logger.error(f"Error getting users: {e}")
        return []

async def verify_blocked_users(context: ContextTypes.DEFAULT_TYPE):
    """Verify if users marked as blocked are actually blocked"""
    bot = context.bot
    
    # Get list of potentially blocked users
    potential_blocked = get_potential_blocked_users() # type: ignore
    
    for user_id in potential_blocked:
        try:
            # Try to send a silent service message
            await bot.send_chat_action(chat_id=user_id, action="typing")
            
            # If successful, user is not blocked - remove from blocklist
            remove_from_blocklist(user_id) # type: ignore
            logger.info(f"User {user_id} removed from blocklist - not actually blocked")
            
        except Exception as e:
            if "blocked" in str(e).lower():
                # Confirm the user is truly blocked
                logger.info(f"Confirmed: User {user_id} has blocked the bot")
            # Keep other users in the potential list for further verification

async def clean_invalid_users():
    """Remove invalid user IDs from the database"""
    try:
        # Get all users
        users = await db.get_all_users()
        
        # Filter out invalid IDs
        invalid_ids = [user[0] for user in users if user[0] < 10000]
        
        if invalid_ids:
            # Remove invalid users from database
            for user_id in invalid_ids:
                await db.delete_user(user_id)
            
            logger.info(f"Removed {len(invalid_ids)} invalid users from database")
    except Exception as e:
        logger.error(f"Error cleaning invalid users: {e}")
        
async def delete_user(self, user_id):
    """Delete a user from the database"""
    try:
        await self.execute(
            "DELETE FROM users WHERE user_id = ?",
            (user_id,)
        )
        return True
    except Exception as e:
        logger.error(f"Error deleting user {user_id}: {e}")
        return False

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Statistics handler"""
    try:
        query = update.callback_query
        await query.answer()
        
        users_count = await db.get_users_count()
        today_users = await db.get_today_users_count()
        anime_count = await db.get_anime_count()
        episodes_count = await db.get_episodes_count()
        vip_count = await db.get_vip_users_count()
        
        stats_text = (
            f"📊 Bot statistikasi:\n\n"
            f"👥 Jami foydalanuvchilar: {users_count}\n"
            f"📅 Bugun qo'shilganlar: {today_users}\n"
            f"🌟 VIP foydalanuvchilar: {vip_count}\n"
            f"🎬 Jami animelar: {anime_count}\n"
            f"📺 Jami epizodlar: {episodes_count}"
        )
        
        back_button = [[InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_admin")]]
        reply_markup = InlineKeyboardMarkup(back_button)
        
        await query.message.edit_text(stats_text, reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Error in stats: {e}")
        await query.message.edit_text(
            "Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_admin")
            ]])
        )

async def start_add_anime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start add anime handler"""
    try:
        query = update.callback_query
        await query.answer()
        
        await query.message.edit_text(
            "🎬 Yangi anime qo'shish:\n\n"
            "Anime nomini kiriting:",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_admin")
            ]])
        )
        return ANIME_NAME
    except Exception as e:
        logger.error(f"Error in start add anime: {e}")
        await query.message.edit_text(
            "Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_admin")
            ]])
        )
        return ConversationHandler.END

async def anime_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Anime name handler"""
    try:
        context.user_data['anime_name'] = update.message.text
        
        await update.message.reply_text(
            "🔢 Anime faslini kiriting (raqamda):",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_admin")
            ]])
        )
        return ANIME_SEASON
    except Exception as e:
        logger.error(f"Error in anime name: {e}")
        await update.message.reply_text(
            "Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_admin")
            ]])
        )
        return ConversationHandler.END

async def anime_season(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Anime season handler"""
    try:
        season = int(update.message.text)
        if season < 1:
            await update.message.reply_text(
                "❌ Fasl raqami 1 dan katta bo'lishi kerak!",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_admin")
                ]])
            )
            return ANIME_SEASON
        
        context.user_data['anime_season'] = season
        await update.message.reply_text(
            "📺 Epizodlar sonini kiriting:",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_admin")
            ]])
        )
        return ANIME_EPISODES
    except ValueError:
        await update.message.reply_text(
            "❌ Iltimos, raqam kiriting!",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_admin")
            ]])
        )
        return ANIME_SEASON
    except Exception as e:
        logger.error(f"Error in anime season: {e}")
        await update.message.reply_text(
            "Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_admin")
            ]])
        )
        return ConversationHandler.END

async def anime_episodes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Anime episodes handler"""
    try:
        episodes = int(update.message.text)
        if episodes < 1:
            await update.message.reply_text(
                "❌ Epizodlar soni 1 dan katta bo'lishi kerak!",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_admin")
                ]])
            )
            return ANIME_EPISODES
        
        context.user_data['anime_episodes'] = episodes
        await update.message.reply_text(
            "🎭 Anime janrini kiriting:",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_admin")
            ]])
        )
        return ANIME_GENRE
    except ValueError:
        await update.message.reply_text(
            "❌ Iltimos, raqam kiriting!",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_admin")
            ]])
        )
        return ANIME_EPISODES
    except Exception as e:
        logger.error(f"Error in anime episodes: {e}")
        await update.message.reply_text(
            "Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_admin")
            ]])
        )
        return ConversationHandler.END

async def anime_genre(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Anime genre handler"""
    try:
        context.user_data['anime_genre'] = update.message.text
        
        await update.message.reply_text(
            "🗣 Anime tilini kiriting:",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_admin")
            ]])
        )
        return ANIME_LANGUAGE
    except Exception as e:
        logger.error(f"Error in anime genre: {e}")
        await update.message.reply_text(
            "Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_admin")
            ]])
        )
        return ConversationHandler.END

async def anime_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Anime language handler"""
    try:
        context.user_data['anime_language'] = update.message.text
        
        await update.message.reply_text(
            "🖼 Anime rasmini yuboring:",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_admin")
            ]])
        )
        return ANIME_THUMBNAIL
    except Exception as e:
        logger.error(f"Error in anime language: {e}")
        await update.message.reply_text(
            "Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_admin")
            ]])
        )
        return ConversationHandler.END

async def anime_thumbnail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Anime thumbnail handler"""
    try:
        if not update.message.photo:
            await update.message.reply_text(
                "❌ Iltimos, rasm yuboring!",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_admin")
                ]])
            )
            return ANIME_THUMBNAIL
        
        photo = update.message.photo[-1]
        context.user_data['anime_thumbnail'] = photo.file_id
        
        anime_data = context.user_data
        await db.add_anime(
            anime_data['anime_name'],
            anime_data['anime_season'],
            anime_data['anime_episodes'],
            anime_data['anime_genre'],
            anime_data['anime_language'],
            anime_data['anime_thumbnail']
        )
        
        success_message = (
            "✅ Anime muvaffaqiyatli qo'shildi!\n\n"
            f"📺 Nomi: {anime_data['anime_name']}\n"
            f"🔢 Fasli: {anime_data['anime_season']}\n"
            f"📺 Epizodlar: {anime_data['anime_episodes']}\n"
            f"🎭 Janr: {anime_data['anime_genre']}\n"
            f"🗣 Tili: {anime_data['anime_language']}"
        )
        
        await update.message.reply_text(
            success_message,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_admin")
            ]])
        )
        
        # Post to channel
        channel_message = (
            f"🎬 Yangi anime qo'shildi!\n\n"
            f"📺 Nomi: {anime_data['anime_name']}\n"
            f"🔢 Fasli: {anime_data['anime_season']}\n"
            f"📺 Epizodlar: {anime_data['anime_episodes']}\n"
            f"🎭 Janr: {anime_data['anime_genre']}\n"
            f"🗣 Tili: {anime_data['anime_language']}\n\n"
            f"👉 @{context.bot.username}"
        )
        
        try:
            for channel_id in CHANNEL_ID:
                await context.bot.send_photo(
                    chat_id=f"@{channel_id}",
                    photo=anime_data['anime_thumbnail'],
                    caption=channel_message
                )
        except Exception as e:
            logger.error(f"Failed to post to channel: {e}")
        
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error in anime thumbnail: {e}")
        await update.message.reply_text(
            "Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_admin")
            ]])
        )
        return ConversationHandler.END

async def edit_anime_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start edit anime handler"""
    try:
        query = update.callback_query
        await query.answer()
        
        animes = await db.get_all_anime()
        if not animes:
            await query.message.edit_text(
                "❌ Hozircha animelar mavjud emas!",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_admin")
                ]])
            )
            return ConversationHandler.END
        
        keyboard = []
        for anime in animes:
            keyboard.append([InlineKeyboardButton(
                f"{anime[1]} (Fasl {anime[2]})",
                callback_data=f"edit_anime_{anime[0]}"
            )])
        
        keyboard.append([InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_admin")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.edit_text(
            "📝 Tahrirlash uchun animeni tanlang:",
            reply_markup=reply_markup
        )
        return SELECT_ANIME_TO_EDIT
    except Exception as e:
        logger.error(f"Error in edit anime start: {e}")
        await query.message.edit_text(
            "Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_admin")
            ]])
        )
        return ConversationHandler.END

async def select_anime_to_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Select anime to edit handler"""
    try:
        query = update.callback_query
        await query.answer()
        
        anime_id = int(query.data.split('_')[2])
        context.user_data['edit_anime_id'] = anime_id
        
        anime = await db.get_anime(anime_id)
        if not anime:
            await query.message.edit_text(
                "❌ Anime topilmadi!",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_admin")
                ]])
            )
            return ConversationHandler.END
        
        keyboard = [
            [InlineKeyboardButton("📝 Nomini o'zgartirish", callback_data="edit_name")],
            [InlineKeyboardButton("🔢 Faslini o'zgartirish", callback_data="edit_season")],
            [InlineKeyboardButton("📺 Epizodlar sonini o'zgartirish", callback_data="edit_episodes")],
            [InlineKeyboardButton("🎭 Janrini o'zgartirish", callback_data="edit_genre")],
            [InlineKeyboardButton("🗣 Tilini o'zgartirish", callback_data="edit_language")],
            [InlineKeyboardButton("🖼 Rasmini o'zgartirish", callback_data="edit_thumbnail")],
            [InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_admin")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.edit_text(
            f"📝 {anime[1]} (Fasl {anime[2]})\n\n"
            "O'zgartirmoqchi bo'lgan maydonni tanlang:",
            reply_markup=reply_markup
        )
        return EDIT_FIELD_CHOICE
    except Exception as e:
        logger.error(f"Error in select anime to edit: {e}")
        await query.message.edit_text(
            "Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_admin")
            ]])
        )
        return ConversationHandler.END

async def edit_field_value(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Edit field value handler"""
    try:
        query = update.callback_query
        await query.answer()
        
        field = query.data.split('_')[1]
        context.user_data['edit_field'] = field
        
        field_names = {
            'name': 'nomini',
            'season': 'faslini',
            'episodes': 'epizodlar sonini',
            'genre': 'janrini',
            'language': 'tilini',
            'thumbnail': 'rasmini'
        }
        
        if field == 'thumbnail':
            await query.message.edit_text(
                "🖼 Yangi rasmni yuboring:",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_admin")
                ]])
            )
        else:
            await query.message.edit_text(
                f"📝 Yangi {field_names[field]} kiriting:",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_admin")
                ]])
            )
        
        return EDIT_FIELD_VALUE
    except Exception as e:
        logger.error(f"Error in edit field value: {e}")
        await query.message.edit_text(
            "Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_admin")
            ]])
        )
        return ConversationHandler.END

async def process_edit_value(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process edit value handler"""
    try:
        field = context.user_data['edit_field']
        anime_id = context.user_data['edit_anime_id']
        
        anime = await db.get_anime(anime_id)
        if not anime:
            await update.message.reply_text(
                "❌ Anime topilmadi!",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_admin")
                ]])
            )
            return ConversationHandler.END
        
        new_value = update.message.text
        
        if field in ['season', 'episodes']:
            try:
                new_value = int(new_value)
                if new_value < 1:
                    await update.message.reply_text(
                        "❌ Qiymat 1 dan katta bo'lishi kerak!",
                        reply_markup=InlineKeyboardMarkup([[
                            InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_admin")
                        ]])
                    )
                    return EDIT_FIELD_VALUE
            except ValueError:
                await update.message.reply_text(
                    "❌ Iltimos, raqam kiriting!",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_admin")
                    ]])
                )
                return EDIT_FIELD_VALUE
        
        # Update anime with new value
        updated_values = {
            'name': anime[1],
            'season': anime[2],
            'episodes': anime[3],
            'genre': anime[4],
            'language': anime[5],
            'thumbnail': anime[6]
        }
        updated_values[field] = new_value
        
        await db.update_anime(
            anime_id,
            updated_values['name'],
            updated_values['season'],
            updated_values['episodes'],
            updated_values['genre'],
            updated_values['language'],
            updated_values['thumbnail']
        )
        
        success_message = (
            "✅ O'zgartirish muvaffaqiyatli saqlandi!\n\n"
            f"📺 Nomi: {updated_values['name']}\n"
            f"🔢 Fasli: {updated_values['season']}\n"
            f"📺 Epizodlar: {updated_values['episodes']}\n"
            f"🎭 Janr: {updated_values['genre']}\n"
            f"🗣 Tili: {updated_values['language']}"
        )
        
        await update.message.reply_text(
            success_message,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_admin")
            ]])
        )
        
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error in process edit value: {e}")
        await update.message.reply_text(
            "Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_admin")
            ]])
        )
        return ConversationHandler.END

async def process_edit_thumbnail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process edit thumbnail handler"""
    try:
        if not update.message.photo:
            await update.message.reply_text(
                "❌ Iltimos, rasm yuboring!",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_admin")
                ]])
            )
            return EDIT_FIELD_VALUE
        
        anime_id = context.user_data['edit_anime_id']
        anime = await db.get_anime(anime_id)
        if not anime:
            await update.message.reply_text(
                "❌ Anime topilmadi!",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_admin")
                ]])
            )
            return ConversationHandler.END
        
        new_thumbnail = update.message.photo[-1].file_id
        
        await db.update_anime(
            anime_id,
            anime[1],  # name
            anime[2],  # season
            anime[3],  # episodes
            anime[4],  # genre
            anime[5],  # language
            new_thumbnail  # thumbnail
        )
        
        await update.message.reply_text(
            "✅ Rasm muvaffaqiyatli o'zgartirildi!",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_admin")
            ]])
        )
        
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error in process edit thumbnail: {e}")
        await update.message.reply_text(
            "Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_admin")
            ]])
        )
        return ConversationHandler.END

async def delete_anime_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start delete anime handler"""
    try:
        query = update.callback_query
        await query.answer()
        
        animes = await db.get_all_anime()
        if not animes:
            await query.message.edit_text(
                "❌ Hozircha animelar mavjud emas!",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_admin")
                ]])
            )
            return ConversationHandler.END
        
        keyboard = []
        for anime in animes:
            keyboard.append([InlineKeyboardButton(
                f"{anime[1]} (Fasl {anime[2]})",
                callback_data=f"delete_anime_{anime[0]}"
            )])
        
        keyboard.append([InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_admin")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.edit_text(
            "🗑 O'chirish uchun animeni tanlang:",
            reply_markup=reply_markup
        )
        return SELECT_ANIME_TO_DELETE
    except Exception as e:
        logger.error(f"Error in delete anime start: {e}")
        await query.message.edit_text(
            "Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_admin")
            ]])
        )
        return ConversationHandler.END

async def confirm_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirm delete handler"""
    try:
        query = update.callback_query
        await query.answer()
        
        anime_id = int(query.data.split('_')[2])
        context.user_data['delete_anime_id'] = anime_id
        
        anime = await db.get_anime(anime_id)
        if not anime:
            await query.message.edit_text(
                "❌ Anime topilmadi!",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_admin")
                ]])
            )
            return ConversationHandler.END
        
        keyboard = [
            [
                InlineKeyboardButton("✅ Ha", callback_data="confirm_delete_yes"),
                InlineKeyboardButton("❌ Yo'q", callback_data="confirm_delete_no")
            ],
            [InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_admin")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.edit_text(
            f"❗️ Rostdan ham '{anime[1]}' animesini o'chirmoqchimisiz?\n\n"
            "⚠️ Barcha epizodlar ham o'chiriladi!",
            reply_markup=reply_markup
        )
        return CONFIRM_DELETE
    except Exception as e:
        logger.error(f"Error in confirm delete: {e}")
        await query.message.edit_text(
            "Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_admin")
            ]])
        )
        return ConversationHandler.END

async def process_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process delete handler"""
    try:
        query = update.callback_query
        await query.answer()
        
        if query.data == "confirm_delete_yes":
            anime_id = context.user_data['delete_anime_id']
            anime = await db.get_anime(anime_id)
            
            if not anime:
                await query.message.edit_text(
                    "❌ Anime topilmadi!",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_admin")
                    ]])
                )
                return ConversationHandler.END
            
            await db.delete_anime(anime_id)
            
            await query.message.edit_text(
                f"✅ '{anime[1]}' animesi muvaffaqiyatli o'chirildi!",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_admin")
                ]])
            )
        else:
            await query.message.edit_text(
                "❌ Anime o'chirish bekor qilindi!",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_admin")
                ]])
            )
        
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error in process delete: {e}")
        await query.message.edit_text(
            "Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_admin")
            ]])
        )
        return ConversationHandler.END

async def add_episode_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start add episode handler"""
    try:
        query = update.callback_query
        await query.answer()
        
        animes = await db.get_all_anime()
        if not animes:
            await query.message.edit_text(
                "❌ Hozircha animelar mavjud emas!",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_admin")
                ]])
            )
            return ConversationHandler.END
        
        keyboard = []
        for anime in animes:
            keyboard.append([InlineKeyboardButton(
                f"{anime[1]} (Fasl {anime[2]})",
                callback_data=f"select_anime_{anime[0]}"
            )])
        
        keyboard.append([InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_admin")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.edit_text(
            "🎬 Qaysi animega epizod qo'shmoqchisiz?",
            reply_markup=reply_markup
        )
        return SELECT_ANIME_FOR_EPISODE
    except Exception as e:
        logger.error(f"Error in add episode start: {e}")
        await query.message.edit_text(
            "Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_admin")
            ]])
        )
        return ConversationHandler.END

async def select_anime_for_episode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Select anime for episode handler"""
    try:
        query = update.callback_query
        await query.answer()
        
        anime_id = int(query.data.split('_')[2])
        context.user_data['selected_anime_id'] = anime_id
        
        anime = await db.get_anime(anime_id)
        existing_episodes = await db.get_episodes(anime_id)
        
        if not anime:
            await query.message.edit_text(
                "❌ Anime topilmadi!",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_admin")
                ]])
            )
            return ConversationHandler.END
        
        await query.message.edit_text(
            f"🎬 {anime[1]} (Fasl {anime[2]})\n\n"
            f"📺 Mavjud epizodlar: {len(existing_episodes)}/{anime[3]}\n\n"
            "🔢 Yangi epizod raqamini kiriting:",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_admin")
            ]])
        )
        return EPISODE_NUMBER
    except Exception as e:
        logger.error(f"Error in select anime for episode: {e}")
        await query.message.edit_text(
            "Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_admin")
            ]])
        )
        return ConversationHandler.END

async def episode_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Episode number handler"""
    try:
        episode_num = int(update.message.text)
        if episode_num < 1:
            await update.message.reply_text(
                "❌ Epizod raqami 1 dan katta bo'lishi kerak!",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_admin")
                ]])
            )
            return EPISODE_NUMBER
        
        anime_id = context.user_data['selected_anime_id']
        anime = await db.get_anime(anime_id)
        
        if not anime:
            await update.message.reply_text(
                "❌ Anime topilmadi!",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_admin")
                ]])
            )
            return ConversationHandler.END
        
        if episode_num > anime[3]:
            await update.message.reply_text(
                f"❌ Epizod raqami {anime[3]} dan katta bo'lishi mumkin emas!",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_admin")
                ]])
            )
            return EPISODE_NUMBER
        
        existing_episode = await db.get_episode_by_number(anime_id, episode_num)
        if existing_episode:
            await update.message.reply_text(
                "❌ Bu raqamli epizod allaqachon mavjud!",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_admin")
                ]])
            )
            return EPISODE_NUMBER
        
        context.user_data['episode_number'] = episode_num
        await update.message.reply_text(
            "📝 Epizod nomini kiriting:",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_admin")
            ]])
        )
        return EPISODE_TITLE
    except ValueError:
        await update.message.reply_text(
            "❌ Iltimos, raqam kiriting!",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_admin")
            ]])
        )
        return EPISODE_NUMBER
    except Exception as e:
        logger.error(f"Error in episode number: {e}")
        await update.message.reply_text(
            "Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_admin")
            ]])
        )
        return ConversationHandler.END

async def episode_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Episode title handler"""
    try:
        context.user_data['episode_title'] = update.message.text
        
        await update.message.reply_text(
            "🎥 Endi epizod videosini yuboring:",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_admin")
            ]])
        )
        return EPISODE_VIDEO
    except Exception as e:
        logger.error(f"Error in episode title: {e}")
        await update.message.reply_text(
            "Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_admin")
            ]])
        )
        return ConversationHandler.END

async def episode_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Episode video handler"""
    try:
        if not update.message.video:
            await update.message.reply_text(
                "❌ Iltimos, video yuboring!",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_admin")
                ]])
            )
            return EPISODE_VIDEO
        
        video = update.message.video
        anime_id = context.user_data['selected_anime_id']
        episode_num = context.user_data['episode_number']
        episode_title = context.user_data['episode_title']
        
        anime = await db.get_anime(anime_id)
        if not anime:
            await update.message.reply_text(
                "❌ Anime topilmadi!",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_admin")
                ]])
            )
            return ConversationHandler.END
        
        await db.add_episode(anime_id, episode_num, video.file_id, episode_title)
        
        success_message = (
            "✅ Epizod muvaffaqiyatli qo'shildi!\n\n"
            f"🎬 Anime: {anime[1]}\n"
            f"🔢 Epizod: {episode_num}\n"
            f"📝 Nomi: {episode_title}"
        )
        
        await update.message.reply_text(
            success_message,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_admin")
            ]])
        )
        
        # Post to channel
        channel_message = (
            f"🎬 Yangi epizod qo'shildi!\n\n"
            f"📺 Anime: {anime[1]}\n"
            f"🔢 Epizod: {episode_num}\n"
            f"📝 Nomi: {episode_title}\n\n"
            f"👉 Ko'rish uchun botga o'ting: @{context.bot.username}"
        )
        
        try:
            for channel_id in CHANNEL_ID:
                await context.bot.send_photo(
                    chat_id=f"@{channel_id}",
                    photo=anime[6],  # anime thumbnail
                    caption=channel_message
                )
        except Exception as e:
            logger.error(f"Failed to post to channel: {e}")
        
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error in episode video: {e}")
        await update.message.reply_text(
            "Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_admin")
            ]])
        )
        return ConversationHandler.END

async def search_anime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Search anime handler"""
    try:
        if update.callback_query:
            query = update.callback_query
            await query.answer()
            await query.message.edit_text(
                "🔍 Qidirmoqchi bo'lgan anime nomini kiriting:",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_main")
                ]])
            )
        else:
            await update.message.reply_text(
                "🔍 Qidirmoqchi bo'lgan anime nomini kiriting:",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_main")
                ]])
            )
        return SEARCH_ANIME
    except Exception as e:
        logger.error(f"Error in search anime: {e}")
        if update.callback_query:
            await update.callback_query.message.edit_text(
                "Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_main")
                ]])
            )
        else:
            await update.message.reply_text(
                "Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_main")
                ]])
            )
        return ConversationHandler.END

async def process_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process search handler"""
    try:
        search_query = update.message.text.lower()
        animes = await db.search_anime(search_query)
        
        if not animes:
            await update.message.reply_text(
                "❌ Hech narsa topilmadi!\n\n"
                "🔍 Boshqa nom bilan qidirib ko'ring.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔍 Qayta qidirish", callback_data="search_anime"),
                    InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_main")
                ]])
            )
            return ConversationHandler.END
        
        message = "🔍 Qidiruv natijalari:\n\n"
        keyboard = []
        
        for anime in animes:
            message += f"• {anime[1]} (Fasl {anime[2]})\n"
            keyboard.append([InlineKeyboardButton(
                f"{anime[1]}",
                callback_data=f"anime_{anime[0]}"
            )])
        
        keyboard.append([
            InlineKeyboardButton("🔍 Qayta qidirish", callback_data="search_anime"),
            InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_main")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(message, reply_markup=reply_markup)
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error in process search: {e}")
        await update.message.reply_text(
            "Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_main")
            ]])
        )
        return ConversationHandler.END

async def anime_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Anime list handler"""
    try:
        animes = await db.get_all_anime()
        if not animes:
            message =  "📭 Hozircha hech qanday anime qo'shilmagan."
            if isinstance(update, Update):
                if update.message:
                    await update.message.reply_text(
                        message,
                        reply_markup=InlineKeyboardMarkup([[
                            InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_main")
                        ]])
                    )
                elif update.callback_query:
                    await update.callback_query.message.edit_text(
                        message,
                        reply_markup=InlineKeyboardMarkup([[
                            InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_main")
                        ]])
                    )
            else:
                await update.edit_message_text(
                    message,
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_main")
                    ]])
                )
            return

        message = "📜 Anime ro'yxati:\n\n"
        keyboard = []

        for anime in animes:
            message += f"• {anime[1]} (Fasl {anime[2]})\n"
            keyboard.append([InlineKeyboardButton(
                f"{anime[1]}",
                callback_data=f"anime_{anime[0]}"
            )])

        keyboard.append([InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_main")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if isinstance(update, Update):
            if update.message:
                await update.message.reply_text(message, reply_markup=reply_markup)
            elif update.callback_query:
                await update.callback_query.message.edit_text(message, reply_markup=reply_markup)
        else:
            await update.edit_message_text(message, reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Error in anime list: {e}")
        if isinstance(update, Update):
            if update.message:
                await update.message.reply_text(
                    "Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_main")
                    ]])
                )
            elif update.callback_query:
                await update.callback_query.message.edit_text(
                    "Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_main")
                    ]])
                )
        else:
            await update.edit_message_text(
                "Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_main")
                ]])
            )

async def check_vip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check VIP status handler"""
    try:
        user_id = update.effective_user.id
        is_vip = await db.get_vip_status(user_id)
        
        if is_vip:
            message = (
                "🌟 VIP Status\n\n"
                "✅ Siz VIP foydalanuvchisiz!\n\n"
                "📋 VIP imkoniyatlari:\n"
                "• Reklamasiz ko'rish\n"
                "• Yuqori tezlik\n"
                "• Maxsus kontent\n"
                "• 24/7 qo'llab-quvvatlash"
            )
        else:
            message = (
                "🌟 VIP Status\n\n"
                "❌ Sizda VIP maqomi yo'q.\n\n"
                "📋 VIP imkoniyatlari:\n"
                "• Reklamasiz ko'rish\n"
                "• Yuqori tezlik\n"
                "• Maxsus kontent\n"
                "• 24/7 qo'llab-quvvatlash\n\n"
                "💳 VIP olish uchun admin bilan bog'laning: @beka_lls"
            )
        
        await update.message.reply_text(
            message,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_main")
            ]])
        )
    except Exception as e:
        logger.error(f"Error in check VIP: {e}")
        await update.message.reply_text(
            "Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_main")
            ]])
        )

async def clean_database(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to clean the database of invalid user IDs"""
    try:
        if update.effective_user.id not in ADMIN_IDS:
            await update.message.reply_text("⛔️ Bu buyruq faqat adminlar uchun!")
            return
            
        # Get all users
        users = await db.get_all_users()
        
        # Count before cleaning
        total_before = len(users)
        
        # Find suspicious user IDs (typically less than 10000000)
        suspicious_ids = [user[0] for user in users if user[0] < 10000000]
        
        if not suspicious_ids:
            await update.message.reply_text("✅ Bazada shubhali foydalanuvchi IDlari topilmadi.")
            return
            
        # Remove suspicious IDs from database
        removed_count = 0
        for user_id in suspicious_ids:
            await db.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
            removed_count += 1
            
        # Get updated count
        users_after = await db.get_all_users()
        total_after = len(users_after)
        
        await update.message.reply_text(
            f"🧹 Baza tozalandi:\n\n"
            f"Oldin: {total_before} foydalanuvchi\n"
            f"O'chirildi: {removed_count} noto'g'ri ID\n"
            f"Hozir: {total_after} foydalanuvchi"
        )
        
    except Exception as e:
        logger.error(f"Error cleaning database: {e}")
        await update.message.reply_text(f"❌ Xatolik yuz berdi: {str(e)}")
        
async def add_user(self, user_id, username, first_name, last_name):
    """Add a new user to the database with validation"""
    try:
        # Validate user ID (Telegram IDs are typically large numbers)
        if user_id < 10000000:
            logger.warning(f"Suspicious user ID detected: {user_id}")
            return False
            
        # Check if user already exists
        existing = await self.execute(
            "SELECT user_id FROM users WHERE user_id = ?",
            (user_id,)
        )
        
        if existing:
            # User already exists, update their info
            await self.execute(
                "UPDATE users SET username = ?, first_name = ?, last_name = ?, last_active = CURRENT_TIMESTAMP WHERE user_id = ?",
                (username, first_name, last_name, user_id)
            )
        else:
            # Add new user
            await self.execute(
                "INSERT INTO users (user_id, username, first_name, last_name, joined_date, last_active) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
                (user_id, username, first_name, last_name)
            )
        return True
    except Exception as e:
        logger.error(f"Error adding user: {e}")
        return False

async def check_database_health():
    """Check database health and fix issues"""
    try:
        # Get all users
        users = await db.get_all_users()
        
        # Find suspicious user IDs
        suspicious_ids = [user[0] for user in users if user[0] < 10000000]
        
        if suspicious_ids:
            logger.warning(f"Found {len(suspicious_ids)} suspicious user IDs in database")
            
            # Remove suspicious IDs
            for user_id in suspicious_ids:
                await db.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
                
            logger.info(f"Removed {len(suspicious_ids)} invalid user IDs from database")
    except Exception as e:
        logger.error(f"Error checking database health: {e}")
        


async def about_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """About bot handler"""
    try:
        message = (
            "ℹ️ Bot haqida:\n\n"
            "🤖 Anime Bot - bu eng sara animalarni o'zbek tilida tomosha qilish uchun yaratilgan bot.\n\n"
            "📺 Bizda:\n"
            "• HD sifatli animelar\n"
            "• O'zbek tilidagi professional tarjimalar\n"
            "• Tezkor yangilanishlar\n"
            "• Qulay interfeys\n\n"
            "👨‍💻 Dasturchi: @beka_lls\n"
            "📢 Kanal: @" + CHANNEL_ID[0]
        )
        
        await update.message.reply_text(
            message,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_main")
            ]])
        )
    except Exception as e:
        logger.error(f"Error in about bot: {e}")
        await update.message.reply_text(
            "Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_main")
            ]])
        )

# For APScheduler to work with async functions
def run_async(func):
    def wrapper(*args, **kwargs):
        loop = asyncio.new_event_loop()
        return loop.run_until_complete(func(*args, **kwargs))
    return wrapper

# Schedule the wrapped function
scheduler.add_job(run_async(check_database_health), 'interval', days=1)

async def setup_scheduler_jobs():
    """Set up scheduled jobs"""
    try:
        # Add the database health check job
        scheduler.add_job(check_database_health, 'interval', days=1)
        logger.info("Scheduled database health check job")
    except Exception as e:
        logger.error(f"Error setting up scheduler jobs: {e}")

# Call this function before starting the bot
setup_scheduler_jobs()

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Button handler"""
    try:
        query = update.callback_query
        await query.answer()
        
        if query.data == "back_to_admin":
            await admin_panel(update, context)
            return
        
        if query.data == "back_to_main":
            await start(update, context)
            return
        
        if query.data.startswith("anime_"):
            anime_id = int(query.data.split("_")[1])
            anime = await db.get_anime(anime_id)
            episodes = await db.get_episodes(anime_id)
            
            if not anime:
                await query.message.edit_text(
                    "❌ Anime topilmadi.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_main")
                    ]])
                )
                return

            message = (
                f"🎬 {anime[1]}\n"
                f"🔢 Fasli: {anime[2]}\n"
                f"📺 Epizodlar: {anime[3]}\n"
                f"🎭 Janr: {anime[4]}\n"
                f"🗣 Tili: {anime[5]}\n\n"
                f"📺 Barcha epizodlar:"
            )

            keyboard = []
            for episode in episodes:
                keyboard.append([InlineKeyboardButton(
                    f"{episode[2]}-qism: {episode[4]}",
                    callback_data=f"watch_{episode[0]}"
                )])
            
            keyboard.append([InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_list")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.message.delete()
            await context.bot.send_photo(
                chat_id=query.message.chat_id,
                photo=anime[6],
                caption=message,
                reply_markup=reply_markup
            )
            
            # Increment views
            await db.increment_anime_views(anime_id)
        
        elif query.data.startswith("watch_"):
            episode_id = int(query.data.split("_")[1])
            episode = await db.get_episode(episode_id)
            
            if not episode:
                await query.message.edit_text(
                    "❌ Epizod topilmadi.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_main")
                    ]])
                )
                return
            
            anime = await db.get_anime(episode[1])
            if not anime:
                await query.message.edit_text(
                    "❌ Anime topilmadi.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_main")
                    ]])
                )
                return
            
            caption = (
                f"🎬 {anime[1]}\n"
                f"📺 {episode[2]}-qism: {episode[4]}"
            )
            
            # Check if user is VIP
            user_id = query.from_user.id
            is_vip = await db.get_vip_status(user_id)
            
            if not is_vip:
                # Add watermark for non-VIP users
                caption += "\n\n💫 VIP bo'ling va reklamasiz ko'ring!"
            
            await context.bot.send_video(
                chat_id=query.message.chat_id,
                video=episode[3],
                caption=caption
            )
            
            # Increment views
            await db.increment_episode_views(episode_id)
        
        elif query.data == "back_to_list":
            await anime_list(update, context)
    except Exception as e:
        logger.error(f"Error in button handler: {e}")
        if query.message:
            await query.message.edit_text(
                "Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_main")
                ]])
            )

# Updated conversation handlers with per_chat=True instead of per_message
anime_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(start_add_anime, pattern='^add_anime$')],
    states={
        ANIME_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, anime_name)],
        ANIME_SEASON: [MessageHandler(filters.TEXT & ~filters.COMMAND, anime_season)],
        ANIME_EPISODES: [MessageHandler(filters.TEXT & ~filters.COMMAND, anime_episodes)],
        ANIME_GENRE: [MessageHandler(filters.TEXT & ~filters.COMMAND, anime_genre)],
        ANIME_LANGUAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, anime_language)],
        ANIME_THUMBNAIL: [MessageHandler(filters.PHOTO & ~filters.COMMAND, anime_thumbnail)]
    },
    fallbacks=[CommandHandler('cancel', lambda u, c: ConversationHandler.END)],
    per_chat=True
)

episode_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(add_episode_start, pattern='^add_episode$')],
    states={
        SELECT_ANIME_FOR_EPISODE: [CallbackQueryHandler(select_anime_for_episode, pattern='^select_anime_')],
        EPISODE_NUMBER: [MessageHandler(filters.TEXT & ~filters.COMMAND, episode_number)],
        EPISODE_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, episode_title)],
        EPISODE_VIDEO: [MessageHandler(filters.VIDEO & ~filters.COMMAND, episode_video)]
    },
    fallbacks=[CommandHandler('cancel', lambda u, c: ConversationHandler.END)],
    per_chat=True
)

vip_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(give_vip, pattern='^give_vip$')],
    states={
        GIVE_VIP_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_vip_id)]
    },
    fallbacks=[CommandHandler('cancel', lambda u, c: ConversationHandler.END)],
    per_chat=True
)

ad_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(send_ad, pattern='^send_ad$')],
    states={
        SEND_AD_MESSAGE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, process_ad),
            MessageHandler(filters.PHOTO & ~filters.COMMAND, process_ad),
            MessageHandler(filters.VIDEO & ~filters.COMMAND, process_ad)
        ]
    },
    fallbacks=[CommandHandler('cancel', lambda u, c: ConversationHandler.END)],
    per_chat=True
)

search_conv_handler = ConversationHandler(
    entry_points=[
        MessageHandler(filters.Regex("^🔍 Anime qidirish$"), search_anime),
        CallbackQueryHandler(search_anime, pattern='^search_anime$')
    ],
    states={
        SEARCH_ANIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_search)]
    },
    fallbacks=[CommandHandler('cancel', lambda u, c: ConversationHandler.END)],
    per_chat=True
)

edit_anime_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(edit_anime_start, pattern='^edit_anime$')],
    states={
        SELECT_ANIME_TO_EDIT: [
            CallbackQueryHandler(select_anime_to_edit, pattern='^edit_anime_')
        ],
        EDIT_FIELD_CHOICE: [
            CallbackQueryHandler(edit_field_value, pattern='^edit_')
        ],
        EDIT_FIELD_VALUE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, process_edit_value),
            MessageHandler(filters.PHOTO & ~filters.COMMAND, process_edit_thumbnail)
        ]
    },
    fallbacks=[CommandHandler('cancel', lambda u, c: ConversationHandler.END)],
    per_chat=True
)

delete_anime_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(delete_anime_start, pattern='^delete_anime$')],
    states={
        SELECT_ANIME_TO_DELETE: [
            CallbackQueryHandler(confirm_delete, pattern='^delete_anime_')
        ],
        CONFIRM_DELETE: [
            CallbackQueryHandler(process_delete, pattern='^confirm_delete_')
        ]
    },
    fallbacks=[CommandHandler('cancel', lambda u, c: ConversationHandler.END)],
    per_chat=True
)

async def main():
    """Start the bot"""
    try:
        # Initialize database
        await db.init()

        # Create application
        application = Application.builder().token(BOT_TOKEN).build()


        # Add handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("admin", admin_panel))
        application.add_handler(CommandHandler("animelist", anime_list))
        application.add_handler(CommandHandler("clean_db", clean_database))
        application.add_handler(CommandHandler("test_send", test_send_message))
        application.add_handler(CommandHandler("top", top_animes))
        application.add_handler(CommandHandler("last", last_animes))
        application.add_handler(CommandHandler("rand", random_anime))
        application.add_handler(CommandHandler("vip", check_vip))


        application.add_handler(MessageHandler(filters.Regex("^🎬 Animelar ro'yxati$"), anime_list))
        application.add_handler(MessageHandler(filters.Regex("^🌟 VIP$"), check_vip))
        application.add_handler(MessageHandler(filters.Regex("^ℹ️ Bot haqida$"), about_bot))
        application.add_handler(MessageHandler(filters.Regex("^👑 Admin Panel$"), admin_panel))

        application.add_handler(anime_conv_handler)
        application.add_handler(episode_conv_handler)
        application.add_handler(vip_conv_handler)
        application.add_handler(ad_conv_handler)
        application.add_handler(search_conv_handler)
        application.add_handler(edit_anime_handler)
        application.add_handler(delete_anime_handler)

        application.add_handler(CallbackQueryHandler(users_count, pattern="^users_count$"))
        application.add_handler(CallbackQueryHandler(stats, pattern="^stats$"))
        application.add_handler(CallbackQueryHandler(check_subscription_callback, pattern="^check_subscription$"))
        application.add_handler(CallbackQueryHandler(random_anime, pattern="^random_anime$"))
        application.add_handler(CallbackQueryHandler(button_handler))

        # Faqat bitta bu qolsin!
        await application.run_polling(allowed_updates=Update.ALL_TYPES, close_loop=False)

    except Exception as e:
        logger.error(f"Error in main: {e}")
    finally:
        if 'scheduler' in locals():
            scheduler.shutdown()
            
if __name__ == '__main__':
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
        if 'scheduler' in locals():
            scheduler.shutdown()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        if 'scheduler' in locals():
            scheduler.shutdown()

import logging

# Formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# INFO va undan yuqori loglar uchun fayl handler
info_handler = logging.FileHandler("bot_info.log", encoding='utf-8')
info_handler.setLevel(logging.INFO)
info_handler.setFormatter(formatter)

# ERROR va undan yuqori loglar uchun alohida handler
error_handler = logging.FileHandler("bot_errors.log", encoding='utf-8')
error_handler.setLevel(logging.ERROR)
error_handler.setFormatter(formatter)

# Root logger
root_logger = logging.getLogger()
root_logger.handlers.clear()
root_logger.setLevel(logging.INFO)
root_logger.addHandler(info_handler)
root_logger.addHandler(error_handler)

# Boshqa modullar uchun (ixtiyoriy)
for module_name in ['apscheduler', 'httpx', 'telegram.ext']:
    logger = logging.getLogger(module_name)
    logger.setLevel(logging.INFO)
    logger.addHandler(info_handler)
    logger.addHandler(error_handler)

keep_alive()