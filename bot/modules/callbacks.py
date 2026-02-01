from aiogram.types import CallbackQuery
import config
from config import router, VOICE_CHOICES
from modules.data import set_user_model, get_user_limits

@router.callback_query()
async def voice_callback(callback: CallbackQuery):
    from modules.handlers import get_voice_keyboard, get_user_model, get_start_text, get_start_keyboard, VOICE_CHOICES

    if callback.data == "show_voices":
        current_model = await get_user_model(callback.from_user.id)
        limits = await get_user_limits(callback.from_user.id)
        usage_dict = limits["tts_usage_dict"]
        limit_max = limits["tts_limit"]

        selected_label = "таңдалмады"
        is_at_limit = False
        
        for key, (label, _, _) in VOICE_CHOICES.items():
            if key == current_model:
                selected_label = label
                safe_key = key.replace(".", "_")
                if usage_dict.get(safe_key, 0) >= limit_max and callback.from_user.id not in config.ADMIN_IDS:
                    is_at_limit = True
                break
        
        is_admin = callback.from_user.id in config.ADMIN_IDS
        builder = get_voice_keyboard(current_model, usage_dict, limit_max, include_back=True, is_admin=is_admin)
        
        text = f"🎙 **Қазір таңдалған дауыс:** {selected_label}"
        if is_at_limit:
            text += f"\n⚠️ **Лимит бітті:** Бүгінгі мүмкіндік таусылды ({limit_max}/{limit_max}). Басқасын таңдаңыз:"
        else:
            text += "\nТөменнен басқа дауыс таңдаңыз:"

        await callback.message.edit_text(
            text=text,
            reply_markup=builder.as_markup(),
            parse_mode="Markdown"
        )
        await callback.answer()
        return

    if callback.data == "back_to_start":
        text = await get_start_text()
        builder = get_start_keyboard()
        await callback.message.edit_text(
            text=text,
            reply_markup=builder.as_markup(),
            parse_mode="Markdown"
        )
        await callback.answer()
        return

    if callback.data == "none":
        await callback.answer()
        return

    if callback.data == "limit_reached":
        if callback.from_user.id in config.ADMIN_IDS:
            # Админдерге лимит болса да өте береді, бірақ біз оны бастырмаймыз (батырма ауысу керек)
            pass
        else:
            await callback.answer("❌ Бұл дауыстың бүгінгі лимиті біткен. Ертең келіңіз немесе басқа дауыс таңдаңыз.", show_alert=True)
            return
        
    selected_voice = callback.data
    model_name = None
    voice_label = None

    for m_name, (label, cb_data, emoji) in VOICE_CHOICES.items():
        if cb_data == selected_voice:
            model_name = m_name
            voice_label = label
            break

    if model_name:
        await set_user_model(callback.from_user.id, model_name)
        
        limits = await get_user_limits(callback.from_user.id)
        usage_dict = limits["tts_usage_dict"]
        limit_max = limits["tts_limit"]
        
        has_back = False
        if callback.message.reply_markup:
            for row in callback.message.reply_markup.inline_keyboard:
                for button in row:
                    if button.callback_data == "back_to_start":
                        has_back = True
                        break
        
        is_admin = callback.from_user.id in config.ADMIN_IDS
        builder = get_voice_keyboard(model_name, usage_dict, limit_max, include_back=has_back, is_admin=is_admin)
        
        safe_key = model_name.replace(".", "_")
        current_usage = usage_dict.get(safe_key, 0)
        
        status_text = f"✅ {voice_label} - дауысы сәтті таңдалды!"
        if current_usage >= limit_max and callback.from_user.id not in config.ADMIN_IDS:
             status_text = f"❌ {voice_label} таңдалды, бірақ лимит біткен!"

        await callback.message.edit_text(
            text=f"{status_text}\n\n🎙 **Қазіргі дауыс:** {voice_label}\nТөменнен өгерте аласыз немесе артқа қайтыңыз:",
            reply_markup=builder.as_markup(),
            parse_mode="Markdown"
        )
        await callback.answer(f"Таңдалды: {voice_label}")
    else:
        await callback.answer("❌ Қате: Дауыс табылмады.")
