import pytest
import respx
import httpx
from tests.conftest import make_context, make_text_update, make_start_update


@respx.mock
@pytest.mark.asyncio
async def test_chat_id_stored_on_text_message():
    from app.handlers.text import text_handler
    respx.post("http://agent:8000/api/v1/chat").mock(
        return_value=httpx.Response(200, text="data: ok\n\n")
    )
    update = make_text_update(user_id=12345, chat_id=67890, text="me siento triste")
    context, redis_mock = make_context()
    await text_handler(update, context)
    redis_mock.set.assert_called_once_with("alma:chat:12345", "67890")


@respx.mock
@pytest.mark.asyncio
async def test_user_id_has_tg_prefix():
    from app.handlers.text import text_handler
    respx.post("http://agent:8000/api/v1/chat").mock(
        return_value=httpx.Response(200, text="data: ok\n\n")
    )
    update = make_text_update(user_id=12345, chat_id=67890)
    context, _ = make_context()
    await text_handler(update, context)
    import json
    sent = json.loads(respx.calls.last.request.content)
    assert sent["user_id"] == "tg_12345"


@pytest.mark.asyncio
async def test_start_handler_stores_chat_id():
    from app.handlers.start import start_handler
    update = make_start_update(user_id=11111, chat_id=99999)
    context, redis_mock = make_context()
    await start_handler(update, context)
    redis_mock.set.assert_called_once_with("alma:chat:11111", "99999")


@pytest.mark.asyncio
async def test_start_handler_alma_welcome():
    from app.handlers.start import start_handler
    update = make_start_update()
    context, _ = make_context()
    await start_handler(update, context)
    reply_text = update.message.reply_text.call_args[0][0]
    assert "Alma" in reply_text
    assert "compañera emocional" in reply_text
