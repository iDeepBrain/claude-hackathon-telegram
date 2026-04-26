import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.mark.asyncio
async def test_start_handler_replies_with_greeting():
    from app.handlers.start import start_handler
    message = MagicMock()
    message.reply_text = AsyncMock()
    update = MagicMock()
    update.message = message
    context = MagicMock()
    await start_handler(update, context)
    message.reply_text.assert_called_once()
    reply_text = message.reply_text.call_args[0][0]
    assert "Alma" in reply_text


@pytest.mark.asyncio
async def test_start_handler_mentions_document_types():
    from app.handlers.start import start_handler
    message = MagicMock()
    message.reply_text = AsyncMock()
    update = MagicMock()
    update.message = message
    context = MagicMock()
    await start_handler(update, context)
    reply_text = message.reply_text.call_args[0][0]
    assert "PDF" in reply_text or "pdf" in reply_text
    assert "foto" in reply_text.lower() or "📸" in reply_text
