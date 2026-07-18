# Alma — Telegram Bot

> Part of the **Alma** system — an emotional AI companion for mental health. See [claude-hackathon-alma](https://github.com/iDeepBrain/claude-hackathon-alma) for the full architecture, diagrams, and project overview.

A Python long-polling Telegram bot that bridges Telegram users to the Alma agent backend. It relays text, PDFs, and photos to the agent, streams the reply back token by token, and persists each user's `chat_id` so the agent can reach out first with proactive check-ins.

> **Service status:** the code is fully available and runnable, but the hosted Cloud Run instance has been shut down to save cost. Everything below runs locally against the rest of the Alma stack.

---

## Role in the Alma system

Alma is a multi-service system (agent + memory MCP + web + Telegram bot, orchestrated by Docker Compose). This repository is the **Telegram channel**: the surface that lets a user talk to Alma from a chat they already use every day, without installing anything.

Its responsibilities are deliberately narrow:

- **Receive** Telegram updates via long polling (no public webhook required).
- **Translate** each Telegram user into a stable Alma identity (`tg_{tg_user_id}`).
- **Forward** the turn to the agent's `/api/v1/chat` endpoint over an authenticated internal call, and stream the reply back to the chat.
- **Persist** the user's `chat_id` in Redis on first contact, which is what enables the agent's scheduler to initiate proactive messages later.

All of the "intelligence" — memory retrieval, model routing, crisis detection, response generation — lives in the agent. This bot is a thin, well-guarded transport layer.

## Architecture and data flow

### Inbound message (user talks to Alma)

```
User → Telegram → [long polling] → Bot
                                     │
                                     ├─ gate: kill-switch + per-user daily rate limit (Redis)
                                     ├─ store chat_id → Redis  (key: alma:chat:{tg_user_id})
                                     ├─ map identity: tg_user_id → "tg_{tg_user_id}"
                                     │
                                     ▼
                    POST /api/v1/chat   (Authorization: Bearer $ALMA_INTERNAL_TOKEN)
                                     │   { user_id, message, language, image_base64? }
                                     ▼
                              Alma Agent  ── SSE stream ──▶ Bot concatenates token
                                                            events → reply_text()
```

The agent responds as a **Server-Sent Events** stream. The bot's `AgentClient` parses it carefully:

- **Unnamed events** (raw `data:` lines) carry response tokens and are concatenated into the final reply.
- **Named events** (`event: agent_start`, `event: memory_retrieved`, `event: model_routed`, `event: agent_done`, `event: cache_hit`, …) carry pipeline observability metadata and are intentionally dropped, so the user never sees internal JSON in their chat.

### Proactive message (Alma reaches out first)

The bot does **not** send proactive messages. The agent's own scheduler reads the stored `chat_id` from Redis and calls the Telegram Bot API directly. This bot's only proactive responsibility is to make sure the `chat_id` was stored on first contact.

```
Agent scheduler → httpx → api.telegram.org/sendMessage  (chat_id from Redis)
```

### Internal bearer-token auth

Every outbound call from the bot to the agent carries an `Authorization: Bearer <ALMA_INTERNAL_TOKEN>` header when the token is present in the environment. The agent's middleware validates it; requests without a valid token are rejected with `401`. In local development without the secret set, the client omits the header and the agent stays fail-open — so the bot is easy to run locally but locked down in a deployed setting. The token is only ever read from the `ALMA_INTERNAL_TOKEN` environment variable and never logged.

## User-identity convention

A Telegram user with numeric id `123456` becomes the Alma user `tg_123456`. This namespaced prefix keeps Telegram users distinct from web users (which use UUID / `google_<sub>` ids) inside the shared memory store.

Optional **account linking** bridges the two worlds: the web app can issue a single-use, 10-minute link token, and the user opens the bot with a deep link (`/start alma_<token>`). The `/start` handler resolves the token from Redis, deletes it (single-use), and records `alma:tg-chat-for:<web_user_id> → chat_id` so proactive messages can target the right chat even for a user who signed up on the web.

## What each message type does

| Handler | Trigger | Behavior |
|---------|---------|----------|
| `/start` | `/start` or `/start alma_<token>` | Stores `chat_id`, optionally consumes a link token, sends the welcome message. |
| Text | any non-command text | Forwards the message to the agent, streams the reply. |
| Document (PDF) | a PDF attachment | Extracts text with PyMuPDF, sends the first ~8k chars to the agent for analysis. |
| Photo | an image | Base64-encodes the highest-resolution photo and sends it to the agent (with the caption as the prompt) for multimodal analysis. |

Two shared guards run before every message reaches the agent:

- **Kill switch** — setting `TELEGRAM_BOT_ENABLED=false` puts the bot into a friendly read-only state (a soft "taking a short break" reply) without a redeploy.
- **Per-user daily rate limit** — a Redis `INCR`/`EXPIRE` counter bounds messages per `tg_user_id` per UTC day (default 30). If Redis is unavailable, the guard fails open and relies on the agent's own per-user limit.

## Running locally

### Prerequisites

- A Telegram bot token from [@BotFather](https://t.me/BotFather).
- The rest of the Alma stack running (agent + Redis). The recommended way is the orchestrator repo, `claude-hackathon-infra`.

### Environment variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `TELEGRAM_BOT_TOKEN` | Bot token from @BotFather | — (required) |
| `TELEGRAM_MODE` | `polling` or `webhook` | `polling` |
| `AGENT_URL` | Base URL of the Alma agent | `http://localhost:8000` |
| `REDIS_URL` | Redis for `chat_id` storage, rate limiting, link tokens | `redis://redis:6379` |
| `ALMA_INTERNAL_TOKEN` | Internal bearer token for agent calls | unset (fail-open locally) |
| `TELEGRAM_BOT_ENABLED` | Global kill switch | `true` |
| `TG_USER_DAILY_LIMIT` | Per-user daily message cap | `30` |

Copy the example file and fill in your token:

```bash
cp .env.example .env
# edit TELEGRAM_BOT_TOKEN and AGENT_URL
```

### Option A — full stack (recommended)

```bash
cd ../claude-hackathon-infra
docker compose up --build -d   # brings up redis + mcp + agent + telegram-bot + web
```

### Option B — bot only, attached to a running stack

```bash
docker compose -f docker-compose.standalone.yml up --build -d
```

The standalone compose joins the `claude-hackathon-infra_hackathon` external network and points `AGENT_URL` at `http://agent:8000`.

### Option C — run the module directly

```bash
pip install -r requirements.txt
python -m app.bot
```

The process starts a tiny health-check HTTP server on `$PORT` (default `8000`, serving `/health`) and then begins long polling. The health server exists only so container platforms with startup probes are satisfied — the bot itself takes no inbound HTTP traffic.

### Tests

```bash
pytest tests/
```

## Deployment (reference)

The included `cloudbuild.yaml` builds the image, pushes it to Artifact Registry, and deploys a single-instance Cloud Run service (`min = max = 1`, `--no-allow-unauthenticated`). Because a long-polling worker holds no inbound request state, it runs at `concurrency=1` on a fractional CPU. Secrets (`TELEGRAM_BOT_TOKEN`, `REDIS_URL`, `ALMA_INTERNAL_TOKEN`) are injected from Secret Manager, never baked into the image. Agent URLs use redacted placeholders of the form `alma-<svc>-dev-PROJECTHASH-uc.a.run.app`.

> This pipeline is provided for reference. The live service has been decommissioned to save cost.

## Tech stack

- **Python 3.12**
- **[python-telegram-bot](https://python-telegram-bot.org/) 21.x** — async bot framework (long polling; webhook mode also supported)
- **httpx** — async HTTP client with SSE stream parsing for the agent call
- **pydantic-settings** — typed, env-driven configuration
- **redis** (`redis.asyncio`) — `chat_id` storage, rate limiting, and link-token resolution
- **PyMuPDF (fitz)** — PDF text extraction
- **pytest / pytest-asyncio / respx** — async test suite with HTTP mocking
- **Docker** + **Google Cloud Build / Cloud Run** — containerization and (former) deployment

---

Built by [Cristian Lazo Quispe](https://github.com/CristianLazoQuispe). Licensed under MIT (© iDeepBrain).
