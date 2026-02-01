import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, Router

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
LOCAL_BOT_TOKEN = os.getenv("LOCAL_BOT_TOKEN")
MONGO_URI = os.getenv("MONGODB_URI")
DAILY_TTS_LIMIT = 5
DAILY_STT_LIMIT = 5
MAX_TEXT_LENGTH = 1000
MAX_AUDIO_DURATION = 30
ADMIN_IDS = [int(i.strip()) for i in os.getenv("ADMIN_IDS", "").split(",") if i.strip()]

is_local = os.getenv("RUN_LOCAL", "false").lower() == "true"
current_token = LOCAL_BOT_TOKEN if is_local and LOCAL_BOT_TOKEN else BOT_TOKEN

if not current_token:
    print("❌ ERROR: No BOT_TOKEN found! Check environment variables.")
    current_token = "0000000000:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA" 

bot = Bot(current_token)
dp = Dispatcher()
router = Router()
dp.include_router(router)

STT_API_URL = "https://your-api/api/stt"
TTS_API_URL = "https://your-api/api/tts"

VOICE_CHOICES = {
    "kk_KZ-issai-high.onnx:0": ("ISSAI M2 (Ер)", "voice_issai_m2", ""),
    "kk_KZ-issai-high.onnx:1": ("Исеке (Ер)", "voice_issai_iseke", ""),
    "kk_KZ-issai-high.onnx:2": ("ISSAI F3 (Әйел)", "voice_issai_f3", ""),
    "kk_KZ-issai-high.onnx:3": ("Рая (Әйел)", "voice_issai_raya", ""),
    "kk_KZ-issai-high.onnx:4": ("ISSAI M1 (Ер)", "voice_issai_m1", ""),
    "kk_KZ-issai-high.onnx:5": ("ISSAI F1 (Әйел)", "voice_issai_f1", ""),

    "kk_KZ-iseke-x_low.onnx": ("Исеке (Low)", "voice_iseke", ""),
    "kk_KZ-raya-x_low.onnx": ("Рая (Low)", "voice_raya", "")
}

forbidden_words = [
"frobidden","words","list","example"
]
