import base64
import httpx
from telegram import Update
from telegram.ext import ContextTypes
from app.services.agent_client import AgentClient
from app.handlers.redis_store import store_chat_id
from app.handlers.gate import allow_message

_AGENT_DOWN = "⚠️ El agente no está disponible ahora mismo. Inténtalo en unos minutos."


async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await allow_message(update, context):
        return
    client: AgentClient = context.bot_data["agent_client"]
    tg_user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    await store_chat_id(context, tg_user_id, chat_id)
    user_id = f"tg_{tg_user_id}"
    await update.message.chat.send_action("typing")
    photo = update.message.photo[-1]  # highest resolution
    tg_file = await photo.get_file()
    file_bytes = await tg_file.download_as_bytearray()
    image_b64 = base64.b64encode(bytes(file_bytes)).decode()
    caption = update.message.caption or "Analiza este documento"
    try:
        response = await client.chat(user_id=user_id, message=caption, image_base64=image_b64)
        await update.message.reply_text(response or "Sin respuesta del agente.")
    except (httpx.ConnectError, httpx.TimeoutException):
        await update.message.reply_text(_AGENT_DOWN)
