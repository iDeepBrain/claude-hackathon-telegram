import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.mark.asyncio
async def test_store_chat_id_calls_redis_set():
    from app.handlers.redis_store import store_chat_id
    redis_mock = AsyncMock()
    context = MagicMock()
    context.bot_data = {"redis": redis_mock}
    await store_chat_id(context, tg_user_id=123, chat_id=456)
    redis_mock.set.assert_called_once_with("alma:chat:123", "456")


@pytest.mark.asyncio
async def test_store_chat_id_survives_redis_error():
    from app.handlers.redis_store import store_chat_id
    redis_mock = AsyncMock()
    redis_mock.set.side_effect = Exception("connection refused")
    context = MagicMock()
    context.bot_data = {"redis": redis_mock}
    # should NOT raise
    await store_chat_id(context, tg_user_id=123, chat_id=456)


@pytest.mark.asyncio
async def test_store_chat_id_key_format():
    from app.handlers.redis_store import store_chat_id
    redis_mock = AsyncMock()
    context = MagicMock()
    context.bot_data = {"redis": redis_mock}
    await store_chat_id(context, tg_user_id=9876543, chat_id=1234567)
    key, value = redis_mock.set.call_args[0]
    assert key == "alma:chat:9876543"
    assert value == "1234567"
