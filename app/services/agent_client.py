import httpx


class AgentClient:
    def __init__(self, base_url: str):
        self.client = httpx.AsyncClient(base_url=base_url, timeout=60.0)

    async def chat(
        self,
        user_id: str,
        message: str,
        language: str = "es",
        image_base64: str | None = None,
    ) -> str:
        payload: dict = {"user_id": user_id, "message": message, "language": language}
        if image_base64 is not None:
            payload["image_base64"] = image_base64
        chunks: list[str] = []
        async with self.client.stream("POST", "/api/v1/chat", json=payload) as resp:
            async for line in resp.aiter_lines():
                if line.startswith("data: "):
                    chunk = line[6:]
                    if chunk.strip():
                        chunks.append(chunk)
        return "".join(chunks)

    async def health(self) -> bool:
        try:
            r = await self.client.get("/health")
            return r.json().get("status") == "ok"
        except Exception:
            return False

    async def aclose(self) -> None:
        await self.client.aclose()
