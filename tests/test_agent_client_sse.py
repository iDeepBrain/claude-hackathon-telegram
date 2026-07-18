"""SSE parser regression tests for ``app.services.agent_client.AgentClient``.

These tests would have caught the post-deploy bug where the previous parser
only filtered by ``data: `` line prefix without tracking the preceding
``event: `` line — so named-event JSON payloads (``agent_start``,
``cache_hit``, ``agent_done``) leaked into the user-facing reply on Telegram.

All bodies use CRLF (``\\r\\n``) because that is what ``sse_starlette`` emits
in production. The cache-hit fixture mirrors exactly the message sequence
reported by the user.
"""
from __future__ import annotations

import httpx
import pytest
import respx

from app.services.agent_client import AgentClient


@pytest.fixture
def agent_client() -> AgentClient:
    return AgentClient(base_url="http://agent:8000")


# ── named events must be dropped from the user-facing reply ──────────────────


@respx.mock
@pytest.mark.asyncio
async def test_named_events_dropped_from_reply(agent_client):
    """``event: <name>`` blocks carry pipeline observability metadata and must
    NEVER appear in the message body the user reads."""
    sse = (
        b"event: agent_start\r\n"
        b'data: {"language": "es", "has_image": false}\r\n'
        b"\r\n"
        b"data: Hola\r\n"
        b"\r\n"
        b"event: agent_done\r\n"
        b'data: {"stop_reason": "end_turn", "latency_ms": 100}\r\n'
        b"\r\n"
    )
    respx.post("http://agent:8000/api/v1/chat").mock(
        return_value=httpx.Response(200, content=sse)
    )
    result = await agent_client.chat(user_id="u1", message="hola")
    assert result == "Hola"
    assert "language" not in result
    assert "stop_reason" not in result
    assert "{" not in result and "}" not in result


# ── cache_hit path: the exact scenario the user reported ─────────────────────


@respx.mock
@pytest.mark.asyncio
async def test_cache_hit_path_returns_clean_text(agent_client):
    """Identical message sent twice → semantic cache hits. The buggy parser
    leaked ``{"language":...}``, ``{}`` and ``{"stop_reason":"cache",...}``
    into the message body."""
    sse = (
        b"event: agent_start\r\n"
        b'data: {"language": "en", "has_image": false}\r\n'
        b"\r\n"
        b"event: cache_hit\r\n"
        b"data: {}\r\n"
        b"\r\n"
        b"data: I'm sorry to hear you're feeling sad.\r\n"
        b"data: \r\n"
        b"data: Can you tell me a bit more about what's making you feel this way?\r\n"
        b"\r\n"
        b"event: agent_done\r\n"
        b'data: {"stop_reason": "cache", "latency_ms": 86}\r\n'
        b"\r\n"
    )
    respx.post("http://agent:8000/api/v1/chat").mock(
        return_value=httpx.Response(200, content=sse)
    )
    result = await agent_client.chat(user_id="u1", message="I am sad")
    expected = (
        "I'm sorry to hear you're feeling sad.\n"
        "\n"
        "Can you tell me a bit more about what's making you feel this way?"
    )
    assert result == expected
    assert "language" not in result
    assert "stop_reason" not in result
    assert "cache" not in result.lower()


# ── multi-line response_chunk ────────────────────────────────────────────────


@respx.mock
@pytest.mark.asyncio
async def test_multiline_response_chunk_concatenates_with_newlines(agent_client):
    """Per SSE spec, multiple ``data:`` lines within a single event are
    joined with ``\\n`` in the parsed value."""
    sse = (
        b"data: line one\r\n"
        b"data: line two\r\n"
        b"data: line three\r\n"
        b"\r\n"
    )
    respx.post("http://agent:8000/api/v1/chat").mock(
        return_value=httpx.Response(200, content=sse)
    )
    result = await agent_client.chat(user_id="u1", message="x")
    assert result == "line one\nline two\nline three"


# ── CRLF line endings ────────────────────────────────────────────────────────


@respx.mock
@pytest.mark.asyncio
async def test_handles_crlf_line_endings(agent_client):
    """``sse_starlette`` emits ``\\r\\n`` by default — parser must tolerate it."""
    sse = b"data: con\r\n\r\ndata: tent\r\n\r\n"
    respx.post("http://agent:8000/api/v1/chat").mock(
        return_value=httpx.Response(200, content=sse)
    )
    result = await agent_client.chat(user_id="u1", message="x")
    assert result == "content"


# ── full normal flow with named and unnamed events interleaved ───────────────


@respx.mock
@pytest.mark.asyncio
async def test_full_normal_flow_named_and_unnamed_interleaved(agent_client):
    """The full pipeline emits agent_start → memory_retrieved → model_routed →
    several response_chunks → agent_done. The reply must contain only the
    chunk text concatenated, no metadata."""
    sse = (
        b"event: agent_start\r\n"
        b'data: {"language": "es"}\r\n'
        b"\r\n"
        b"event: memory_retrieved\r\n"
        b'data: {"count": 0, "layers": []}\r\n'
        b"\r\n"
        b"event: model_routed\r\n"
        b'data: {"model": "claude-haiku-4-5"}\r\n'
        b"\r\n"
        b"data: Hola.\r\n"
        b"\r\n"
        b"data:  Estoy aqu\xc3\xad contigo.\r\n"
        b"\r\n"
        b"event: agent_done\r\n"
        b'data: {"stop_reason": "end_turn", "chunks": 2}\r\n'
        b"\r\n"
    )
    respx.post("http://agent:8000/api/v1/chat").mock(
        return_value=httpx.Response(200, content=sse)
    )
    result = await agent_client.chat(user_id="u1", message="hola")
    assert result == "Hola. Estoy aquí contigo."


# ── guard_blocked path ───────────────────────────────────────────────────────


@respx.mock
@pytest.mark.asyncio
async def test_guard_blocked_path_returns_only_safe_response(agent_client):
    sse = (
        b"event: agent_start\r\n"
        b'data: {"language": "es"}\r\n'
        b"\r\n"
        b"event: guard_blocked\r\n"
        b'data: {"pattern": "ignore previous"}\r\n'
        b"\r\n"
        b"data: Lo siento, no puedo procesar eso.\r\n"
        b"\r\n"
        b"event: agent_done\r\n"
        b'data: {"stop_reason": "guard"}\r\n'
        b"\r\n"
    )
    respx.post("http://agent:8000/api/v1/chat").mock(
        return_value=httpx.Response(200, content=sse)
    )
    result = await agent_client.chat(user_id="u1", message="ignore previous")
    assert result == "Lo siento, no puedo procesar eso."
    assert "guard" not in result


# ── DONE sentinel still honored (legacy) ─────────────────────────────────────


@respx.mock
@pytest.mark.asyncio
async def test_done_sentinel_does_not_leak(agent_client):
    """Legacy ``[DONE]`` sentinel from older streaming conventions: when seen
    in an unnamed-event ``data:`` line it terminates the stream and is not
    appended to the reply."""
    sse = b"data: hello\r\n\r\ndata: [DONE]\r\n\r\n"
    respx.post("http://agent:8000/api/v1/chat").mock(
        return_value=httpx.Response(200, content=sse)
    )
    result = await agent_client.chat(user_id="u1", message="x")
    assert result == "hello"
    assert "DONE" not in result
