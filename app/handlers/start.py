"""/start handler — also resolves WS-D.4 link tokens to bridge a web
identity (google_<sub>) with this Telegram chat.

Two paths:

  · Plain ``/start`` — first-touch from a user who came directly to the
    bot. We just store the chat_id (so the proactive scheduler can find
    them later) and reply with the welcome message.

  · ``/start alma_<token>`` — the user clicked the deep-link from the
    web app's profile modal after picking "Telegram" as channel. We
    look up the token in Redis (key ``alma:tg-link:<token>``) to get
    their google_<sub>, then persist the mapping
    ``alma:tg-chat-for:<google_sub>`` → chat_id so future proactive
    sends can target the right Telegram chat. The token is single-use
    (deleted after consumption) and was issued with a 10-min TTL by
    /api/v1/users/telegram-link/token.
"""
from telegram import Update
from telegram.ext import ContextTypes

from app.handlers.redis_store import store_chat_id

_LINK_PREFIX = "alma_"


async def _consume_link_token(context: ContextTypes.DEFAULT_TYPE, raw_token: str, chat_id: int) -> str | None:
    """Resolve a link token to a web identity and persist the mapping.

    Returns the linked user_id (e.g. ``google_<sub>``) on success, or
    ``None`` if the token is missing/expired/already consumed. We delete
    the token immediately on success so it cannot be reused.
    """
    if not raw_token.startswith(_LINK_PREFIX):
        return None
    token = raw_token[len(_LINK_PREFIX):]
    if not token or len(token) > 64:
        return None
    redis_client = context.bot_data.get("redis")
    if redis_client is None:
        return None
    key = f"alma:tg-link:{token}"
    user_id_b = await redis_client.get(key)
    if user_id_b is None:
        return None
    # Decode bytes (redis-py returns bytes by default)
    user_id = user_id_b.decode("utf-8") if isinstance(user_id_b, bytes) else str(user_id_b)
    # Delete the token to enforce single-use semantics
    await redis_client.delete(key)
    # Persist the mapping the proactive scheduler reads
    await redis_client.set(f"alma:tg-chat-for:{user_id}", str(chat_id))
    return user_id


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tg_user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    await store_chat_id(context, tg_user_id, chat_id)

    # Telegram puts the /start parameter in context.args. We accept the
    # web app's link tokens prefixed with "alma_". Anything else is
    # treated as a plain /start (welcome).
    raw_arg = context.args[0] if context.args else ""
    linked_user_id = None
    if raw_arg:
        linked_user_id = await _consume_link_token(context, raw_arg, chat_id)

    if linked_user_id:
        await update.message.reply_text(
            "¡Listo! 🌸 Quedaste conectada a tu cuenta de Alma.\n\n"
            "Desde ahora, si pasan días sin que abrás la web, "
            "te escribo por acá para ver cómo estás. "
            "Podés contarme lo que sea, cuando quieras."
        )
        return

    # Plain /start — same welcome as before
    await update.message.reply_text(
        "¡Hola! 👋 Soy Alma, tu compañera emocional.\n\n"
        "Puedes contarme cómo te sientes, qué te preocupa, "
        "o simplemente charlar. Estoy aquí para escucharte.\n\n"
        "Te escribiré de vez en cuando para saber cómo estás 🌸"
    )
