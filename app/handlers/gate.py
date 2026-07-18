"""Shared message gate for all Telegram handlers.

Two guards:

1. **Kill switch** — when ``settings.telegram_bot_enabled`` is False the
   bot replies with a soft "taking a break" message and skips the agent
   call entirely. Flip the env var to disable the bot in seconds.
2. **Per-user daily rate limit** — bounds the number of messages the bot
   forwards to the agent per ``tg_user_id`` per UTC day. Uses Redis
   INCR + EXPIRE 24h.

Returns ``True`` when the message should proceed to the agent, ``False``
when the handler already replied with a polite block message.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from telegram import Update
from telegram.ext import ContextTypes

from app.config import settings

logger = logging.getLogger(__name__)

_BREAK_MESSAGE = "Alma is taking a short break right now. See you soon 💛"
_LIMIT_MESSAGE = "Por hoy ya conversamos bastante. Mañana sigo aquí 💛"


def _today_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d")


async def allow_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if not settings.telegram_bot_enabled:
        await update.message.reply_text(_BREAK_MESSAGE)
        return False

    redis_client = context.bot_data.get("redis")
    if redis_client is None:
        # No Redis → fail open. Without rate limiting we still let the
        # message through; the agent has its own per-user_id limit.
        return True

    tg_user_id = update.effective_user.id
    key = f"rate:tg:user:{tg_user_id}:{_today_utc()}"
    try:
        count = await redis_client.incr(key)
        if count == 1:
            await redis_client.expire(key, 86400)
    except Exception:
        logger.warning("Redis unavailable, skipping tg rate limit for tg_%s", tg_user_id)
        return True

    if count > settings.tg_user_daily_limit:
        await update.message.reply_text(_LIMIT_MESSAGE)
        return False
    return True
