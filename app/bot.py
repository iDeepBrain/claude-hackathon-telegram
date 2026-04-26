import asyncio
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
from app.config import settings
from app.services.agent_client import AgentClient
from app.handlers.start import start_handler
from app.handlers.text import text_handler
from app.handlers.document import document_handler
from app.handlers.photo import photo_handler


async def main() -> None:
    agent_client = AgentClient(base_url=settings.agent_url)

    app = (
        ApplicationBuilder()
        .token(settings.telegram_bot_token)
        .post_init(lambda a: a.bot_data.update({"agent_client": agent_client}))
        .build()
    )

    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    app.add_handler(MessageHandler(filters.Document.PDF, document_handler))
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))

    if settings.telegram_mode == "webhook":
        await app.run_webhook(
            listen="0.0.0.0",
            port=settings.telegram_webhook_port,
            webhook_url=settings.telegram_webhook_url,
        )
    else:
        await app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    asyncio.run(main())
