"""
Unit tests for scripts/smoke_test.py
All external I/O is mocked — no real Redis, Agent, or Telegram needed.
"""
import pytest
import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch

# Ensure BOT_TOKEN env is set before importing the module
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-token-placeholder")


def _import_smoke():
    """Import smoke_test module, adding scripts/ to path if needed."""
    scripts_path = os.path.join(os.path.dirname(__file__), "..", "scripts")
    if scripts_path not in sys.path:
        sys.path.insert(0, scripts_path)
    import importlib
    import smoke_test
    importlib.reload(smoke_test)
    return smoke_test


# ── resolve_chat_id ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_resolve_chat_id_from_env():
    smoke = _import_smoke()
    with patch.dict(os.environ, {"TELEGRAM_TEST_CHAT_ID": "99887766"}):
        result = await smoke.resolve_chat_id()
    assert result == "99887766"


@pytest.mark.asyncio
async def test_resolve_chat_id_from_redis():
    smoke = _import_smoke()
    redis_mock = AsyncMock()
    redis_mock.keys = AsyncMock(return_value=[b"alma:chat:12345"])
    redis_mock.get = AsyncMock(return_value=b"67890")
    redis_mock.aclose = AsyncMock()

    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("TELEGRAM_TEST_CHAT_ID", None)
        with patch("smoke_test.aioredis.from_url", return_value=redis_mock):
            result = await smoke.resolve_chat_id()

    assert result == "67890"


@pytest.mark.asyncio
async def test_resolve_chat_id_returns_none_when_no_source():
    smoke = _import_smoke()
    redis_mock = AsyncMock()
    redis_mock.keys = AsyncMock(return_value=[])
    redis_mock.aclose = AsyncMock()

    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("TELEGRAM_TEST_CHAT_ID", None)
        with patch("smoke_test.aioredis.from_url", return_value=redis_mock):
            result = await smoke.resolve_chat_id()

    assert result is None


# ── check_redis ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_check_redis_ok():
    smoke = _import_smoke()
    redis_mock = AsyncMock()
    redis_mock.ping = AsyncMock(return_value=True)
    redis_mock.aclose = AsyncMock()
    with patch("smoke_test.aioredis.from_url", return_value=redis_mock):
        ok, detail = await smoke._check_redis_once()
    assert ok is True
    assert "PONG" in detail


@pytest.mark.asyncio
async def test_check_redis_connection_error():
    smoke = _import_smoke()
    redis_mock = AsyncMock()
    redis_mock.ping = AsyncMock(side_effect=Exception("Connection refused"))
    with patch("smoke_test.aioredis.from_url", return_value=redis_mock):
        ok, detail = await smoke._check_redis_once()
    assert ok is False
    assert "Connection refused" in detail


# ── check_agent ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_check_agent_ok():
    import respx
    import httpx
    smoke = _import_smoke()
    with respx.mock:
        respx.get(f"{smoke.AGENT_URL}/health").mock(
            return_value=httpx.Response(200, json={"status": "ok", "model": "haiku"})
        )
        ok, detail = await smoke._check_agent_once()
    assert ok is True
    assert "haiku" in detail


@pytest.mark.asyncio
async def test_check_agent_down():
    smoke = _import_smoke()
    import httpx
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(side_effect=httpx.ConnectError("refused"))
        mock_client_cls.return_value = mock_client
        ok, detail = await smoke._check_agent_once()
    assert ok is False


# ── check_bot_api ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_check_bot_api_ok():
    import respx
    import httpx
    smoke = _import_smoke()
    with respx.mock:
        respx.get(f"{smoke.TG_API}/getMe").mock(
            return_value=httpx.Response(200, json={
                "ok": True,
                "result": {"username": "AlmaBot", "first_name": "Alma"}
            })
        )
        ok, detail = await smoke.check_bot_api()
    assert ok is True
    assert "AlmaBot" in detail


@pytest.mark.asyncio
async def test_check_bot_api_invalid_token():
    import respx
    import httpx
    smoke = _import_smoke()
    with respx.mock:
        respx.get(f"{smoke.TG_API}/getMe").mock(
            return_value=httpx.Response(401, json={"ok": False, "description": "Unauthorized"})
        )
        ok, detail = await smoke.check_bot_api()
    assert ok is False
    assert "Unauthorized" in detail


# ── run_unit_tests ────────────────────────────────────────────────────────────

def test_run_unit_tests_returns_bool_and_summary():
    smoke = _import_smoke()
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="44 passed in 0.46s\n",
            stderr="",
        )
        ok, summary, elapsed = smoke.run_unit_tests()
    assert ok is True
    assert "passed" in summary


def test_run_unit_tests_failure_captured():
    smoke = _import_smoke()
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="FAILED tests/test_foo.py::test_bar\n2 failed in 1.2s\n",
            stderr="",
        )
        ok, summary, elapsed = smoke.run_unit_tests()
    assert ok is False
    assert "failed" in summary


# ── tg_send ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_tg_send_does_not_raise_on_error():
    smoke = _import_smoke()
    import httpx
    with patch("httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(side_effect=httpx.ConnectError("unreachable"))
        mock_cls.return_value = mock_client
        # Must not raise
        await smoke.tg_send("123456", "test message")
