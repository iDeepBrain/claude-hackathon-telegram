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


# ──────────── WS-D.4: link-token bridge from web demo ────────────


@pytest.mark.asyncio
async def test_start_with_link_token_links_chat_and_replies_linked():
    """When the user opens the bot via the web's deep-link, /start has
    an `alma_<token>` argument. The handler must (1) resolve the token
    against Redis to get the web user_id, (2) persist the chat_id under
    `alma:tg-chat-for:<user_id>` so the proactive scheduler can reach
    them, and (3) reply with the linked-confirmation message."""
    from app.handlers.start import start_handler
    update = make_start_update(user_id=222, chat_id=555)
    context, redis_mock = make_context(args=["alma_deadbeef"])
    redis_mock.get.return_value = b"google_999"

    await start_handler(update, context)

    # Token was looked up
    redis_mock.get.assert_any_call("alma:tg-link:deadbeef")
    # Token was deleted (single-use)
    redis_mock.delete.assert_called_once_with("alma:tg-link:deadbeef")
    # Chat-for-user mapping was persisted
    set_calls = [c.args for c in redis_mock.set.call_args_list]
    assert ("alma:tg-chat-for:google_999", "555") in set_calls
    # Reply confirms link (different from plain welcome)
    reply_text = update.message.reply_text.call_args[0][0]
    assert "conectada" in reply_text.lower() or "conectado" in reply_text.lower()


@pytest.mark.asyncio
async def test_start_with_unknown_token_falls_back_to_welcome():
    """If the token is missing/expired, no linking happens and we serve
    the standard welcome — never lock the user out of the bot."""
    from app.handlers.start import start_handler
    update = make_start_update()
    context, redis_mock = make_context(args=["alma_expired"])
    redis_mock.get.return_value = None  # token not in Redis

    await start_handler(update, context)

    redis_mock.get.assert_any_call("alma:tg-link:expired")
    redis_mock.delete.assert_not_called()
    reply_text = update.message.reply_text.call_args[0][0]
    assert "compañera emocional" in reply_text  # plain welcome path


@pytest.mark.asyncio
async def test_start_with_non_alma_arg_is_ignored():
    """A start parameter that doesn't have our `alma_` prefix must not
    trigger any Redis lookup — could be from another integration."""
    from app.handlers.start import start_handler
    update = make_start_update()
    context, redis_mock = make_context(args=["other_42"])

    await start_handler(update, context)

    redis_mock.get.assert_not_called()
    redis_mock.delete.assert_not_called()
    reply_text = update.message.reply_text.call_args[0][0]
    assert "compañera emocional" in reply_text
