import pytest
from tests.conftest import make_context, make_start_update


@pytest.mark.asyncio
async def test_start_handler_replies_with_greeting():
    from app.handlers.start import start_handler
    update = make_start_update()
    context, _ = make_context()
    await start_handler(update, context)
    update.message.reply_text.assert_called_once()
    reply_text = update.message.reply_text.call_args[0][0]
    assert "Alma" in reply_text


@pytest.mark.asyncio
async def test_start_handler_mentions_emotional_companion():
    from app.handlers.start import start_handler
    update = make_start_update()
    context, _ = make_context()
    await start_handler(update, context)
    reply_text = update.message.reply_text.call_args[0][0]
    assert "compañera emocional" in reply_text
    assert "escucharte" in reply_text


@pytest.mark.asyncio
async def test_start_handler_stores_chat_id():
    from app.handlers.start import start_handler
    update = make_start_update(user_id=11111, chat_id=99999)
    context, redis_mock = make_context()
    await start_handler(update, context)
    redis_mock.set.assert_called_once_with("alma:chat:11111", "99999")


@pytest.mark.asyncio
async def test_start_handler_still_replies_when_redis_down():
    from app.handlers.start import start_handler
    update = make_start_update()
    context, _ = make_context(redis_raises=True)
    await start_handler(update, context)
    update.message.reply_text.assert_called_once()
    reply_text = update.message.reply_text.call_args[0][0]
    assert "Alma" in reply_text
