from telegram import Update
from telegram.ext import ContextTypes


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "¡Hola! Soy Alma 👋\n\n"
        "Puedo ayudarte a entender contratos, términos y condiciones o cualquier documento legal.\n\n"
        "Envíame:\n"
        "• Un texto o pregunta 💬\n"
        "• Un PDF 📄\n"
        "• Una foto del documento 📸"
    )
