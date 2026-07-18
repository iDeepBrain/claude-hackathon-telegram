import os

import httpx


class AgentClient:
    def __init__(self, base_url: str):
        # Internal bearer — when set, every outbound call carries
        # Authorization: Bearer <token>. The agent's middleware
        # validates it; without the header those endpoints return 401.
        # If the env var is empty (local dev without the secret), the
        # client sends no Authorization and the agent stays fail-open.
        token = os.getenv("ALMA_INTERNAL_TOKEN", "").strip()
        headers = {"Authorization": f"Bearer {token}"} if token else None
        self.client = httpx.AsyncClient(base_url=base_url, timeout=60.0, headers=headers)

    async def chat(
        self,
        user_id: str,
        message: str,
        language: str = "es",
        image_base64: str | None = None,
    ) -> str:
        """POST a turn to the agent and return the user-facing reply text.

        Parses the agent's SSE stream:

        - **Unnamed events** (no preceding ``event:`` line) carry response
          token text and are concatenated into the final reply.
        - **Named events** (``event: agent_start``, ``event: memory_retrieved``,
          ``event: model_routed``, ``event: agent_done``, ``event: cache_hit``,
          etc.) carry pipeline observability metadata and are intentionally
          dropped — the user must never see ``{"language": "es", ...}`` JSON
          in their Telegram message body.

        Each SSE event is terminated by a blank line; the parser dispatches
        the buffered ``data:`` lines on every blank line it sees, then resets.
        """
        payload: dict = {"user_id": user_id, "message": message, "language": language}
        if image_base64 is not None:
            payload["image_base64"] = image_base64

        chunks: list[str] = []
        current_event: str | None = None
        current_data: list[str] = []

        def flush() -> None:
            if current_event is None and current_data:
                content = "\n".join(current_data)
                stripped = content.strip()
                if stripped and stripped != "[DONE]":
                    chunks.append(content)
            # Named events: payload metadata, intentionally dropped from reply

        async with self.client.stream("POST", "/api/v1/chat", json=payload) as resp:
            async for line in resp.aiter_lines():
                if line == "":
                    flush()
                    current_event = None
                    current_data = []
                elif line.startswith("event: "):
                    current_event = line[7:].strip()
                elif line.startswith("data: "):
                    current_data.append(line[6:])
                # SSE comments (lines starting with ':') and unknown fields are ignored

        # Final dispatch in case stream ends without a trailing blank line
        flush()

        return "".join(chunks)

    async def health(self) -> bool:
        try:
            r = await self.client.get("/health")
            return r.json().get("status") == "ok"
        except Exception:
            return False

    async def aclose(self) -> None:
        await self.client.aclose()
