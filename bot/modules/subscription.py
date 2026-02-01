from aiogram import BaseMiddleware
from aiogram.types import Message, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import Callable, Any, Dict
from modules.data import get_chat_members

class SubscriptionMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Any],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        if not isinstance(event, Message):
            return await handler(event, data)

        if event.text and event.text.startswith(("/start", "/info","/voice","/limits")):
             return await handler(event, data)

        if event.chat.type == "private":
            role_user = await get_chat_members(event.from_user.id)
            print(role_user)
            if role_user not in ('member', 'owner', 'admin'):
                msg = 'Ботты қолдану үшін, Дәуіт Сұраған арнасына тіркелу қажет!'
                builder = InlineKeyboardBuilder()
                builder.row(InlineKeyboardButton(text="✅Тіркелу", url="https://t.me/davidsuragan"))
                
                return await event.answer(
                    text=msg,
                    reply_markup=builder.as_markup()
                )
        
        return await handler(event, data)
