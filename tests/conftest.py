import os

os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-token-placeholder")

import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.agent_client import AgentClient


@pytest.fixture
def agent_client():
    return AgentClient(base_url="http://agent:8000")


def make_context(redis_raises: bool = False) -> tuple:
    """Returns (context, redis_mock). If redis_raises=True, redis.set raises Exception."""
    client = AgentClient(base_url="http://agent:8000")
    redis_mock = AsyncMock()
    if redis_raises:
        redis_mock.set.side_effect = Exception("Redis connection refused")
    context = MagicMock()
    context.bot_data = {"agent_client": client, "redis": redis_mock}
    return context, redis_mock


def make_text_update(user_id: int, chat_id: int, text: str = "hola") -> MagicMock:
    message = MagicMock()
    message.text = text
    message.reply_text = AsyncMock()
    chat = MagicMock()
    chat.id = chat_id
    chat.send_action = AsyncMock()
    message.chat = chat
    user = MagicMock()
    user.id = user_id
    update = MagicMock()
    update.message = message
    update.effective_user = user
    update.effective_chat = chat
    return update


def make_start_update(user_id: int = 42, chat_id: int = 100) -> MagicMock:
    message = MagicMock()
    message.reply_text = AsyncMock()
    chat = MagicMock()
    chat.id = chat_id
    user = MagicMock()
    user.id = user_id
    update = MagicMock()
    update.message = message
    update.effective_user = user
    update.effective_chat = chat
    return update
