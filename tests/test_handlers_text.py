import pytest
import respx
import httpx
from unittest.mock import AsyncMock, MagicMock
from tests.conftest import make_context, make_text_update


@respx.mock
@pytest.mark.asyncio
async def test_text_handler_calls_agent_and_replies():
    from app.handlers.text import text_handler
    respx.post("http://agent:8000/api/v1/chat").mock(
        return_value=httpx.Response(200, text="data: Respuesta del agente\n\n")
    )
    update = make_text_update(user_id=42, chat_id=100, text="me siento sola")
    context, _ = make_context()
    await text_handler(update, context)
    update.message.reply_text.assert_called_once_with("Respuesta del agente")


@respx.mock
@pytest.mark.asyncio
async def test_text_handler_sends_typing_action():
    from app.handlers.text import text_handler
    respx.post("http://agent:8000/api/v1/chat").mock(
        return_value=httpx.Response(200, text="data: ok\n\n")
    )
    update = make_text_update(user_id=7, chat_id=100, text="hola")
    context, _ = make_context()
    await text_handler(update, context)
    update.message.chat.send_action.assert_called_once_with("typing")


@respx.mock
@pytest.mark.asyncio
async def test_text_handler_passes_user_id_with_tg_prefix():
    from app.handlers.text import text_handler
    respx.post("http://agent:8000/api/v1/chat").mock(
        return_value=httpx.Response(200, text="data: ok\n\n")
    )
    update = make_text_update(user_id=99, chat_id=100, text="prueba")
    context, _ = make_context()
    await text_handler(update, context)
    import json
    sent = json.loads(respx.calls.last.request.content)
    assert sent["user_id"] == "tg_99"
    assert sent["message"] == "prueba"


@respx.mock
@pytest.mark.asyncio
async def test_text_handler_replies_agent_down_on_connect_error():
    from app.handlers.text import text_handler
    respx.post("http://agent:8000/api/v1/chat").mock(
        side_effect=httpx.ConnectError("refused")
    )
    update = make_text_update(user_id=1, chat_id=100, text="hola")
    context, _ = make_context()
    await text_handler(update, context)
    reply = update.message.reply_text.call_args[0][0]
    assert "agente" in reply.lower()


@respx.mock
@pytest.mark.asyncio
async def test_text_handler_still_replies_when_redis_down():
    from app.handlers.text import text_handler
    respx.post("http://agent:8000/api/v1/chat").mock(
        return_value=httpx.Response(200, text="data: Sigo aquí\n\n")
    )
    update = make_text_update(user_id=5, chat_id=100, text="hola")
    context, _ = make_context(redis_raises=True)
    # must NOT raise — bot degraded gracefully
    await text_handler(update, context)
    update.message.reply_text.assert_called_once_with("Sigo aquí")
