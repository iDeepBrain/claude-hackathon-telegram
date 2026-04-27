import pytest
import respx
import httpx
from app.services.agent_client import AgentClient


@pytest.fixture
def agent_client():
    return AgentClient(base_url="http://agent:8000")


@respx.mock
@pytest.mark.asyncio
async def test_chat_collects_sse_chunks(agent_client):
    sse_body = "data: Hola\n\ndata:  mundo\n\n"
    respx.post("http://agent:8000/api/v1/chat").mock(
        return_value=httpx.Response(200, text=sse_body)
    )
    result = await agent_client.chat(user_id="123", message="test")
    assert result == "Hola mundo"


@respx.mock
@pytest.mark.asyncio
async def test_chat_skips_empty_data_lines(agent_client):
    sse_body = "data: Hello\n\ndata: \n\ndata: world\n\n"
    respx.post("http://agent:8000/api/v1/chat").mock(
        return_value=httpx.Response(200, text=sse_body)
    )
    result = await agent_client.chat(user_id="123", message="test")
    assert result == "Helloworld"


@respx.mock
@pytest.mark.asyncio
async def test_chat_with_image_includes_image_in_payload(agent_client):
    respx.post("http://agent:8000/api/v1/chat").mock(
        return_value=httpx.Response(200, text="data: ok\n\n")
    )
    await agent_client.chat(user_id="123", message="test", image_base64="abc123")
    import json
    sent_body = json.loads(respx.calls.last.request.content)
    assert sent_body["image_base64"] == "abc123"


@respx.mock
@pytest.mark.asyncio
async def test_chat_without_image_omits_image_key(agent_client):
    respx.post("http://agent:8000/api/v1/chat").mock(
        return_value=httpx.Response(200, text="data: ok\n\n")
    )
    await agent_client.chat(user_id="123", message="test")
    import json
    sent_body = json.loads(respx.calls.last.request.content)
    assert "image_base64" not in sent_body


@respx.mock
@pytest.mark.asyncio
async def test_chat_sends_language_es_by_default(agent_client):
    respx.post("http://agent:8000/api/v1/chat").mock(
        return_value=httpx.Response(200, text="data: ok\n\n")
    )
    await agent_client.chat(user_id="42", message="hola")
    import json
    sent_body = json.loads(respx.calls.last.request.content)
    assert sent_body["language"] == "es"
    assert sent_body["user_id"] == "42"


@respx.mock
@pytest.mark.asyncio
async def test_health_returns_true_when_ok(agent_client):
    respx.get("http://agent:8000/health").mock(
        return_value=httpx.Response(200, json={"status": "ok"})
    )
    result = await agent_client.health()
    assert result is True


@respx.mock
@pytest.mark.asyncio
async def test_health_returns_false_on_connect_error(agent_client):
    respx.get("http://agent:8000/health").mock(side_effect=httpx.ConnectError("fail"))
    result = await agent_client.health()
    assert result is False


@respx.mock
@pytest.mark.asyncio
async def test_health_returns_false_when_status_not_ok(agent_client):
    respx.get("http://agent:8000/health").mock(
        return_value=httpx.Response(200, json={"status": "degraded"})
    )
    result = await agent_client.health()
    assert result is False
