import pytest
import base64
import respx
import httpx
from unittest.mock import AsyncMock, MagicMock
from tests.conftest import make_context


def make_photo_update(user_id: int, image_bytes: bytes, caption: str | None = None, chat_id: int = 100):
    tg_file = MagicMock()
    tg_file.download_as_bytearray = AsyncMock(return_value=bytearray(image_bytes))
    photo_size = MagicMock()
    photo_size.get_file = AsyncMock(return_value=tg_file)
    message = MagicMock()
    message.photo = [photo_size]
    message.caption = caption
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


@respx.mock
@pytest.mark.asyncio
async def test_photo_handler_sends_base64_image_to_agent():
    from app.handlers.photo import photo_handler
    respx.post("http://agent:8000/api/v1/chat").mock(
        return_value=httpx.Response(200, text="data: Documento analizado\n\n")
    )
    fake_image = b"\x89PNG fake image bytes"
    expected_b64 = base64.b64encode(fake_image).decode()
    update = make_photo_update(user_id=11, image_bytes=fake_image)
    context, _ = make_context()
    await photo_handler(update, context)
    import json
    sent = json.loads(respx.calls.last.request.content)
    assert sent["image_base64"] == expected_b64
    assert sent["user_id"] == "tg_11"


@respx.mock
@pytest.mark.asyncio
async def test_photo_handler_uses_caption_as_message():
    from app.handlers.photo import photo_handler
    respx.post("http://agent:8000/api/v1/chat").mock(
        return_value=httpx.Response(200, text="data: ok\n\n")
    )
    update = make_photo_update(user_id=11, image_bytes=b"fake", caption="¿Qué dice aquí?")
    context, _ = make_context()
    await photo_handler(update, context)
    import json
    sent = json.loads(respx.calls.last.request.content)
    assert sent["message"] == "¿Qué dice aquí?"


@respx.mock
@pytest.mark.asyncio
async def test_photo_handler_uses_default_message_when_no_caption():
    from app.handlers.photo import photo_handler
    respx.post("http://agent:8000/api/v1/chat").mock(
        return_value=httpx.Response(200, text="data: ok\n\n")
    )
    update = make_photo_update(user_id=11, image_bytes=b"fake", caption=None)
    context, _ = make_context()
    await photo_handler(update, context)
    import json
    sent = json.loads(respx.calls.last.request.content)
    assert sent["message"] == "Analiza este documento"


@respx.mock
@pytest.mark.asyncio
async def test_photo_handler_replies_with_agent_response():
    from app.handlers.photo import photo_handler
    respx.post("http://agent:8000/api/v1/chat").mock(
        return_value=httpx.Response(200, text="data: Resultado\n\n")
    )
    update = make_photo_update(user_id=22, image_bytes=b"img")
    context, _ = make_context()
    await photo_handler(update, context)
    update.message.reply_text.assert_called_once_with("Resultado")


@respx.mock
@pytest.mark.asyncio
async def test_photo_handler_sends_typing_action():
    from app.handlers.photo import photo_handler
    respx.post("http://agent:8000/api/v1/chat").mock(
        return_value=httpx.Response(200, text="data: ok\n\n")
    )
    update = make_photo_update(user_id=5, image_bytes=b"img")
    context, _ = make_context()
    await photo_handler(update, context)
    update.message.chat.send_action.assert_called_once_with("typing")


@respx.mock
@pytest.mark.asyncio
async def test_photo_handler_selects_highest_resolution():
    from app.handlers.photo import photo_handler
    respx.post("http://agent:8000/api/v1/chat").mock(
        return_value=httpx.Response(200, text="data: ok\n\n")
    )
    tg_file = MagicMock()
    tg_file.download_as_bytearray = AsyncMock(return_value=bytearray(b"hires"))
    small = MagicMock()
    small.get_file = AsyncMock()
    large = MagicMock()
    large.get_file = AsyncMock(return_value=tg_file)
    message = MagicMock()
    message.photo = [small, large]
    message.caption = None
    message.reply_text = AsyncMock()
    chat = MagicMock()
    chat.id = 100
    chat.send_action = AsyncMock()
    message.chat = chat
    user = MagicMock()
    user.id = 1
    update = MagicMock()
    update.message = message
    update.effective_user = user
    update.effective_chat = chat
    context, _ = make_context()
    await photo_handler(update, context)
    large.get_file.assert_called_once()
    small.get_file.assert_not_called()


@respx.mock
@pytest.mark.asyncio
async def test_photo_handler_stores_chat_id():
    from app.handlers.photo import photo_handler
    respx.post("http://agent:8000/api/v1/chat").mock(
        return_value=httpx.Response(200, text="data: ok\n\n")
    )
    update = make_photo_update(user_id=33333, image_bytes=b"fake", chat_id=77777)
    context, redis_mock = make_context()
    await photo_handler(update, context)
    redis_mock.set.assert_called_once_with("alma:chat:33333", "77777")


@respx.mock
@pytest.mark.asyncio
async def test_photo_handler_still_replies_when_redis_down():
    from app.handlers.photo import photo_handler
    respx.post("http://agent:8000/api/v1/chat").mock(
        return_value=httpx.Response(200, text="data: ok\n\n")
    )
    update = make_photo_update(user_id=1, image_bytes=b"img")
    context, _ = make_context(redis_raises=True)
    await photo_handler(update, context)
    update.message.reply_text.assert_called_once_with("ok")
