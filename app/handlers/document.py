import fitz  # PyMuPDF
from telegram import Update
from telegram.ext import ContextTypes
from app.services.agent_client import AgentClient


async def extract_pdf_text(file_bytes: bytes) -> str:
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    text = "\n".join(page.get_text() for page in doc)
    doc.close()
    return text.strip()


async def document_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    client: AgentClient = context.bot_data["agent_client"]
    user_id = str(update.effective_user.id)
    await update.message.chat.send_action("typing")
    tg_file = await update.message.document.get_file()
    file_bytes = await tg_file.download_as_bytearray()
    text = await extract_pdf_text(bytes(file_bytes))
    if not text:
        await update.message.reply_text(
            "No pude extraer texto del PDF. ¿Puedes enviarlo como foto?"
        )
        return
    response = await client.chat(
        user_id=user_id,
        message=f"Analiza este documento:\n\n{text[:8000]}",
    )
    await update.message.reply_text(response)
