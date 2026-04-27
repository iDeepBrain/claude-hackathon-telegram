import logging
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


async def store_chat_id(context: ContextTypes.DEFAULT_TYPE, tg_user_id: int, chat_id: int) -> None:
    try:
        redis_client = context.bot_data["redis"]
        await redis_client.set(f"alma:chat:{tg_user_id}", str(chat_id))
    except Exception:
        logger.warning("Redis unavailable, chat_id not stored for tg_%s", tg_user_id)
