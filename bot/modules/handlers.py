import logging
import httpx
import io
import re
import aiohttp
import logging, html
import wave
import asyncio

from tempfile import NamedTemporaryFile
from datetime import datetime
from aiogram.types import Message, BufferedInputFile
from aiogram.filters import Command
from aiogram import types, F
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

import config
from config import *
from modules.data import get_user_model, log_synthesis, get_stats, get_user_limits, increment_usage
from modules.tts_engine import synthesize_chunk, get_wav_duration

logging.basicConfig(level=logging.INFO)

def get_voice_keyboard(current_model: str, usage_dict: dict = None, limit_max: int = 5, include_back: bool = False, is_admin: bool = False):
    builder = InlineKeyboardBuilder()
    usage_dict = usage_dict or {}
    high_quality = []
    low_quality = []

    for model_key, (clean_label, callback_data, _) in VOICE_CHOICES.items():
        button_text = clean_label
        final_callback = callback_data
        safe_key = model_key.replace(".", "_")
        current_usage = usage_dict.get(safe_key, 0)
        
        if current_usage >= limit_max and not is_admin:
             if model_key == current_model:
                 button_text = f"❌ {clean_label}"
             else:
                 button_text = f"🚫 {clean_label}"
             final_callback = "limit_reached"
        elif model_key == current_model:
            button_text = f"✅ {clean_label}"
        
        button = InlineKeyboardButton(text=button_text, callback_data=final_callback)
        if "high" in model_key:
            high_quality.append(button)
        else:
            low_quality.append(button)

    builder.row(InlineKeyboardButton(text="-- HIGH --", callback_data="none"))
    for i in range(0, len(high_quality), 2):
        builder.row(*high_quality[i:i+2])

    builder.row(InlineKeyboardButton(text="- LOW -", callback_data="none"))
    for i in range(0, len(low_quality), 2):
        builder.row(*low_quality[i:i+2])
    
    if include_back:
        builder.row(InlineKeyboardButton(text="⬅️ Артқа", callback_data="back_to_start"))
    
    return builder

async def get_start_text():
    total_users, total_syntheses = await get_stats()
    text = (
        "Сәлем, байланыста DAUYS! 🎙\n"
        "Лимиттерді тексеру - /limits\n\n"
        "Статистика:\n"
        f"👥 Пайдаланушылар саны: {total_users}\n"
        f"🎧 Барлық синтездер: {total_syntheses}\n\n"
        f"Мәтінді сөйлету үшін дауыс таңдаңыз 👇\n"
    )
    return text

def get_start_keyboard():
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="🎙 Дауыс таңдау", callback_data="show_voices"))
    return builder

@router.message(Command("start"))
async def start_handler(message: Message):
    if message.chat.type != "private":
        return

    text = await get_start_text()
    builder = get_start_keyboard()
    
    await message.answer(text=text, reply_markup=builder.as_markup(), parse_mode="Markdown")

@router.message(Command("info"))
async def info_handler(message: Message):
    if message.chat.type == "supergroup":
        await message.answer("Дауыс Бот - мәтінді таниды және сөйлете алады!\n\nБотты құрастырушы - @davidsuragan")
    elif message.chat.type == "private":
         await message.answer("Бұл-бұл қарапайым бот емес!🔥 Бот мәтінді таниды және сөйлете алады! Маған аудио немесе мәтін жіберіңіз.\n\n /voice - мәтінді синтездеу дауысын таңдау.\n /limits - күнделікті лимиттерді тексеру.\n\nБотты құрастырушы - @davidsuragan")

@router.message(Command("stats"))
async def stats_handler(message: Message):
    total_users, total_syntheses = await get_stats()
    await message.answer(
        f"Бот статистикасы:\n\n"
        f"👥 Пайдаланушылар саны: {total_users}\n"
        f"🎧 Барлық синтездер: {total_syntheses}"
    )

