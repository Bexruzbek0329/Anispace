import TelegramBot from 'node-telegram-bot-api';
import { createClient } from '@supabase/supabase-js';
import dotenv from 'dotenv';
import { adminCommands } from './commands/admin.js';
import { animeCommands } from './commands/anime.js';
import { userCommands } from './commands/user.js';

dotenv.config();

const bot = new TelegramBot(process.env.BOT_TOKEN, { polling: true });
const supabase = createClient(process.env.SUPABASE_URL, process.env.SUPABASE_ANON_KEY);

// Admin commands
bot.onText(/\/admin/, (msg) => adminCommands.showPanel(bot, msg, supabase));
bot.onText(/\/users/, (msg) => adminCommands.showUsers(bot, msg, supabase));
bot.onText(/\/broadcast/, (msg) => adminCommands.broadcast(bot, msg, supabase));

// Anime commands
bot.onText(/\/addanime/, (msg) => animeCommands.addAnime(bot, msg, supabase));
bot.onText(/\/animelist/, (msg) => animeCommands.listAnimes(bot, msg, supabase));
bot.onText(/\/episodes/, (msg) => animeCommands.showEpisodes(bot, msg, supabase));

// User commands
bot.onText(/\/start/, (msg) => userCommands.start(bot, msg, supabase));
bot.onText(/\/vip/, (msg) => userCommands.checkVip(bot, msg, supabase));

console.log('Bot is running...');