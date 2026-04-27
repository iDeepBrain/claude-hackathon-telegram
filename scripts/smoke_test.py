"""
Alma Telegram Smoke Test
Runs on docker compose up — verifies all connections and unit tests,
then sends a step-by-step Telegram notification to the registered user.

Chat-id resolution order:
  1. TELEGRAM_TEST_CHAT_ID env var
  2. Scan Redis for alma:chat:* keys (populated by /start or any message to the bot)
  3. No notifications — tests still run and print to stdout
"""
import asyncio
import os
import subprocess
import sys
import time

import httpx
import redis.asyncio as aioredis

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
AGENT_URL = os.environ.get("AGENT_URL", "http://agent:8000")
REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379")
TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

RETRY_ATTEMPTS = 6
RETRY_DELAY = 5  # seconds between retries


# ── helpers ──────────────────────────────────────────────────────────────────

async def tg_send(chat_id: str, text: str) -> None:
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(f"{TG_API}/sendMessage", json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "HTML",
            })
    except Exception as e:
        print(f"  [warn] Telegram send failed: {e}")


async def resolve_chat_id() -> str | None:
    # 1. Env var manual override
    chat_id = os.environ.get("TELEGRAM_TEST_CHAT_ID", "").strip()
    if chat_id:
        print(f"  chat_id desde TELEGRAM_TEST_CHAT_ID: {chat_id}")
        return chat_id

    # 2. Scan Redis for registered users (populated by any message to the bot)
    try:
        r = aioredis.from_url(REDIS_URL)
        keys = await r.keys("alma:chat:*")
        if keys:
            val = await r.get(keys[0])
            await r.aclose()
            if val:
                chat_id = val.decode()
                print(f"  chat_id desde Redis ({keys[0].decode()}): {chat_id}")
                return chat_id
        await r.aclose()
    except Exception as e:
        print(f"  Redis scan: {e}")

    print("  ⚠️  Sin chat_id — corriendo sin notificaciones Telegram.")
    print("  Para habilitarlas: envía /start al bot y re-corre el smoke test.")
    return None


# ── checks ───────────────────────────────────────────────────────────────────

def run_unit_tests() -> tuple[bool, str, str]:
    start = time.time()
    result = subprocess.run(
        ["python", "-m", "pytest", "tests/", "--tb=short", "--no-header", "-q"],
        capture_output=True,
        text=True,
    )
    elapsed = f"{time.time() - start:.1f}s"
    lines = result.stdout.strip().split("\n")
    summary = next(
        (l for l in reversed(lines) if "passed" in l or "failed" in l or "error" in l),
        "sin output",
    )
    if result.returncode != 0:
        # include first failure lines for context
        fail_lines = [l for l in lines if "FAILED" in l or "ERROR" in l][:3]
        summary += "\n" + "\n".join(fail_lines)
    return result.returncode == 0, summary.strip(), elapsed


async def _check_redis_once() -> tuple[bool, str]:
    try:
        r = aioredis.from_url(REDIS_URL)
        await asyncio.wait_for(r.ping(), timeout=3.0)
        await r.aclose()
        return True, f"PONG ✓  ({REDIS_URL})"
    except asyncio.TimeoutError:
        return False, f"Timeout ({REDIS_URL})"
    except Exception as e:
        return False, str(e)


async def check_redis() -> tuple[bool, str]:
    for attempt in range(1, RETRY_ATTEMPTS + 1):
        ok, detail = await _check_redis_once()
        if ok:
            return ok, detail
        print(f"  Redis intento {attempt}/{RETRY_ATTEMPTS}: {detail}")
        if attempt < RETRY_ATTEMPTS:
            await asyncio.sleep(RETRY_DELAY)
    return False, detail


async def _check_agent_once() -> tuple[bool, str]:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{AGENT_URL}/health")
            data = resp.json()
            if data.get("status") == "ok":
                model = data.get("model", "?")
                return True, f"status=ok, model={model}  ({AGENT_URL})"
            return False, f"status={data.get('status', '?')}"
    except Exception as e:
        return False, str(e)