@router.message(Command("limits"))
async def limits_handler(message: Message):
    limits = await get_user_limits(message.from_user.id)
    
    tts_usage_dict = limits["tts_usage_dict"] 
    tts_limit = limits["tts_limit"]
    stt_usage = limits["stt_usage"]
    stt_limit = limits["stt_limit"]
    
    # Таңдалған дауыс пен лимит
    current_model = await get_user_model(message.from_user.id)
    safe_current_model = current_model.replace(".", "_")
    current_model_usage = tts_usage_dict.get(safe_current_model, 0)
    
    # Дауыс атын табу (әдемілеп көрсету үшін)
    voice_label = "Белгісіз"
    for key, (label, _, _) in VOICE_CHOICES.items():
        if key == current_model:
            voice_label = label
            break

    text = (
        "📊 **Сіздің бүгінгі лимиттеріңіз:**\n\n"
        f"🗣 **Мәтін дыбыстау ({voice_label}):** {current_model_usage} / {tts_limit}\n"
        f"   (Басқа дауыстардың лимиті бөлек есептеледі)\n"
        f"   (Макс. ұзындық: {MAX_TEXT_LENGTH} символ)\n\n"
        f"🎙 **Аудионы аудиоға түрлендіру:** {stt_usage} / {stt_limit}\n"
        f"   (Макс. ұзақтық: {MAX_AUDIO_DURATION} секунд)\n\n"
        "Лимиттер күн сайын жаңартылады."
    )
    await message.answer(text, parse_mode="Markdown")

@router.message(Command("voice"))
async def choose_voice(message: Message):
    if message.chat.type != "private":
        return

    current_model = await get_user_model(message.from_user.id)
    limits = await get_user_limits(message.from_user.id)
    usage_dict = limits["tts_usage_dict"]
    limit_max = limits["tts_limit"]

    selected_label = "таңдалмады"
    is_at_limit = False

    is_admin = message.from_user.id in config.ADMIN_IDS
    
    for key, (label, _, _) in VOICE_CHOICES.items():
        if key == current_model:
            selected_label = label
            safe_key = key.replace(".", "_")
            if usage_dict.get(safe_key, 0) >= limit_max and not is_admin:
                is_at_limit = True
            break

    builder = get_voice_keyboard(current_model, usage_dict, limit_max, is_admin=is_admin)
    
    text = f"🎙 **Қазір таңдалған дауыс:** {selected_label}"
    if is_at_limit:
        text += f"\n⚠️ **Ескерту:** Бұл дауыстың бүгінгі лимиті бітті ({limit_max}/{limit_max}). Төменнен басқа дауыс таңдаңыз:"
    elif is_admin:
        text += "\nТөменнен басқа дауыс таңдай аласыз (Лимитсіз):"
    else:
        text += "\nТөменнен басқа дауыс таңдай аласыз:"

    await message.answer(
        text=text,
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )
    
@router.message(F.text, ~F.from_user.is_bot)
async def text_handler(message: Message):
    user_input = message.text or ""
    try:
        processing_message = None
        # Көп рет синтездеу деп шықпауы үшін кішкене кідіріс немесе тексеріс
        processing_message = await message.answer(f"🎧 Синтездеу басталды... ({len(user_input)} символ)")

        for word in forbidden_words:
            if re.search(fr'\b{re.escape(word)}\b', user_input, flags=re.IGNORECASE):
                await message.answer(
                    text=f"❌ Сіздің хабарламаңызда тыйым салынған сөз бар: {word}",
                    reply_to_message_id=message.message_id
                )
                return

        if message.chat.type == "supergroup":
            model_name = "kk_KZ-iseke-x_low.onnx"
        else:
            model_name = await get_user_model(message.from_user.id)

        model_parts = model_name.split(':')
        actual_model = model_parts[0]
        speaker_id = int(model_parts[1]) if len(model_parts) > 1 else None
        
        # Мәтінді бірден дыбыстау
        audio_bytes = await synthesize_chunk(user_input, actual_model, speaker_id)
        
        if not audio_bytes:
            await message.answer("❌ Синтездеу қатесі!")
            return
            
        # Лимитті арттыру
        await increment_usage(message.from_user.id, 'tts', model_name)

        duration = get_wav_duration(audio_bytes)

        now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_title = f"dauys_bot_{now_str}.wav"

        audio_buffer = io.BytesIO(audio_bytes)
        audio_buffer.seek(0)

        voice_file = BufferedInputFile(audio_buffer.read(), filename=file_title)

        await message.answer_audio(
            audio=voice_file,
            title="Аудио",
            performer='@dauys_bot',
            duration=duration,
            caption="🎙️ Сіздің аудиоңыз.\n\n@dauys_bot",
            reply_to_message_id=message.message_id
        )
        
        # Статистиканы жаңарту
        await log_synthesis(message.from_user.id)

    except Exception as e:
        import traceback
        logging.error(f"[text_handler ERROR]: {type(e).__name__}: {e}")
        logging.error(traceback.format_exc())
        await message.answer("⚠️ Қате орын алды.")

    finally:
        if processing_message:
            try:
                await bot.delete_message(chat_id=message.chat.id, message_id=processing_message.message_id)
            except Exception as e:
                logging.warning(f"[text_handler delete_message WARNING]: {e}")

