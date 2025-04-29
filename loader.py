from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties  # yangi qator
import asyncio

BOT_TOKEN = "7815051544:AAE9l914fO31aOoiQrGm_LauSRGPWEmalW8"

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)  # to'g'rilangan joy
)
dp = Dispatcher()