async def check_agent() -> tuple[bool, str]:
    for attempt in range(1, RETRY_ATTEMPTS + 1):
        ok, detail = await _check_agent_once()
        if ok:
            return ok, detail
        print(f"  Agent intento {attempt}/{RETRY_ATTEMPTS}: {detail}")
        if attempt < RETRY_ATTEMPTS:
            await asyncio.sleep(RETRY_DELAY)
    return False, detail


async def check_bot_api() -> tuple[bool, str]:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{TG_API}/getMe")
            data = resp.json()
            if data.get("ok"):
                bot = data["result"]
                return True, f"@{bot['username']} — {bot['first_name']}"
            return False, data.get("description", "error desconocido")
    except Exception as e:
        return False, str(e)


# ── main ─────────────────────────────────────────────────────────────────────

async def main():
    SEP = "=" * 56

    print(f"\n{SEP}")
    print("  🌸  ALMA TELEGRAM — SMOKE TEST")
    print(SEP)

    print("\n📱 Resolviendo chat_id para notificaciones...")
    chat_id = await resolve_chat_id()

    if chat_id:
        await tg_send(
            chat_id,
            "🌸 <b>Alma Smoke Test iniciando</b>\n\n"
            "Verificando componentes del bot de Telegram.\n"
            "Te envío el resultado de cada paso 👇",
        )

    steps: list[tuple[bool, str]] = []

    # ── 1. Unit tests ──────────────────────────────────────────────────────
    print(f"\n[1/4] 🧪 Unit tests (pytest)...")
    ok, summary, elapsed = run_unit_tests()
    icon = "✅" if ok else "❌"
    steps.append((ok, f"{icon} Unit Tests: {summary} ({elapsed})"))
    print(f"  {steps[-1][1]}")
    if chat_id:
        await tg_send(
            chat_id,
            f"<b>[1/4] Unit Tests</b>\n{icon} {summary}\n⏱ {elapsed}",
        )

    # ── 2. Redis ───────────────────────────────────────────────────────────
    print(f"\n[2/4] 🔴 Redis ({REDIS_URL})...")
    ok, detail = await check_redis()
    icon = "✅" if ok else "❌"
    steps.append((ok, f"{icon} Redis: {detail}"))
    print(f"  {steps[-1][1]}")
    if chat_id:
        await tg_send(chat_id, f"<b>[2/4] Redis</b>\n{icon} {detail}")

    # ── 3. Agent API ───────────────────────────────────────────────────────
    print(f"\n[3/4] 🤖 Agent API ({AGENT_URL})...")
    ok, detail = await check_agent()
    icon = "✅" if ok else "❌"
    steps.append((ok, f"{icon} Agent API: {detail}"))
    print(f"  {steps[-1][1]}")
    if chat_id:
        await tg_send(
            chat_id,
            f"<b>[3/4] Agent API</b>\n{icon} {detail}",
        )

    # ── 4. Telegram Bot API ────────────────────────────────────────────────
    print(f"\n[4/4] 📨 Telegram Bot API...")
    ok, detail = await check_bot_api()
    icon = "✅" if ok else "❌"
    steps.append((ok, f"{icon} Telegram Bot API: {detail}"))
    print(f"  {steps[-1][1]}")
    if chat_id:
        await tg_send(chat_id, f"<b>[4/4] Telegram Bot API</b>\n{icon} {detail}")

    # ── Final summary ──────────────────────────────────────────────────────
    all_ok = all(s[0] for s in steps)
    n_ok = sum(1 for s in steps if s[0])
    banner = "🟢 TODO OK" if all_ok else f"🔴 {4 - n_ok} FALLO(S)"
    body = "\n".join(s[1] for s in steps)

    print(f"\n{SEP}")
    print(f"  {banner}  ({n_ok}/4)")
    print(SEP)
    for s in steps:
        print(f"  {s[1]}")
    print(SEP + "\n")

    if chat_id:
        status_word = "COMPLETO ✓" if all_ok else "CON FALLOS ✗"
        await tg_send(
            chat_id,
            f"{'🟢' if all_ok else '🔴'} <b>Smoke Test {status_word}</b> ({n_ok}/4)\n\n{body}",
        )

    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    asyncio.run(main())