@router.message((F.audio | F.voice), ~F.from_user.is_bot)
async def audio_handler(message: Message):
    processing = None
    temp_path = None

    try:
        duration = message.voice.duration if message.voice else message.audio.duration
        if duration > 30:
            await message.reply(f"❌ Аудио ұзақтығы {duration} сек. 30 секундтан аспау керек!")
            return

        processing = await message.answer("🎧 Аудио өңделуде...")

        tg_file = await bot.get_file(message.voice.file_id if message.voice else message.audio.file_id)
        file_ext = tg_file.file_path.split('.')[-1]

        with NamedTemporaryFile(delete=False, suffix=f".{file_ext}") as temp:
            await bot.download_file(tg_file.file_path, destination=temp)
            temp_path = temp.name

        async with aiohttp.ClientSession() as session:
            with open(temp_path, "rb") as audio_file:
                form = aiohttp.FormData()
                form.add_field("file", audio_file, filename=f"voice.{file_ext}", content_type="application/octet-stream")

                async with session.post(STT_API_URL, data=form) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        text = result.get("text", "").strip()

                        if not text:
                            await message.reply("❌ Ештеңе танылмады.")
                            return

                        # STT лимитін арттыру
                        await increment_usage(message.from_user.id, 'stt')

                        # await message.reply(
                        #     f"🗣 Танылған мәтін:\n<pre>{html.escape(text)}</pre>",
                        #     parse_mode="HTML"
                        # )

                        # 🔁 TTS (Локалды)
                        model_name = await get_user_model(message.from_user.id)
                        model_parts = model_name.split(':')
                        actual_model = model_parts[0]
                        speaker_id = int(model_parts[1]) if len(model_parts) > 1 else None
                        
                        audio_bytes = await synthesize_chunk(text, actual_model, speaker_id)

                        if audio_bytes:
                            # TTS лимитін арттыру
                            await increment_usage(message.from_user.id, 'tts', model_name)
                            
                            duration = get_wav_duration(audio_bytes)
                            now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                            file_title = f"dauys_bot_{now_str}.wav"

                            voice_file = BufferedInputFile(audio_bytes, filename=file_title)

                            await message.reply_audio( 
                                audio=voice_file,
                                title='Аудио',
                                performer="@dauys_bot",
                                duration=duration,
                                caption=f"🗣 Танылған мәтін:\n<pre>{html.escape(text)}</pre>",parse_mode="HTML"
                            )
                            
                            # Статистиканы жаңарту
                            await log_synthesis(message.from_user.id)
                        else:
                            await message.reply("⚠️ Мәтінді TTS-ке жіберу қатесі!")
    except Exception as e:
        logging.error(f"[audio_handler ERROR]: {e}")
        await message.reply("🚫 Ішкі қате орын алды. Әкімшіге хабарлас.")

    finally:
        if processing:
            try:
                await bot.delete_message(chat_id=message.chat.id, message_id=processing.message_id)
            except Exception as e:
                logging.warning(f"[audio_handler delete_message WARNING]: {e}")
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)