from telegram import Update
from telegram.ext import ContextTypes
from app.handlers.redis_store import store_chat_id


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tg_user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    await store_chat_id(context, tg_user_id, chat_id)
    await update.message.reply_text(
        "¡Hola! 👋 Soy Alma, tu compañera emocional.\n\n"
        "Puedes contarme cómo te sientes, qué te preocupa, "
        "o simplemente charlar. Estoy aquí para escucharte.\n\n"
        "Te escribiré de vez en cuando para saber cómo estás 🌸"
    )
