import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from aiogram import *
from config import *
from aiogram.exceptions import TelegramAPIError, TelegramForbiddenError, TelegramRetryAfter
if is_local:
    import dns.resolver
    dns.resolver.default_resolver = dns.resolver.Resolver(configure=False)
    dns.resolver.default_resolver.nameservers = ['8.8.8.8', '8.8.4.4']

# MongoDB setup
import certifi
ca = certifi.where()

if not MONGO_URI:
    print("⚠️ WARNING: MONGO_URI is not set! Check Vercel environment variables.")

client = AsyncIOMotorClient(
    MONGO_URI,
    serverSelectionTimeoutMS=20000,
    tlsCAFile=ca
)
db = client.get_database("bot_database") 
users_collection = db.users
stats_collection = db.stats
usage_collection = db.usage_stats
processed_updates = db.processed_updates

async def check_user_limit(user_id: int, limit_type: str = 'tts', model_name: str = None) -> bool:
    """Лимиттен аспағанын тексереді. limit_type: 'tts' or 'stt'"""
    from datetime import date
    today = date.today().isoformat()
    
    user_stat = await usage_collection.find_one({"user_id": user_id, "date": today})
    
    if limit_type == 'tts':
        safe_model_name = model_name.replace(".", "_") if model_name else "default"
        tts_usage = user_stat.get("tts_usage", {}) if user_stat else {}
        current_count = tts_usage.get(safe_model_name, 0)
        return current_count < DAILY_TTS_LIMIT
        
    elif limit_type == 'stt':
        current_count = user_stat.get("stt_count", 0) if user_stat else 0
        return current_count < DAILY_STT_LIMIT
    return False

async def get_user_limits(user_id: int):
    """Пайдаланушының бүгінгі лимиттерін қайтарады"""
    from datetime import date
    today = date.today().isoformat()
    
    user_stat = await usage_collection.find_one({"user_id": user_id, "date": today})
    
    tts_usage = user_stat.get("tts_usage", {}) if user_stat else {}
    stt_count = user_stat.get("stt_count", 0) if user_stat else 0
    
    return {
        "tts_usage_dict": tts_usage,
        "stt_usage": stt_count,
        "tts_limit": DAILY_TTS_LIMIT,
        "stt_limit": DAILY_STT_LIMIT
    }

async def increment_usage(user_id: int, limit_type: str = 'tts', model_name: str = None):
    """Қолдану санын арттыру. limit_type: 'tts' or 'stt'"""
    from datetime import date
    today = date.today().isoformat()
    
    update_query = {}
    
    if limit_type == 'tts':
        safe_model_name = model_name.replace(".", "_") if model_name else "default"
        update_query = {"$inc": {f"tts_usage.{safe_model_name}": 1}}
    else:
        update_query = {"$inc": {"stt_count": 1}}
    
    await usage_collection.update_one(
        {"user_id": user_id, "date": today},
        update_query,
        upsert=True
    )

async def log_synthesis(user_id: int):
    """Синтездеу оқиғасын тіркеу және статистиканы жаңарту"""
    await users_collection.update_one(
        {"user_id": user_id},
        {"$set": {"last_active": asyncio.get_event_loop().time()}}, 
        upsert=True
    )
    await stats_collection.update_one(
        {"_id": "global_stats"},
        {"$inc": {"total_syntheses": 1}},
        upsert=True
    )

async def get_stats():
    """Жалпы статистиканы алу"""
    total_users = await users_collection.count_documents({})
    stats_data = await stats_collection.find_one({"_id": "global_stats"})
    total_syntheses = stats_data.get("total_syntheses", 0) if stats_data else 0
    return total_users, total_syntheses

async def get_chat_members(user_id: int):
    try:
        chat_id = '-1003295950562'
        chat_member = await bot.get_chat_member(chat_id, user_id)
        if isinstance(chat_member, types.ChatMemberOwner):
            return "owner"
        elif isinstance(chat_member, types.ChatMemberAdministrator):
            return "admin"
        elif isinstance(chat_member, types.ChatMemberMember):
            return "member"
        elif isinstance(chat_member, types.ChatMemberRestricted):
            return "restricted"
        elif isinstance(chat_member, types.ChatMemberLeft):
            return "user"
        elif isinstance(chat_member, types.ChatMemberBanned):
            return "banned"
        return "user"
    except TelegramAPIError:
        return "user"
    except Exception:
        return None
    except TelegramRetryAfter as e:
        await asyncio.sleep(e.retry_after)
        return await get_chat_members(user_id)

async def get_user_model(user_id):
    user_data = await users_collection.find_one({"user_id": user_id})
    if user_data:
        return user_data.get("model_name", "kk_KZ-issai-high.onnx:1")
    return "kk_KZ-issai-high.onnx:1"

async def is_duplicate_update(update_id: int) -> bool:
    """Update ID-дің дубликат екенін тексереді (retry-ларды тоқтату үшін)"""
    from datetime import datetime
    try:
        # Бірден insert жасап көреміз. Егер бар болса, DuplicateKeyError шығады.
        await processed_updates.insert_one({
            "_id": update_id, 
            "created_at": datetime.now()
        })
        return False # Жаңа хабарлама
    except Exception as e:
        # Тек егер қате "дубликат" туралы болса ғана True қайтарамыз
        if "duplicate key error" in str(e).lower():
            return True
        # Басқа жағдайда (DB байланысы жоқ т.б.) хабарламаны жібере береміз
        print(f"[is_duplicate_update DEBUG]: {e}")
        return False

async def set_user_model(user_id, model_name):
    await users_collection.update_one(
        {"user_id": user_id},
        {"$set": {"model_name": model_name}},
        upsert=True
    )