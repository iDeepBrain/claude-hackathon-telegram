import httpx
from telegram import Update
from telegram.ext import ContextTypes
from app.services.agent_client import AgentClient
from app.handlers.redis_store import store_chat_id

_AGENT_DOWN = "⚠️ El agente no está disponible ahora mismo. Inténtalo en unos minutos."


async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    client: AgentClient = context.bot_data["agent_client"]
    tg_user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    await store_chat_id(context, tg_user_id, chat_id)
    user_id = f"tg_{tg_user_id}"
    message = update.message.text
    await update.message.chat.send_action("typing")
    try:
        response = await client.chat(user_id=user_id, message=message)
        await update.message.reply_text(response or "Sin respuesta del agente.")
    except (httpx.ConnectError, httpx.TimeoutException):
        await update.message.reply_text(_AGENT_DOWN)
