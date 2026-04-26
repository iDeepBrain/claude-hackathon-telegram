import base64
from telegram import Update
from telegram.ext import ContextTypes
from app.services.agent_client import AgentClient


async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    client: AgentClient = context.bot_data["agent_client"]
    user_id = str(update.effective_user.id)
    await update.message.chat.send_action("typing")
    photo = update.message.photo[-1]  # highest resolution
    tg_file = await photo.get_file()
    file_bytes = await tg_file.download_as_bytearray()
    image_b64 = base64.b64encode(bytes(file_bytes)).decode()
    caption = update.message.caption or "Analiza este documento"
    response = await client.chat(user_id=user_id, message=caption, image_base64=image_b64)
    await update.message.reply_text(response)
