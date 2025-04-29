import { Telegraf, Markup } from 'telegraf';
import { BOT_TOKEN, CHANNEL_ID, ADMIN_IDS } from './config.js';
import { db } from './database.js';

const bot = new Telegraf(BOT_TOKEN);

// Initialize database
await db.init();

// Start command
bot.command('start', async (ctx) => {
  const user = ctx.from;
  await db.addUser(user.id, user.username, user.first_name, user.last_name);

  const keyboard = Markup.keyboard([
    ['🎬 Animelar ro\'yxati', '🔍 Anime qidirish'],
    ['🌟 VIP', 'ℹ️ Bot haqida']
  ]).resize();

  await ctx.reply(
    `Assalomu alaykum, ${user.first_name}!\n` +
    'Anime botimizga xush kelibsiz!\n\n' +
    '🔥 Bizda eng sara animalar mavjud\n' +
    '🎬 Barcha animalar HD sifatda\n' +
    '🌟 VIP a\'zolar uchun maxsus imkoniyatlar\n\n' +
    'Quyidagi tugmalar orqali botdan foydalaning:',
    keyboard
  );
});

// First, let's create a middleware function that will check subscriptions before any command
async def subscription_middleware(update: Update, context: ContextTypes.DEFAULT_TYPE, next_handler):
    """Middleware to check subscription before processing any command"""
    try:
        # Skip check for admin users
        if update.effective_user.id in ADMIN_IDS:
            return await next_handler(update, context)
            
        # Check subscription
        is_subscribed = await check_subscription(update, context)
        if not is_subscribed:
            await send_subscription_message(update, context)
            return
            
        # If subscribed, proceed to the next handler
        return await next_handler(update, context)
    except Exception as e:
        logger.error(f"Error in subscription middleware: {e}")
        return

# Modify the Application class to add middleware support
class SubscriptionApplication(Application):
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
                    return await subscription_middleware(update, context, original_handler)
                handler.callback = wrapped_handler
                break
                
        return await super().process_update(update)

# Update the main function to use the new Application class
async def main():
    try:
        # Initialize database
        await db.init()

        # Create application with middleware support
        application = SubscriptionApplication.builder().token(BOT_TOKEN).build()
        
        # Add handlers (same as before)
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("admin", admin_panel))
        # ... rest of your handlers ...

        await application.run_polling(allowed_updates=Update.ALL_TYPES, close_loop=False)
    except Exception as e:
        logger.error(f"Error in main: {e}")
    finally:
        if 'scheduler' in locals():
            scheduler.shutdown()

// Anime list command
bot.command('animelist', async (ctx) => {
  const animes = await db.getAllAnime();
  if (!animes.length) {
    return ctx.reply('📭 Hozircha hech qanday anime qo\'shilmagan.');
  }

  const message = '📜 Anime ro\'yxati:\n\n' + 
    animes.map(anime => `• ${anime.name} (Fasl ${anime.season})`).join('\n');

  await ctx.reply(message);
});

// Start the bot
bot.launch();

// Enable graceful stop
process.once('SIGINT', () => bot.stop('SIGINT'));
process.once('SIGTERM', () => bot.stop('SIGTERM'));