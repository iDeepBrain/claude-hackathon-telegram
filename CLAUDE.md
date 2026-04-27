# claude-hackathon-telegram

Bot de Telegram que reenvía mensajes al Alma Agent vía HTTP y almacena el `chat_id` para que el agent pueda enviar mensajes proactivos.

## Para el stack completo (recomendado)

```bash
cd ../claude-hackathon-infra
docker compose up --build -d
```

## Stand-alone (solo el bot, requiere infra corriendo)

```bash
cd claude-hackathon-telegram
docker compose -f docker-compose.standalone.yml up --build -d
```

El compose standalone usa la red `claude-hackathon-infra_hackathon` como `external: true`.

> Renombrado a `.standalone.yml` para no chocar con el stack de `claude-hackathon-infra`.

## Responsabilidad crítica: almacenar chat_id

En el **primer mensaje** de cada usuario, el bot debe almacenar el `chat_id` en Redis:

```python
redis.set(f"alma:chat:{tg_user_id}", chat_id)
```

Esto es lo que permite al APScheduler del agent encontrar al usuario para enviarle mensajes proactivos (desayuno, almuerzo, cena). Sin este paso, la proactividad no funciona.

## Flujo de mensaje entrante

```
1. Usuario → mensaje a Telegram
2. Bot recibe update (polling)
3. redis.set(f"alma:chat:{tg_user_id}", chat_id)   ← CRÍTICO
4. POST http://agent:8000/api/v1/chat (SSE stream)
5. SSE chunks concatenados → reply_text(full_response)
```

## Flujo de mensaje proactivo (iniciado por agent)

```
APScheduler en agent → httpx.post(api.telegram.org/sendMessage) con chat_id de Redis
```
El bot NO participa en el envío proactivo — el agent llama directo a la Telegram Bot API.

## .env requerido

```
TELEGRAM_BOT_TOKEN=<token de BotFather>
TELEGRAM_MODE=polling
AGENT_URL=http://localhost:8000   # override en compose a http://agent:8000
```

## Nota IPv6

La red hackathon tiene IPv6 deshabilitado (`com.docker.network.enable_ipv6: "false"`). Necesario porque httpx intenta conectar a `api.telegram.org` por IPv6 primero y Docker no tiene conectividad IPv6 → `[Errno -5] No address associated with hostname`.

## Tests

```bash
pytest tests/
```

## Pendiente por implementar

| Item | Story | Sprint | Estado |
|------|-------|--------|--------|
| Redis client + almacenar chat_id | STORY-011 | Sprint 03 | ❌ BLOCKER |
| `redis>=5.0` en requirements.txt | STORY-011 | Sprint 03 | ❌ Falta |
| REDIS_URL en Settings/config | STORY-011 | Sprint 03 | ❌ Falta |
| Fix user_id: `"123"` → `"tg_123"` | STORY-011 | Sprint 03 | ❌ Bug |
| Welcome message de Alma (no genérico) | STORY-012 | Sprint 03 | ❌ Bug |

## Qué ya funciona

- Handler de texto → POST al agent API
- Parseo SSE del agent response
- Envío de respuesta al usuario
- Dockerfile correcto
- IPv6 workaround documentado
