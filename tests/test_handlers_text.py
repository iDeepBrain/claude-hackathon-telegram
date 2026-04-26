import pytest
import respx
import httpx
from unittest.mock import AsyncMock, MagicMock


def make_text_update(user_id: int, text: str):
    message = MagicMock()
    message.text = text
    message.reply_text = AsyncMock()
    chat = MagicMock()
    chat.send_action = AsyncMock()
    message.chat = chat
    user = MagicMock()
    user.id = user_id
    update = MagicMock()
    update.message = message
    update.effective_user = user
    return update


@respx.mock
@pytest.mark.asyncio
async def test_text_handler_calls_agent_and_replies():
    from app.handlers.text import text_handler
    from app.services.agent_client import AgentClient
    respx.post("http://agent:8000/api/v1/chat").mock(
        return_value=httpx.Response(200, text="data: Respuesta del agente\n\n")
    )
    client = AgentClient(base_url="http://agent:8000")
    update = make_text_update(user_id=42, text="¿Qué significa este contrato?")
    context = MagicMock()
    context.bot_data = {"agent_client": client}
    await text_handler(update, context)
    update.message.reply_text.assert_called_once_with("Respuesta del agente")


@respx.mock
@pytest.mark.asyncio
async def test_text_handler_sends_typing_action():
    from app.handlers.text import text_handler
    from app.services.agent_client import AgentClient
    respx.post("http://agent:8000/api/v1/chat").mock(
        return_value=httpx.Response(200, text="data: ok\n\n")
    )
    client = AgentClient(base_url="http://agent:8000")
    update = make_text_update(user_id=7, text="hola")
    context = MagicMock()
    context.bot_data = {"agent_client": client}
    await text_handler(update, context)
    update.message.chat.send_action.assert_called_once_with("typing")


@respx.mock
@pytest.mark.asyncio
async def test_text_handler_passes_user_id_as_string():
    from app.handlers.text import text_handler
    from app.services.agent_client import AgentClient
    respx.post("http://agent:8000/api/v1/chat").mock(
        return_value=httpx.Response(200, text="data: ok\n\n")
    )
    client = AgentClient(base_url="http://agent:8000")
    update = make_text_update(user_id=99, text="prueba")
    context = MagicMock()
    context.bot_data = {"agent_client": client}
    await text_handler(update, context)
    import json
    sent = json.loads(respx.calls.last.request.content)
    assert sent["user_id"] == "99"
    assert sent["message"] == "prueba"
