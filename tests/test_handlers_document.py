import pytest
import fitz
import respx
import httpx
from unittest.mock import AsyncMock, MagicMock


def make_pdf_bytes(text: str = "") -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    if text:
        page.insert_text((50, 100), text)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def make_document_update(user_id: int, pdf_bytes: bytes):
    tg_file = MagicMock()
    tg_file.download_as_bytearray = AsyncMock(return_value=bytearray(pdf_bytes))
    document = MagicMock()
    document.get_file = AsyncMock(return_value=tg_file)
    message = MagicMock()
    message.document = document
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


@pytest.mark.asyncio
async def test_extract_pdf_text_returns_content():
    from app.handlers.document import extract_pdf_text
    pdf_bytes = make_pdf_bytes("Contrato de prueba")
    result = await extract_pdf_text(pdf_bytes)
    assert "Contrato de prueba" in result


@pytest.mark.asyncio
async def test_extract_pdf_text_empty_pdf_returns_empty_string():
    from app.handlers.document import extract_pdf_text
    pdf_bytes = make_pdf_bytes()
    result = await extract_pdf_text(pdf_bytes)
    assert result == ""


@pytest.mark.asyncio
async def test_extract_pdf_text_multipage():
    from app.handlers.document import extract_pdf_text
    doc = fitz.open()
    for i in range(3):
        page = doc.new_page()
        page.insert_text((50, 100), f"Página {i + 1}")
    pdf_bytes = doc.tobytes()
    doc.close()
    result = await extract_pdf_text(pdf_bytes)
    assert "Página 1" in result and "Página 2" in result and "Página 3" in result


@respx.mock
@pytest.mark.asyncio
async def test_document_handler_sends_extracted_text_to_agent():
    from app.handlers.document import document_handler
    from app.services.agent_client import AgentClient
    respx.post("http://agent:8000/api/v1/chat").mock(
        return_value=httpx.Response(200, text="data: Análisis completo\n\n")
    )
    client = AgentClient(base_url="http://agent:8000")
    pdf_bytes = make_pdf_bytes("Cláusula de responsabilidad")
    update = make_document_update(user_id=55, pdf_bytes=pdf_bytes)
    context = MagicMock()
    context.bot_data = {"agent_client": client}
    await document_handler(update, context)
    update.message.reply_text.assert_called_once_with("Análisis completo")
    import json
    sent = json.loads(respx.calls.last.request.content)
    assert "Cláusula de responsabilidad" in sent["message"]
    assert sent["user_id"] == "55"


@pytest.mark.asyncio
async def test_document_handler_replies_error_when_pdf_has_no_text():
    from app.handlers.document import document_handler
    from app.services.agent_client import AgentClient
    client = AgentClient(base_url="http://agent:8000")
    pdf_bytes = make_pdf_bytes()
    update = make_document_update(user_id=55, pdf_bytes=pdf_bytes)
    context = MagicMock()
    context.bot_data = {"agent_client": client}
    await document_handler(update, context)
    reply = update.message.reply_text.call_args[0][0]
    assert "foto" in reply.lower() or "imagen" in reply.lower() or "extraer" in reply.lower()


@respx.mock
@pytest.mark.asyncio
async def test_document_handler_sends_typing_action():
    from app.handlers.document import document_handler
    from app.services.agent_client import AgentClient
    respx.post("http://agent:8000/api/v1/chat").mock(
        return_value=httpx.Response(200, text="data: ok\n\n")
    )
    client = AgentClient(base_url="http://agent:8000")
    pdf_bytes = make_pdf_bytes("texto")
    update = make_document_update(user_id=3, pdf_bytes=pdf_bytes)
    context = MagicMock()
    context.bot_data = {"agent_client": client}
    await document_handler(update, context)
    update.message.chat.send_action.assert_called_once_with("typing")
