from aiogram import BaseMiddleware
from aiogram.types import Message,Update
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import *
from loader import bot
from ..data.config import CHANNEL_ID, BOT_TOKEN, ADMIN_IDS, DB_NAME
from utils.misc.subscription import checksubscription # type: ignore
from aiogram.filters.callback_data import CallbackData
import sys
import os

# Bu yerda AniSpace papkasini python yo'liga qo'shamiz
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))




class CheckSubCallback(CallbackData,prefix='check'):
    check :bool
class UserCheckMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: Dict[str, Any]
    ) -> bool:
        btn = InlineKeyboardBuilder()
        user = event.from_user
        final_status = True
        print(CHANNEL_ID)  # Bu yerda CHANNEL_ID ni ishlatish kerak
        if CHANNEL_ID:  # CHANNELS o'rniga CHANNEL_ID
            for channel in CHANNEL_ID:  # Bu yerda ham CHANNELS o'rniga CHANNEL_ID
                status = True
                try:
                    status = await checksubscription(user_id=user.id, channel=channel)
                except Exception as e:
                    print(f"Subscription check error: {e}")

                final_status = final_status and status

                try:
                    chat = await bot.get_chat(chat_id=channel)
                    if status:
                        btn.button(text=f"✅ {chat.title}", url=f"{await chat.export_invite_link()}")
                    else:
                        btn.button(text=f"❌ {chat.title}", url=f"{await chat.export_invite_link()}")
                except Exception as e:
                    print(e)
                    pass

            if final_status:
                await handler(event, data)
            else:
                btn.button(
                    text="🔄 Tekshirish",
                    callback_data=CheckSubCallback(check=False)
                )
                btn.adjust(1)
                await event.answer(
                    "Iltimos bot to'liq ishlashi uchun quyidagi kanal(lar)ga obuna bo'ling!",
                    reply_markup=btn.as_markup()
                )
        else:
            await handler(event, data)
