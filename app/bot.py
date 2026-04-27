import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import redis.asyncio as aioredis
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
from app.config import settings
from app.services.agent_client import AgentClient
from app.handlers.start import start_handler
from app.handlers.text import text_handler
from app.handlers.document import document_handler
from app.handlers.photo import photo_handler


class _HealthHandler(BaseHTTPRequestHandler):
    """Minimal HTTP listener so Cloud Run startup probes pass.

    The bot is a polling worker (no inbound HTTP) but Cloud Run requires
    services to listen on $PORT. This thread serves /health and silences
    everything else with a 200.
    """

    def do_GET(self):  # noqa: N802
        body = b'{"status":"ok","service":"alma-telegram-bot"}'
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args, **_kwargs):  # silence default access logs
        pass


def _start_health_server() -> None:
    port = int(os.getenv("PORT", "8000"))
    server = ThreadingHTTPServer(("0.0.0.0", port), _HealthHandler)
    threading.Thread(target=server.serve_forever, daemon=True, name="health-server").start()


async def _post_init(application) -> None:
    application.bot_data["agent_client"] = AgentClient(base_url=settings.agent_url)
    application.bot_data["redis"] = aioredis.from_url(settings.redis_url)


def main() -> None:
    _start_health_server()
    app = (
        ApplicationBuilder()
        .token(settings.telegram_bot_token)
        .post_init(_post_init)
        .build()
    )

    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    app.add_handler(MessageHandler(filters.Document.PDF, document_handler))
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))

    if settings.telegram_mode == "webhook":
        app.run_webhook(
            listen="0.0.0.0",
            port=settings.telegram_webhook_port,
            webhook_url=settings.telegram_webhook_url,
        )
    else:
        app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
