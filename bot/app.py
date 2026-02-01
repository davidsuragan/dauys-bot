import os
import traceback
import json
import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from aiogram.types import Update

if __name__ == "__main__":
    os.environ["RUN_LOCAL"] = "true"

from config import bot, dp, is_local
from modules.chat_filter import ChatFilterMiddleware
from modules.subscription import SubscriptionMiddleware
from modules.limit import LimitMiddleware
import modules.handlers
import modules.callbacks

app = FastAPI()

print(f"ℹ️ Бот іске қосылуда. Режим: {'LOCAL (Polling)' if is_local else 'PRODUCTION (Webhook)'}")

dp.update.middleware(ChatFilterMiddleware())
dp.message.middleware(SubscriptionMiddleware())
dp.message.middleware(LimitMiddleware())

@app.post("/api/webhook")
async def webhook(request: Request):
    print("📥 WEBHOOK RECEIVED")
    from modules.data import is_duplicate_update
    update_id = None
    try:
        data = await request.json()
        print(f"📦 Payload: {json.dumps(data)[:100]}...")
        update_id = data.get("update_id")
        
        if update_id and await is_duplicate_update(update_id):
            return JSONResponse(content={"ok": True})

        update = Update.model_validate(data)
        await dp.feed_update(bot, update)
        return JSONResponse(content={"ok": True})
    except Exception as e:
        print(f"[ERROR webhook] Update ID {update_id}: {e}")
        print(traceback.format_exc())
        return JSONResponse(content={"ok": True})

@app.get("/set_webhook")
async def set_webhook(request: Request):
    from os import getenv
    base_url = str(request.base_url).rstrip("/")
    webhook_url = f"{base_url}/api/webhook"
    tg_url = f"https://api.telegram.org/bot{getenv('BOT_TOKEN')}/setWebhook"

    payload = {
        "url": webhook_url,
        "allowed_updates": ["message", "chat_member", "callback_query"],
        "drop_pending_updates": True
    }

    try:
        async with httpx.AsyncClient() as client:
            res = await client.post(tg_url, json=payload)
            res.raise_for_status()
            return res.json()
    except Exception:
        return {"error": traceback.format_exc()}

@app.api_route("/", methods=["GET", "HEAD"])
async def root(request: Request):
    return {"message": "✅ Aiogram + FastAPI бот жұмыс істеп тұр!"}

if __name__ == "__main__":
    import asyncio
    import logging

    async def start_polling():
        logging.basicConfig(level=logging.INFO)
        print("🚀 Бот LOCAL (Polling) режимінде іске қосылуда...")
        
        await dp.start_polling(bot)

    try:
        asyncio.run(start_polling())
    except KeyboardInterrupt:
        print("🛑 Бот тоқтатылды")
