from telegram import Update
from telegram.ext import ContextTypes
from app.services.agent_client import AgentClient


async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    client: AgentClient = context.bot_data["agent_client"]
    user_id = str(update.effective_user.id)
    message = update.message.text
    await update.message.chat.send_action("typing")
    response = await client.chat(user_id=user_id, message=message)
    await update.message.reply_text(response)
