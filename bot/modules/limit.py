from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message
import config
from modules.data import check_user_limit, increment_usage, get_user_model

class LimitMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        # Егер бұл хабарлама (Message) болмаса, өткізе береміз
        if not isinstance(event, Message):
            return await handler(event, data)

        user = data.get("event_from_user")
        
        if not user:
            return await handler(event, data)
        
        # Админ тексеісі (ID бойынша)
        if user.id in config.ADMIN_IDS:
            return await handler(event, data)

        # Командаларды лимитке санамаймыз
        if event.text and event.text.startswith("/"):
            return await handler(event, data)

        limit_type = None

        # 1. Тексеру: Мәтін (TTS)
        if event.text:
            limit_type = 'tts'
            if len(event.text) > config.MAX_TEXT_LENGTH:
                 await event.answer(f"❌ Мәтін {config.MAX_TEXT_LENGTH} символдан аспауы керек!")
                 return

        # 2. Тексеру: Аудио/Войс (STT)
        elif event.voice or event.audio:
            limit_type = 'stt'
            duration = event.voice.duration if event.voice else event.audio.duration
            if duration > config.MAX_AUDIO_DURATION:
                await event.answer(f"❌ Аудио {config.MAX_AUDIO_DURATION} секундтан аспауы керек!")
                return
        
        # Егер басқа тип болса (сурет т.б.), лимитсіз өткіземіз(немесе кейін қосамыз)
        if not limit_type:
             return await handler(event, data)

        model_name = None
        if limit_type == 'tts':
             if event.chat.type == "supergroup":
                 model_name = "kk_KZ-iseke-x_low.onnx"
             else:
                 model_name = await get_user_model(user.id)

        # Лимитті тексеру
        has_limit = await check_user_limit(user.id, limit_type, model_name)
        
        if not has_limit:
            limit_val = config.DAILY_TTS_LIMIT if limit_type == 'tts' else config.DAILY_STT_LIMIT
            
            voice_label = "осы дауыспен"
            if limit_type == 'tts' and model_name:
                for key, (label, _, _) in config.VOICE_CHOICES.items():
                    if key == model_name:
                        voice_label = f"<b>{label}</b> дауысымен"
                        break
            
            limit_name = f"{voice_label} мәтін дыбыстау" if limit_type == 'tts' else "аудио тану"
            await event.answer(
                f"❌ Сіздің бүгінгі {limit_name} лимитіңіз бітті ({limit_val}/{limit_val}).\n\n"
                f"Бұл дауыс бойынша бүгінгі мүмкіндік таусылды. Басқа дауыс таңдап көріңіз: /voice",
                parse_mode="HTML"
            )
            return

        return await handler(event, data)
