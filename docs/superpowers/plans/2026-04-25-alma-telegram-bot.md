# Alma — Telegram Bot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build Alma — a proactive wellness companion Telegram bot powered by Claude Opus 4.7 — with 4-layer persistent memory, proactive scheduled messages (APScheduler), crisis detection with escalation, and a Next.js demo UI showing the memory panel live.

**Architecture:** FastAPI backend handles all business logic (agent, memory, scheduler, crisis); a separate Telegram bot process calls the backend via HTTP. APScheduler runs inside the FastAPI process and sends proactive messages directly to Telegram via Bot API. SQLite stores all memory layers. The Next.js frontend simulates a WhatsApp-like UI with a live memory panel for the demo.

**Tech Stack:** Python 3.11+, FastAPI, aiosqlite, APScheduler 3.x, python-telegram-bot 20+, anthropic SDK (claude-opus-4-7), pytest + pytest-asyncio, Next.js 14, TypeScript, Tailwind CSS.

---

## File Structure

```
claude-hackathon-telegram/
├── backend/
│   ├── alma/
│   │   ├── __init__.py
│   │   ├── agent.py           # Conversational response generation
│   │   ├── prompts.py         # System prompts & message templates
│   │   └── onboarding.py      # 5-question onboarding state machine
│   ├── memory/
│   │   ├── __init__.py
│   │   ├── database.py        # aiosqlite connection + schema creation
│   │   ├── models.py          # Pydantic models for all 4 layers
│   │   ├── store.py           # MemoryStore class — CRUD for 4 layers
│   │   └── context.py         # ContextBuilder — assembles prompt context
│   ├── scheduler/
│   │   ├── __init__.py
│   │   ├── engine.py          # APScheduler setup + lifecycle
│   │   └── proactivity.py     # should_proact() + message generation
│   ├── crisis/
│   │   ├── __init__.py
│   │   └── detector.py        # risk_score() + escalation flow
│   ├── api/
│   │   ├── __init__.py
│   │   ├── app.py             # FastAPI app factory
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── chat.py        # POST /chat, POST /onboarding
│   │       ├── memory.py      # GET /memory/{user_id}
│   │       └── health.py      # GET /health
│   ├── tests/
│   │   ├── conftest.py        # Shared fixtures (DB, mock anthropic client)
│   │   ├── test_memory_store.py
│   │   ├── test_context_builder.py
│   │   ├── test_agent.py
│   │   ├── test_onboarding.py
│   │   ├── test_proactivity.py
│   │   ├── test_crisis.py
│   │   └── test_api.py
│   ├── requirements.txt
│   ├── .env.example
│   └── main.py                # Entrypoint: starts FastAPI + scheduler
├── bot/
│   ├── alma_bot.py            # Telegram bot — handlers + backend client
│   ├── requirements.txt
│   └── tests/
│       └── test_handlers.py
└── frontend/
    ├── app/
    │   ├── layout.tsx
    │   ├── page.tsx            # Demo chat UI
    │   └── volunteer/
    │       └── page.tsx        # Volunteer dashboard
    ├── components/
    │   ├── ChatWindow.tsx      # Chat bubbles + typing indicator
    │   ├── MessageBubble.tsx   # Single message with feature badge
    │   ├── MemoryPanel.tsx     # Live 4-layer memory view
    │   └── VolunteerBrief.tsx  # Structured context for volunteer
    ├── lib/
    │   └── api.ts              # Backend API client (fetch)
    ├── package.json
    └── tsconfig.json
```

---

## Stage 1 — Project Foundation

### Task 1: Directory scaffold + dependencies

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/.env.example`
- Create: `backend/main.py`
- Create: `bot/requirements.txt`
- Create: `bot/.env.example`

- [ ] **Step 1: Create backend directory structure**

```bash
cd /Users/cristian/Documents/Proyectos/Claude-Hackathon-Opus/claude-hackathon-telegram
mkdir -p backend/{alma,memory,scheduler,crisis,api/routes,tests}
mkdir -p bot/tests
mkdir -p frontend/{app/volunteer,components,lib}
touch backend/alma/__init__.py
touch backend/memory/__init__.py
touch backend/scheduler/__init__.py
touch backend/crisis/__init__.py
touch backend/api/__init__.py
touch backend/api/routes/__init__.py
```

- [ ] **Step 2: Create `backend/requirements.txt`**

```text
fastapi==0.115.0
uvicorn[standard]==0.30.6
aiosqlite==0.20.0
anthropic==0.40.0
apscheduler==3.10.4
pydantic==2.9.2
pydantic-settings==2.5.2
python-dotenv==1.0.1
httpx==0.27.2
pytest==8.3.3
pytest-asyncio==0.24.0
pytest-mock==3.14.0
```

- [ ] **Step 3: Create `backend/.env.example`**

```bash
ANTHROPIC_API_KEY=sk-ant-...
TELEGRAM_BOT_TOKEN=...
DATABASE_URL=alma.db
BACKEND_URL=http://localhost:8000
```

- [ ] **Step 4: Create `bot/requirements.txt`**

```text
python-telegram-bot==21.5
httpx==0.27.2
python-dotenv==1.0.1
pytest==8.3.3
pytest-asyncio==0.24.0
pytest-mock==3.14.0
```

- [ ] **Step 5: Create `backend/main.py`**

```python
import uvicorn
from api.app import create_app

app = create_app()

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
```

- [ ] **Step 6: Install backend dependencies**

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Expected: All packages install without error.

- [ ] **Step 7: Commit**

```bash
git add backend/ bot/ frontend/ docs/
git commit -m "chore: project scaffold — backend, bot, frontend directories"
```

---

## Stage 2 — Database & Memory Models

### Task 2: SQLite schema + migration

**Files:**
- Create: `backend/memory/database.py`
- Create: `backend/tests/conftest.py`

- [ ] **Step 1: Write failing test for DB init**

Create `backend/tests/conftest.py`:

```python
import pytest
import pytest_asyncio
import aiosqlite
from memory.database import init_db, get_db_path


@pytest_asyncio.fixture
async def db():
    path = ":memory:"
    async with aiosqlite.connect(path) as conn:
        await init_db(conn)
        yield conn


@pytest.fixture
def anyio_backend():
    return "asyncio"
```

Create `backend/tests/test_memory_store.py` (first test only):

```python
import pytest
import pytest_asyncio
import aiosqlite
from memory.database import init_db


@pytest.mark.asyncio
async def test_init_db_creates_all_tables():
    async with aiosqlite.connect(":memory:") as conn:
        await init_db(conn)
        cursor = await conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        tables = {row[0] for row in await cursor.fetchall()}

    assert "users" in tables
    assert "conversations" in tables
    assert "mood_history" in tables
    assert "mentioned_events" in tables
    assert "habits" in tables
    assert "interaction_preferences" in tables
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend
source venv/bin/activate
python -m pytest tests/test_memory_store.py::test_init_db_creates_all_tables -v
```

Expected: `FAILED — ModuleNotFoundError: No module named 'memory.database'`

- [ ] **Step 3: Create `backend/memory/database.py`**

```python
import aiosqlite
import os

DB_PATH = os.getenv("DATABASE_URL", "alma.db")


def get_db_path() -> str:
    return DB_PATH


async def init_db(conn: aiosqlite.Connection) -> None:
    await conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            telegram_id TEXT UNIQUE,
            name TEXT,
            onboarding_complete INTEGER DEFAULT 0,
            onboarding_step INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            features_used TEXT DEFAULT '[]',
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        );

        CREATE TABLE IF NOT EXISTS mood_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            mood_score REAL NOT NULL,
            events TEXT DEFAULT '[]',
            tone TEXT DEFAULT 'neutral',
            raw_message TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        );

        CREATE TABLE IF NOT EXISTS mentioned_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            event_name TEXT NOT NULL,
            scheduled_date TEXT,
            status TEXT DEFAULT 'pending',
            emotional_weight REAL DEFAULT 5.0,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        );

        CREATE TABLE IF NOT EXISTS habits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            habit_name TEXT NOT NULL,
            frequency_observed TEXT,
            last_occurrence TEXT,
            associated_mood_delta REAL DEFAULT 0.0,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        );

        CREATE TABLE IF NOT EXISTS interaction_preferences (
            user_id TEXT PRIMARY KEY,
            preferred_time TEXT DEFAULT '09:00',
            communication_style TEXT DEFAULT 'coloquial',
            topics_off_limits TEXT DEFAULT '[]',
            topics_important TEXT DEFAULT '[]',
            language TEXT DEFAULT 'es',
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        );
    """)
    await conn.commit()


async def get_connection() -> aiosqlite.Connection:
    conn = await aiosqlite.connect(DB_PATH)
    conn.row_factory = aiosqlite.Row
    await init_db(conn)
    return conn
```

- [ ] **Step 4: Run test to verify it passes**

```bash
python -m pytest tests/test_memory_store.py::test_init_db_creates_all_tables -v
```

Expected: `PASSED`

- [ ] **Step 5: Commit**

```bash
git add backend/memory/database.py backend/tests/
git commit -m "feat: SQLite schema with 6 tables for users, conversations, and 4 memory layers"
```

---

### Task 3: Pydantic memory models

**Files:**
- Create: `backend/memory/models.py`

- [ ] **Step 1: Create `backend/memory/models.py`**

```python
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class User(BaseModel):
    user_id: str
    telegram_id: Optional[str] = None
    name: Optional[str] = None
    onboarding_complete: bool = False
    onboarding_step: int = 0
    created_at: Optional[str] = None


class MoodEntry(BaseModel):
    user_id: str
    mood_score: float = Field(ge=1.0, le=10.0)
    events: list[str] = []
    tone: str = "neutral"
    raw_message: Optional[str] = None
    created_at: Optional[str] = None


class MentionedEvent(BaseModel):
    id: Optional[int] = None
    user_id: str
    event_name: str
    scheduled_date: Optional[str] = None
    status: str = "pending"
    emotional_weight: float = 5.0
    created_at: Optional[str] = None


class Habit(BaseModel):
    id: Optional[int] = None
    user_id: str
    habit_name: str
    frequency_observed: Optional[str] = None
    last_occurrence: Optional[str] = None
    associated_mood_delta: float = 0.0


class InteractionPreferences(BaseModel):
    user_id: str
    preferred_time: str = "09:00"
    communication_style: str = "coloquial"
    topics_off_limits: list[str] = []
    topics_important: list[str] = []
    language: str = "es"


class ContextBundle(BaseModel):
    user: User
    recent_mood: list[MoodEntry] = []
    pending_events: list[MentionedEvent] = []
    habits: list[Habit] = []
    preferences: Optional[InteractionPreferences] = None
    recent_messages: list[dict] = []
```

- [ ] **Step 2: Verify models work (no formal test needed — just import check)**

```bash
python -c "from memory.models import User, MoodEntry, MentionedEvent, Habit, InteractionPreferences, ContextBundle; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/memory/models.py
git commit -m "feat: Pydantic models for all 4 memory layers + ContextBundle"
```

---

### Task 4: MemoryStore — CRUD for all 4 layers

**Files:**
- Create: `backend/memory/store.py`
- Modify: `backend/tests/test_memory_store.py`

- [ ] **Step 1: Add tests for MemoryStore**

Append to `backend/tests/test_memory_store.py`:

```python
import json
import pytest
import pytest_asyncio
import aiosqlite
from memory.database import init_db
from memory.models import User, MoodEntry, MentionedEvent, Habit, InteractionPreferences
from memory.store import MemoryStore


@pytest_asyncio.fixture
async def store():
    async with aiosqlite.connect(":memory:") as conn:
        conn.row_factory = aiosqlite.Row
        await init_db(conn)
        yield MemoryStore(conn)


@pytest.mark.asyncio
async def test_create_and_get_user(store):
    await store.create_user("u1", telegram_id="t123", name="Ana")
    user = await store.get_user("u1")
    assert user.name == "Ana"
    assert user.telegram_id == "t123"
    assert user.onboarding_complete is False


@pytest.mark.asyncio
async def test_add_and_get_mood_history(store):
    await store.create_user("u1")
    entry = MoodEntry(user_id="u1", mood_score=7.5, events=["trabajo"], tone="ansioso")
    await store.add_mood_entry(entry)

    history = await store.get_recent_mood("u1", limit=5)
    assert len(history) == 1
    assert history[0].mood_score == 7.5
    assert "trabajo" in history[0].events


@pytest.mark.asyncio
async def test_add_and_get_pending_events(store):
    await store.create_user("u1")
    event = MentionedEvent(user_id="u1", event_name="entrevista trabajo", scheduled_date="2026-04-25", emotional_weight=8.0)
    await store.add_mentioned_event(event)

    events = await store.get_pending_events("u1")
    assert len(events) == 1
    assert events[0].event_name == "entrevista trabajo"
    assert events[0].status == "pending"


@pytest.mark.asyncio
async def test_mark_event_resolved(store):
    await store.create_user("u1")
    event = MentionedEvent(user_id="u1", event_name="entrevista", scheduled_date="2026-04-25")
    await store.add_mentioned_event(event)
    events = await store.get_pending_events("u1")
    await store.resolve_event(events[0].id)

    pending = await store.get_pending_events("u1")
    assert len(pending) == 0


@pytest.mark.asyncio
async def test_upsert_interaction_preferences(store):
    await store.create_user("u1")
    prefs = InteractionPreferences(user_id="u1", preferred_time="20:00", communication_style="formal")
    await store.upsert_preferences(prefs)

    loaded = await store.get_preferences("u1")
    assert loaded.preferred_time == "20:00"
    assert loaded.communication_style == "formal"

    # Upsert again — update only preferred_time
    prefs2 = InteractionPreferences(user_id="u1", preferred_time="21:00", communication_style="formal")
    await store.upsert_preferences(prefs2)
    loaded2 = await store.get_preferences("u1")
    assert loaded2.preferred_time == "21:00"


@pytest.mark.asyncio
async def test_add_conversation_and_retrieve(store):
    await store.create_user("u1")
    await store.add_message("u1", role="user", content="Hola Alma")
    await store.add_message("u1", role="assistant", content="Hola! ¿Cómo estás?")

    messages = await store.get_recent_messages("u1", limit=10)
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "assistant"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/test_memory_store.py -v --ignore=tests/test_memory_store.py::test_init_db_creates_all_tables -k "not test_init_db"
```

Expected: `FAILED — ModuleNotFoundError: No module named 'memory.store'`

- [ ] **Step 3: Create `backend/memory/store.py`**

```python
import json
import aiosqlite
from typing import Optional
from memory.models import User, MoodEntry, MentionedEvent, Habit, InteractionPreferences


class MemoryStore:
    def __init__(self, conn: aiosqlite.Connection):
        self._conn = conn

    async def create_user(self, user_id: str, telegram_id: str = None, name: str = None) -> User:
        await self._conn.execute(
            "INSERT OR IGNORE INTO users (user_id, telegram_id, name) VALUES (?, ?, ?)",
            (user_id, telegram_id, name),
        )
        await self._conn.commit()
        return await self.get_user(user_id)

    async def get_user(self, user_id: str) -> Optional[User]:
        cursor = await self._conn.execute(
            "SELECT * FROM users WHERE user_id = ?", (user_id,)
        )
        row = await cursor.fetchone()
        if not row:
            return None
        return User(
            user_id=row["user_id"],
            telegram_id=row["telegram_id"],
            name=row["name"],
            onboarding_complete=bool(row["onboarding_complete"]),
            onboarding_step=row["onboarding_step"],
            created_at=row["created_at"],
        )

    async def get_user_by_telegram_id(self, telegram_id: str) -> Optional[User]:
        cursor = await self._conn.execute(
            "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
        )
        row = await cursor.fetchone()
        if not row:
            return None
        return User(
            user_id=row["user_id"],
            telegram_id=row["telegram_id"],
            name=row["name"],
            onboarding_complete=bool(row["onboarding_complete"]),
            onboarding_step=row["onboarding_step"],
            created_at=row["created_at"],
        )

    async def update_onboarding_step(self, user_id: str, step: int, complete: bool = False) -> None:
        await self._conn.execute(
            "UPDATE users SET onboarding_step = ?, onboarding_complete = ? WHERE user_id = ?",
            (step, 1 if complete else 0, user_id),
        )
        await self._conn.commit()

    async def update_user_name(self, user_id: str, name: str) -> None:
        await self._conn.execute(
            "UPDATE users SET name = ? WHERE user_id = ?", (name, user_id)
        )
        await self._conn.commit()

    async def get_all_active_users(self) -> list[User]:
        cursor = await self._conn.execute(
            "SELECT * FROM users WHERE onboarding_complete = 1"
        )
        rows = await cursor.fetchall()
        return [
            User(
                user_id=r["user_id"],
                telegram_id=r["telegram_id"],
                name=r["name"],
                onboarding_complete=bool(r["onboarding_complete"]),
                onboarding_step=r["onboarding_step"],
            )
            for r in rows
        ]

    # ── Mood History ─────────────────────────────────────────────────────────

    async def add_mood_entry(self, entry: MoodEntry) -> None:
        await self._conn.execute(
            """INSERT INTO mood_history (user_id, mood_score, events, tone, raw_message)
               VALUES (?, ?, ?, ?, ?)""",
            (
                entry.user_id,
                entry.mood_score,
                json.dumps(entry.events),
                entry.tone,
                entry.raw_message,
            ),
        )
        await self._conn.commit()

    async def get_recent_mood(self, user_id: str, limit: int = 14) -> list[MoodEntry]:
        cursor = await self._conn.execute(
            """SELECT * FROM mood_history WHERE user_id = ?
               ORDER BY created_at DESC LIMIT ?""",
            (user_id, limit),
        )
        rows = await cursor.fetchall()
        return [
            MoodEntry(
                user_id=r["user_id"],
                mood_score=r["mood_score"],
                events=json.loads(r["events"]),
                tone=r["tone"],
                raw_message=r["raw_message"],
                created_at=r["created_at"],
            )
            for r in rows
        ]

    async def get_average_mood(self, user_id: str, days: int = 7) -> Optional[float]:
        cursor = await self._conn.execute(
            """SELECT AVG(mood_score) as avg FROM mood_history
               WHERE user_id = ? AND created_at >= datetime('now', ?)""",
            (user_id, f"-{days} days"),
        )
        row = await cursor.fetchone()
        return row["avg"] if row and row["avg"] is not None else None

    # ── Mentioned Events ─────────────────────────────────────────────────────

    async def add_mentioned_event(self, event: MentionedEvent) -> None:
        await self._conn.execute(
            """INSERT INTO mentioned_events (user_id, event_name, scheduled_date, status, emotional_weight)
               VALUES (?, ?, ?, ?, ?)""",
            (event.user_id, event.event_name, event.scheduled_date, event.status, event.emotional_weight),
        )
        await self._conn.commit()

    async def get_pending_events(self, user_id: str) -> list[MentionedEvent]:
        cursor = await self._conn.execute(
            "SELECT * FROM mentioned_events WHERE user_id = ? AND status = 'pending' ORDER BY created_at DESC",
            (user_id,),
        )
        rows = await cursor.fetchall()
        return [
            MentionedEvent(
                id=r["id"],
                user_id=r["user_id"],
                event_name=r["event_name"],
                scheduled_date=r["scheduled_date"],
                status=r["status"],
                emotional_weight=r["emotional_weight"],
                created_at=r["created_at"],
            )
            for r in rows
        ]

    async def resolve_event(self, event_id: int) -> None:
        await self._conn.execute(
            "UPDATE mentioned_events SET status = 'resolved' WHERE id = ?", (event_id,)
        )
        await self._conn.commit()

    # ── Habits ───────────────────────────────────────────────────────────────

    async def upsert_habit(self, habit: Habit) -> None:
        await self._conn.execute(
            """INSERT INTO habits (user_id, habit_name, frequency_observed, last_occurrence, associated_mood_delta)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(rowid) DO UPDATE SET
                 frequency_observed = excluded.frequency_observed,
                 last_occurrence = excluded.last_occurrence""",
            (habit.user_id, habit.habit_name, habit.frequency_observed, habit.last_occurrence, habit.associated_mood_delta),
        )
        await self._conn.commit()

    async def get_habits(self, user_id: str) -> list[Habit]:
        cursor = await self._conn.execute(
            "SELECT * FROM habits WHERE user_id = ?", (user_id,)
        )
        rows = await cursor.fetchall()
        return [
            Habit(
                id=r["id"],
                user_id=r["user_id"],
                habit_name=r["habit_name"],
                frequency_observed=r["frequency_observed"],
                last_occurrence=r["last_occurrence"],
                associated_mood_delta=r["associated_mood_delta"],
            )
            for r in rows
        ]

    # ── Interaction Preferences ───────────────────────────────────────────────

    async def upsert_preferences(self, prefs: InteractionPreferences) -> None:
        await self._conn.execute(
            """INSERT INTO interaction_preferences
               (user_id, preferred_time, communication_style, topics_off_limits, topics_important, language)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(user_id) DO UPDATE SET
                 preferred_time = excluded.preferred_time,
                 communication_style = excluded.communication_style,
                 topics_off_limits = excluded.topics_off_limits,
                 topics_important = excluded.topics_important,
                 language = excluded.language""",
            (
                prefs.user_id,
                prefs.preferred_time,
                prefs.communication_style,
                json.dumps(prefs.topics_off_limits),
                json.dumps(prefs.topics_important),
                prefs.language,
            ),
        )
        await self._conn.commit()

    async def get_preferences(self, user_id: str) -> Optional[InteractionPreferences]:
        cursor = await self._conn.execute(
            "SELECT * FROM interaction_preferences WHERE user_id = ?", (user_id,)
        )
        row = await cursor.fetchone()
        if not row:
            return InteractionPreferences(user_id=user_id)
        return InteractionPreferences(
            user_id=row["user_id"],
            preferred_time=row["preferred_time"],
            communication_style=row["communication_style"],
            topics_off_limits=json.loads(row["topics_off_limits"]),
            topics_important=json.loads(row["topics_important"]),
            language=row["language"],
        )

    # ── Conversations ────────────────────────────────────────────────────────

    async def add_message(self, user_id: str, role: str, content: str, features_used: list[str] = None) -> None:
        await self._conn.execute(
            "INSERT INTO conversations (user_id, role, content, features_used) VALUES (?, ?, ?, ?)",
            (user_id, role, content, json.dumps(features_used or [])),
        )
        await self._conn.commit()

    async def get_recent_messages(self, user_id: str, limit: int = 20) -> list[dict]:
        cursor = await self._conn.execute(
            """SELECT role, content, features_used, created_at FROM conversations
               WHERE user_id = ? ORDER BY created_at ASC LIMIT ?""",
            (user_id, limit),
        )
        rows = await cursor.fetchall()
        return [
            {
                "role": r["role"],
                "content": r["content"],
                "features_used": json.loads(r["features_used"]),
                "created_at": r["created_at"],
            }
            for r in rows
        ]

    async def get_last_user_message_time(self, user_id: str) -> Optional[str]:
        cursor = await self._conn.execute(
            """SELECT created_at FROM conversations WHERE user_id = ? AND role = 'user'
               ORDER BY created_at DESC LIMIT 1""",
            (user_id,),
        )
        row = await cursor.fetchone()
        return row["created_at"] if row else None

    async def count_proactive_today(self, user_id: str) -> int:
        cursor = await self._conn.execute(
            """SELECT COUNT(*) as cnt FROM conversations
               WHERE user_id = ? AND role = 'assistant'
               AND json_extract(features_used, '$[0]') = 'proactive'
               AND created_at >= date('now')""",
            (user_id,),
        )
        row = await cursor.fetchone()
        return row["cnt"] if row else 0
```

- [ ] **Step 4: Run all memory store tests**

```bash
python -m pytest tests/test_memory_store.py -v
```

Expected: All 7 tests `PASSED`

- [ ] **Step 5: Commit**

```bash
git add backend/memory/store.py backend/tests/test_memory_store.py
git commit -m "feat: MemoryStore with full CRUD for users, mood, events, habits, preferences, conversations"
```

---

### Task 5: ContextBuilder

**Files:**
- Create: `backend/memory/context.py`
- Create: `backend/tests/test_context_builder.py`

- [ ] **Step 1: Write failing test**

Create `backend/tests/test_context_builder.py`:

```python
import pytest
import pytest_asyncio
import aiosqlite
from memory.database import init_db
from memory.store import MemoryStore
from memory.models import MoodEntry, MentionedEvent, InteractionPreferences
from memory.context import ContextBuilder, build_memory_summary


@pytest_asyncio.fixture
async def populated_store():
    async with aiosqlite.connect(":memory:") as conn:
        conn.row_factory = aiosqlite.Row
        await init_db(conn)
        store = MemoryStore(conn)
        await store.create_user("u1", telegram_id="t1", name="Ricardo")
        await store.add_mood_entry(MoodEntry(user_id="u1", mood_score=4.5, tone="triste", raw_message="me siento mal"))
        await store.add_mood_entry(MoodEntry(user_id="u1", mood_score=6.0, tone="neutral", raw_message="más o menos"))
        await store.add_mentioned_event(MentionedEvent(user_id="u1", event_name="entrevista de trabajo", scheduled_date="2026-04-25", emotional_weight=8.5))
        await store.upsert_preferences(InteractionPreferences(user_id="u1", preferred_time="09:00", communication_style="coloquial"))
        await store.add_message("u1", "user", "Hola Alma")
        await store.add_message("u1", "assistant", "Hola Ricardo!")
        yield store


@pytest.mark.asyncio
async def test_build_context_includes_user_name(populated_store):
    builder = ContextBuilder(populated_store)
    ctx = await builder.build("u1", "¿qué onda?")
    assert ctx.user.name == "Ricardo"


@pytest.mark.asyncio
async def test_build_context_includes_recent_mood(populated_store):
    builder = ContextBuilder(populated_store)
    ctx = await builder.build("u1", "¿qué onda?")
    assert len(ctx.recent_mood) == 2
    assert ctx.recent_mood[0].mood_score == 6.0


@pytest.mark.asyncio
async def test_build_context_includes_pending_events(populated_store):
    builder = ContextBuilder(populated_store)
    ctx = await builder.build("u1", "¿qué onda?")
    assert len(ctx.pending_events) == 1
    assert ctx.pending_events[0].event_name == "entrevista de trabajo"


@pytest.mark.asyncio
async def test_build_context_includes_preferences(populated_store):
    builder = ContextBuilder(populated_store)
    ctx = await builder.build("u1", "¿qué onda?")
    assert ctx.preferences.communication_style == "coloquial"


@pytest.mark.asyncio
async def test_memory_summary_contains_name_and_mood(populated_store):
    builder = ContextBuilder(populated_store)
    ctx = await builder.build("u1", "test")
    summary = build_memory_summary(ctx)
    assert "Ricardo" in summary
    assert "4.5" in summary or "triste" in summary
```

- [ ] **Step 2: Run to verify failure**

```bash
python -m pytest tests/test_context_builder.py -v
```

Expected: `FAILED — ModuleNotFoundError: No module named 'memory.context'`

- [ ] **Step 3: Create `backend/memory/context.py`**

```python
from memory.store import MemoryStore
from memory.models import ContextBundle


class ContextBuilder:
    def __init__(self, store: MemoryStore):
        self._store = store

    async def build(self, user_id: str, current_message: str) -> ContextBundle:
        user = await self._store.get_user(user_id)
        recent_mood = await self._store.get_recent_mood(user_id, limit=14)
        pending_events = await self._store.get_pending_events(user_id)
        habits = await self._store.get_habits(user_id)
        preferences = await self._store.get_preferences(user_id)
        recent_messages = await self._store.get_recent_messages(user_id, limit=20)

        return ContextBundle(
            user=user,
            recent_mood=recent_mood,
            pending_events=pending_events,
            habits=habits,
            preferences=preferences,
            recent_messages=recent_messages,
        )


def build_memory_summary(ctx: ContextBundle) -> str:
    lines = []
    name = ctx.user.name or "el usuario"
    lines.append(f"Usuario: {name}")

    if ctx.recent_mood:
        scores = [m.mood_score for m in ctx.recent_mood]
        avg = sum(scores) / len(scores)
        latest = ctx.recent_mood[0]
        lines.append(f"Estado emocional reciente: promedio {avg:.1f}/10, último tono: {latest.tone} (score {latest.mood_score})")
        if latest.raw_message:
            lines.append(f"  Último mensaje: \"{latest.raw_message}\"")

    if ctx.pending_events:
        events_str = ", ".join(
            f"{e.event_name} (peso emocional {e.emotional_weight})" + (f" el {e.scheduled_date}" if e.scheduled_date else "")
            for e in ctx.pending_events[:3]
        )
        lines.append(f"Eventos pendientes: {events_str}")

    if ctx.habits:
        habits_str = ", ".join(h.habit_name for h in ctx.habits[:3])
        lines.append(f"Hábitos detectados: {habits_str}")

    if ctx.preferences:
        p = ctx.preferences
        lines.append(f"Preferencias: hora preferida {p.preferred_time}, estilo {p.communication_style}, idioma {p.language}")
        if p.topics_off_limits:
            lines.append(f"  Temas off-limits: {', '.join(p.topics_off_limits)}")

    return "\n".join(lines)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/test_context_builder.py -v
```

Expected: All 5 tests `PASSED`

- [ ] **Step 5: Commit**

```bash
git add backend/memory/context.py backend/tests/test_context_builder.py
git commit -m "feat: ContextBuilder assembles 4-layer memory into ContextBundle for agent prompt"
```

---

## Stage 3 — Alma Agent

### Task 6: System prompts & templates

**Files:**
- Create: `backend/alma/prompts.py`

- [ ] **Step 1: Create `backend/alma/prompts.py`**

```python
ALMA_SYSTEM_PROMPT = """Eres Alma, un companion de bienestar proactivo que vive en Telegram.

PERSONALIDAD:
- Cálida pero directa — no condescendiente ni excesivamente positiva
- Recuerdas detalles específicos de conversaciones anteriores y los usas naturalmente
- Haces UNA sola pregunta por mensaje, nunca abrumas con varias preguntas
- No das consejos no pedidos — escuchas primero
- No usas jerga psicológica ni frases de autoayuda genéricas
- No pretendes ser terapeuta — eres un companion que se preocupa genuinamente

REGLAS DE RESPUESTA:
1. Si el usuario menciona algo importante (evento, persona, situación), recuérdalo y pregunta después
2. Mantén respuestas entre 1-3 oraciones en conversaciones normales. Solo más largas si el usuario lo necesita.
3. Nunca empieces con "¡" — suena artificial
4. Si detectas tristeza o ansiedad, valida primero antes de preguntar
5. Nunca des diagnósticos ni nombres de condiciones mentales
6. Si el usuario dice que quiere hablar con una persona real, ofrece la escalada a voluntario

SOBRE LA MEMORIA:
Tienes acceso a la historia emocional del usuario y eventos que mencionó. Úsalos naturalmente.
Ejemplo correcto: "La semana pasada mencionaste que tenías esa entrevista. ¿Cómo te fue?"
Ejemplo incorrecto: "Según mis registros, el 22 de abril mencionaste una entrevista..."
"""

ONBOARDING_SYSTEM_PROMPT = """Eres Alma. Estás conociendo a una persona nueva.

Tu objetivo es extraer 5 datos clave en una conversación NATURAL — sin que parezca un formulario:
1. Nombre preferido
2. Horario preferido para mensajes (mañana / tarde / noche)
3. Contexto emocional actual (cómo están en este momento)
4. Estilo de comunicación que prefieren (formal / informal)
5. Si hay temas que prefieren no tocar

Instrucciones:
- Empieza presentándote brevemente y preguntando el nombre
- Haz una pregunta a la vez
- Si el usuario da información adicional no pedida, úsala (no la ignores)
- El onboarding termina cuando tienes los 5 datos — di algo cálido de cierre

Responde siempre en el idioma que usa el usuario.
"""

CRISIS_EVALUATION_PROMPT = """Evalúa el riesgo de crisis emocional en este mensaje.

Responde SOLO con un JSON:
{
  "risk_score": <float 0.0-1.0>,
  "risk_level": "<none|low|medium|high|critical>",
  "signals": [<lista de señales detectadas>],
  "recommended_action": "<continue|monitor|gentle_check|direct_question|escalate>"
}

Niveles:
- none (0.0-0.2): mensaje normal, sin señales
- low (0.2-0.4): algo de tristeza/estrés, normal
- medium (0.4-0.6): frustración intensa, aislamiento mencionado
- high (0.6-0.85): desesperanza, frases de rendirse, llanto intenso
- critical (0.85-1.0): ideación suicida explícita o implícita, autolesión

Señales a detectar: "ya no quiero", "para qué todo", "nadie me importa", "quiero desaparecer",
"me voy a hacer daño", "no tiene sentido seguir", "mejor sin mí", "estoy muy solo".
"""

PROACTIVITY_DECISION_PROMPT = """Decides si Alma debe enviar un mensaje proactivo a este usuario ahora.

Responde SOLO con JSON:
{
  "should_send": <true|false>,
  "reason": "<por qué sí o no>",
  "message_type": "<morning_checkin|event_followup|anomaly_check|post_crisis_followup|null>",
  "suggested_opening": "<primer mensaje sugerido, máx 2 oraciones, o null>"
}

Criterios para enviar:
- Han pasado más de 20 horas desde el último mensaje del usuario Y es su hora preferida
- Hay un evento pendiente con scheduled_date = hoy
- El usuario normalmente responde en <4h pero lleva >12h sin responder
- Hubo una crisis en las últimas 48h (seguimiento)

Criterios para NO enviar:
- El usuario respondió hace menos de 4 horas
- Ya se enviaron 2+ mensajes proactivos hoy sin respuesta
- Es fuera del horario preferido del usuario (±2h)
"""

VOLUNTEER_BRIEF_PROMPT = """Genera un brief estructurado para un voluntario que va a hablar con este usuario.
El voluntario no conoce al usuario — necesita contexto para ser útil desde el primer mensaje.

Incluye:
1. Nombre del usuario
2. Resumen del estado emocional actual (2-3 oraciones)
3. Lo que activó la escalada (cita textual si aplica)
4. Historial emocional de las últimas 2 semanas (tendencia)
5. Eventos importantes mencionados recientemente
6. Recomendación de tono para el voluntario

Sé directo y clínico — este brief es para el voluntario, no para el usuario.
"""

ONBOARDING_EXTRACT_PROMPT = """Extrae información de onboarding de esta conversación.

Responde SOLO con JSON (usa null si no se mencionó):
{
  "name": "<nombre preferido o null>",
  "preferred_time": "<HH:MM en formato 24h o null, inferido de 'mañana'=09:00, 'tarde'=15:00, 'noche'=20:00>",
  "communication_style": "<formal|coloquial|mixto — inferido del tono del usuario>",
  "topics_off_limits": [<lista de temas mencionados como sensibles, puede estar vacía>],
  "current_emotional_state": "<descripción breve de cómo está emocionalmente ahora>",
  "onboarding_complete": <true si se obtuvieron nombre + horario + estilo, false si no>
}
"""

def build_chat_prompt(context_summary: str, conversation_history: list[dict], current_message: str) -> list[dict]:
    messages = []
    if context_summary:
        messages.append({
            "role": "user",
            "content": f"[CONTEXTO DE MEMORIA — no mencionarlo directamente]\n{context_summary}\n[FIN CONTEXTO]"
        })
        messages.append({
            "role": "assistant",
            "content": "Entendido, tengo el contexto."
        })

    for msg in conversation_history[-10:]:
        messages.append({"role": msg["role"], "content": msg["content"]})

    messages.append({"role": "user", "content": current_message})
    return messages
```

- [ ] **Step 2: Verify import**

```bash
python -c "from alma.prompts import ALMA_SYSTEM_PROMPT, build_chat_prompt; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/alma/prompts.py
git commit -m "feat: Alma system prompts for chat, onboarding, crisis detection, proactivity, volunteer brief"
```

---

### Task 7: Alma conversational agent

**Files:**
- Create: `backend/alma/agent.py`
- Create: `backend/tests/test_agent.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_agent.py`:

```python
import pytest
import pytest_asyncio
import aiosqlite
from unittest.mock import AsyncMock, MagicMock, patch
from memory.database import init_db
from memory.store import MemoryStore
from memory.models import ContextBundle, User, InteractionPreferences
from memory.context import ContextBuilder
from alma.agent import AlmaAgent, AlmaResponse


@pytest_asyncio.fixture
async def store_with_user():
    async with aiosqlite.connect(":memory:") as conn:
        conn.row_factory = aiosqlite.Row
        await init_db(conn)
        store = MemoryStore(conn)
        await store.create_user("u1", telegram_id="t1", name="Ana")
        await store.upsert_preferences(InteractionPreferences(user_id="u1"))
        yield store


@pytest.mark.asyncio
async def test_generate_response_returns_alma_response(store_with_user):
    mock_client = MagicMock()
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text="Hola Ana, ¿cómo estás hoy?")]
    mock_client.messages.create.return_value = mock_message

    agent = AlmaAgent(anthropic_client=mock_client, store=store_with_user)
    result = await agent.respond("u1", "Hola")

    assert isinstance(result, AlmaResponse)
    assert result.text == "Hola Ana, ¿cómo estás hoy?"
    assert "conversation" in result.features_used


@pytest.mark.asyncio
async def test_respond_saves_messages_to_store(store_with_user):
    mock_client = MagicMock()
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text="Hola!")]
    mock_client.messages.create.return_value = mock_message

    agent = AlmaAgent(anthropic_client=mock_client, store=store_with_user)
    await agent.respond("u1", "Hola Alma")

    messages = await store_with_user.get_recent_messages("u1", limit=10)
    roles = [m["role"] for m in messages]
    assert "user" in roles
    assert "assistant" in roles


@pytest.mark.asyncio
async def test_respond_includes_memory_context_in_prompt(store_with_user):
    from memory.models import MoodEntry
    await store_with_user.add_mood_entry(MoodEntry(user_id="u1", mood_score=3.0, tone="triste", raw_message="tuve un dia horrible"))

    mock_client = MagicMock()
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text="Te escucho.")]
    mock_client.messages.create.return_value = mock_message

    agent = AlmaAgent(anthropic_client=mock_client, store=store_with_user)
    await agent.respond("u1", "me siento mal")

    call_args = mock_client.messages.create.call_args
    messages_sent = call_args.kwargs["messages"]
    full_text = " ".join(m["content"] for m in messages_sent)
    assert "Ana" in full_text or "triste" in full_text
```

- [ ] **Step 2: Run to verify failure**

```bash
python -m pytest tests/test_agent.py -v
```

Expected: `FAILED — ModuleNotFoundError: No module named 'alma.agent'`

- [ ] **Step 3: Create `backend/alma/agent.py`**

```python
from dataclasses import dataclass, field
from typing import Optional
import anthropic
from memory.store import MemoryStore
from memory.context import ContextBuilder, build_memory_summary
from memory.models import MoodEntry
from alma.prompts import ALMA_SYSTEM_PROMPT, build_chat_prompt


@dataclass
class AlmaResponse:
    text: str
    features_used: list[str] = field(default_factory=list)
    mood_inferred: Optional[float] = None


class AlmaAgent:
    def __init__(self, anthropic_client: anthropic.Anthropic, store: MemoryStore):
        self._client = anthropic_client
        self._store = store
        self._context_builder = ContextBuilder(store)

    async def respond(self, user_id: str, message: str) -> AlmaResponse:
        ctx = await self._context_builder.build(user_id, message)
        summary = build_memory_summary(ctx)
        messages = build_chat_prompt(summary, ctx.recent_messages, message)

        response = self._client.messages.create(
            model="claude-opus-4-7",
            max_tokens=512,
            system=ALMA_SYSTEM_PROMPT,
            messages=messages,
        )

        reply_text = response.content[0].text

        await self._store.add_message(user_id, "user", message, features_used=["conversation"])
        await self._store.add_message(user_id, "assistant", reply_text, features_used=["conversation", "memory_store"])

        mood_score = await self._infer_mood_score(message)
        if mood_score is not None:
            await self._store.add_mood_entry(
                MoodEntry(user_id=user_id, mood_score=mood_score, raw_message=message)
            )

        return AlmaResponse(
            text=reply_text,
            features_used=["conversation", "memory_store"],
            mood_inferred=mood_score,
        )

    async def _infer_mood_score(self, message: str) -> Optional[float]:
        low_keywords = ["mal", "terrible", "horrible", "triste", "llorar", "solo", "ansiedad", "angustia", "no puedo más"]
        high_keywords = ["bien", "genial", "feliz", "contento", "alegre", "emocionado", "logré"]

        text = message.lower()
        if any(k in text for k in low_keywords):
            return 3.0
        if any(k in text for k in high_keywords):
            return 8.0
        return 5.0
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_agent.py -v
```

Expected: All 3 tests `PASSED`

- [ ] **Step 5: Commit**

```bash
git add backend/alma/agent.py backend/tests/test_agent.py
git commit -m "feat: AlmaAgent generates responses using Opus 4.7 with 4-layer memory context"
```

---

### Task 8: Onboarding state machine

**Files:**
- Create: `backend/alma/onboarding.py`
- Create: `backend/tests/test_onboarding.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_onboarding.py`:

```python
import pytest
import pytest_asyncio
import aiosqlite
from unittest.mock import MagicMock
from memory.database import init_db
from memory.store import MemoryStore
from alma.onboarding import OnboardingAgent, OnboardingResult


@pytest_asyncio.fixture
async def store():
    async with aiosqlite.connect(":memory:") as conn:
        conn.row_factory = aiosqlite.Row
        await init_db(conn)
        s = MemoryStore(conn)
        await s.create_user("u1", telegram_id="t1")
        yield s


@pytest.mark.asyncio
async def test_first_message_returns_greeting(store):
    mock_client = MagicMock()
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text="Hola! Soy Alma. ¿Cómo te llamas?")]
    )
    agent = OnboardingAgent(mock_client, store)
    result = await agent.process("u1", "hola")
    assert isinstance(result, OnboardingResult)
    assert result.reply != ""
    assert result.complete is False


@pytest.mark.asyncio
async def test_extract_name_from_response(store):
    mock_client = MagicMock()
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text='{"name": "Luis", "preferred_time": null, "communication_style": "coloquial", "topics_off_limits": [], "current_emotional_state": null, "onboarding_complete": false}')]
    )
    agent = OnboardingAgent(mock_client, store)
    await agent._extract_and_save("u1", "Me llamo Luis")
    user = await store.get_user("u1")
    assert user.name == "Luis"


@pytest.mark.asyncio
async def test_onboarding_complete_when_all_data_extracted(store):
    mock_client = MagicMock()
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text='{"name": "María", "preferred_time": "09:00", "communication_style": "coloquial", "topics_off_limits": [], "current_emotional_state": "bien", "onboarding_complete": true}')]
    )
    agent = OnboardingAgent(mock_client, store)
    result = await agent._extract_and_save("u1", "Soy María, prefiero mañanas")
    assert result is True

    user = await store.get_user("u1")
    assert user.name == "María"
```

- [ ] **Step 2: Run to verify failure**

```bash
python -m pytest tests/test_onboarding.py -v
```

Expected: `FAILED — ModuleNotFoundError: No module named 'alma.onboarding'`

- [ ] **Step 3: Create `backend/alma/onboarding.py`**

```python
import json
from dataclasses import dataclass
from typing import Optional
import anthropic
from memory.store import MemoryStore
from memory.models import InteractionPreferences, MoodEntry
from alma.prompts import ONBOARDING_SYSTEM_PROMPT, ONBOARDING_EXTRACT_PROMPT


@dataclass
class OnboardingResult:
    reply: str
    complete: bool


class OnboardingAgent:
    def __init__(self, client: anthropic.Anthropic, store: MemoryStore):
        self._client = client
        self._store = store

    async def process(self, user_id: str, message: str) -> OnboardingResult:
        user = await self._store.get_user(user_id)
        history = await self._store.get_recent_messages(user_id, limit=20)

        messages = [{"role": m["role"], "content": m["content"]} for m in history]
        messages.append({"role": "user", "content": message})

        response = self._client.messages.create(
            model="claude-opus-4-7",
            max_tokens=256,
            system=ONBOARDING_SYSTEM_PROMPT,
            messages=messages,
        )
        reply = response.content[0].text

        await self._store.add_message(user_id, "user", message)
        await self._store.add_message(user_id, "assistant", reply)

        complete = await self._extract_and_save(user_id, message)

        if complete:
            await self._store.update_onboarding_step(user_id, step=5, complete=True)

        return OnboardingResult(reply=reply, complete=complete)

    async def _extract_and_save(self, user_id: str, message: str) -> bool:
        history = await self._store.get_recent_messages(user_id, limit=10)
        conversation_text = "\n".join(f"{m['role']}: {m['content']}" for m in history)

        response = self._client.messages.create(
            model="claude-opus-4-7",
            max_tokens=256,
            system=ONBOARDING_EXTRACT_PROMPT,
            messages=[{"role": "user", "content": f"Conversación:\n{conversation_text}\n\nÚltimo mensaje del usuario: {message}"}],
        )

        try:
            data = json.loads(response.content[0].text)
        except (json.JSONDecodeError, IndexError):
            return False

        if data.get("name"):
            await self._store.update_user_name(user_id, data["name"])

        prefs = InteractionPreferences(
            user_id=user_id,
            preferred_time=data.get("preferred_time") or "09:00",
            communication_style=data.get("communication_style") or "coloquial",
            topics_off_limits=data.get("topics_off_limits") or [],
        )
        await self._store.upsert_preferences(prefs)

        if data.get("current_emotional_state"):
            await self._store.add_mood_entry(
                MoodEntry(user_id=user_id, mood_score=5.0, tone=data["current_emotional_state"])
            )

        return bool(data.get("onboarding_complete", False))
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_onboarding.py -v
```

Expected: All 3 tests `PASSED`

- [ ] **Step 5: Commit**

```bash
git add backend/alma/onboarding.py backend/tests/test_onboarding.py
git commit -m "feat: OnboardingAgent — 5-question conversational onboarding extracts name, time, style, limits"
```

---

## Stage 4 — Crisis Detection

### Task 9: Crisis detector

**Files:**
- Create: `backend/crisis/detector.py`
- Create: `backend/tests/test_crisis.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_crisis.py`:

```python
import pytest
import pytest_asyncio
import aiosqlite
from unittest.mock import MagicMock
from memory.database import init_db
from memory.store import MemoryStore
from memory.models import MoodEntry
from crisis.detector import CrisisDetector, CrisisResult, RiskLevel


@pytest_asyncio.fixture
async def store():
    async with aiosqlite.connect(":memory:") as conn:
        conn.row_factory = aiosqlite.Row
        await init_db(conn)
        s = MemoryStore(conn)
        await s.create_user("u1", name="Ana")
        yield s


def make_mock_client(risk_json: str) -> MagicMock:
    mock = MagicMock()
    mock.messages.create.return_value = MagicMock(
        content=[MagicMock(text=risk_json)]
    )
    return mock


@pytest.mark.asyncio
async def test_normal_message_returns_none_risk(store):
    client = make_mock_client('{"risk_score": 0.1, "risk_level": "none", "signals": [], "recommended_action": "continue"}')
    detector = CrisisDetector(client, store)
    result = await detector.evaluate("u1", "hoy tuve un día tranquilo")
    assert result.level == RiskLevel.NONE
    assert result.should_escalate is False


@pytest.mark.asyncio
async def test_crisis_message_returns_critical_risk(store):
    client = make_mock_client('{"risk_score": 0.9, "risk_level": "critical", "signals": ["ideacion suicida"], "recommended_action": "escalate"}')
    detector = CrisisDetector(client, store)
    result = await detector.evaluate("u1", "ya no quiero seguir aquí")
    assert result.level == RiskLevel.CRITICAL
    assert result.should_escalate is True


@pytest.mark.asyncio
async def test_high_risk_triggers_gentle_check(store):
    client = make_mock_client('{"risk_score": 0.7, "risk_level": "high", "signals": ["desesperanza"], "recommended_action": "direct_question"}')
    detector = CrisisDetector(client, store)
    result = await detector.evaluate("u1", "para qué todo si nada cambia")
    assert result.level == RiskLevel.HIGH
    assert result.recommended_action == "direct_question"


@pytest.mark.asyncio
async def test_generate_volunteer_brief_contains_user_name(store):
    await store.add_mood_entry(MoodEntry(user_id="u1", mood_score=3.0, tone="triste"))
    client = make_mock_client("Brief: Ana está en crisis...")
    detector = CrisisDetector(client, store)
    brief = await detector.generate_volunteer_brief("u1", "no quiero seguir")
    assert brief != ""
    assert len(brief) > 10
```

- [ ] **Step 2: Run to verify failure**

```bash
python -m pytest tests/test_crisis.py -v
```

Expected: `FAILED — ModuleNotFoundError: No module named 'crisis.detector'`

- [ ] **Step 3: Create `backend/crisis/detector.py`**

```python
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import anthropic
from memory.store import MemoryStore
from memory.context import ContextBuilder, build_memory_summary
from alma.prompts import CRISIS_EVALUATION_PROMPT, VOLUNTEER_BRIEF_PROMPT


class RiskLevel(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class CrisisResult:
    level: RiskLevel
    score: float
    signals: list[str] = field(default_factory=list)
    recommended_action: str = "continue"

    @property
    def should_escalate(self) -> bool:
        return self.level in (RiskLevel.HIGH, RiskLevel.CRITICAL)

    @property
    def should_ask_direct_question(self) -> bool:
        return self.recommended_action == "direct_question"


class CrisisDetector:
    def __init__(self, client: anthropic.Anthropic, store: MemoryStore):
        self._client = client
        self._store = store
        self._context_builder = ContextBuilder(store)

    async def evaluate(self, user_id: str, message: str) -> CrisisResult:
        ctx = await self._context_builder.build(user_id, message)
        summary = build_memory_summary(ctx)

        prompt = f"Contexto del usuario:\n{summary}\n\nMensaje a evaluar: \"{message}\""

        response = self._client.messages.create(
            model="claude-opus-4-7",
            max_tokens=256,
            system=CRISIS_EVALUATION_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )

        try:
            data = json.loads(response.content[0].text)
            return CrisisResult(
                level=RiskLevel(data.get("risk_level", "none")),
                score=float(data.get("risk_score", 0.0)),
                signals=data.get("signals", []),
                recommended_action=data.get("recommended_action", "continue"),
            )
        except (json.JSONDecodeError, ValueError, KeyError):
            return CrisisResult(level=RiskLevel.NONE, score=0.0)

    async def generate_volunteer_brief(self, user_id: str, trigger_message: str) -> str:
        ctx = await self._context_builder.build(user_id, trigger_message)
        summary = build_memory_summary(ctx)

        prompt = f"Información del usuario:\n{summary}\n\nMensaje que activó la escalada: \"{trigger_message}\""

        response = self._client.messages.create(
            model="claude-opus-4-7",
            max_tokens=512,
            system=VOLUNTEER_BRIEF_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_crisis.py -v
```

Expected: All 4 tests `PASSED`

- [ ] **Step 5: Commit**

```bash
git add backend/crisis/detector.py backend/tests/test_crisis.py
git commit -m "feat: CrisisDetector evaluates risk 0-1, generates volunteer brief via Opus 4.7"
```

---

## Stage 5 — Proactivity Engine

### Task 10: Proactivity decision + message generation

**Files:**
- Create: `backend/scheduler/proactivity.py`
- Create: `backend/tests/test_proactivity.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_proactivity.py`:

```python
import pytest
import pytest_asyncio
import aiosqlite
from unittest.mock import MagicMock
from datetime import datetime, timedelta
from memory.database import init_db
from memory.store import MemoryStore
from memory.models import InteractionPreferences, MentionedEvent
from scheduler.proactivity import ProactivityEngine, ProactDecision


@pytest_asyncio.fixture
async def store():
    async with aiosqlite.connect(":memory:") as conn:
        conn.row_factory = aiosqlite.Row
        await init_db(conn)
        s = MemoryStore(conn)
        await s.create_user("u1", telegram_id="t1", name="Pedro")
        await s.upsert_preferences(InteractionPreferences(user_id="u1", preferred_time="09:00"))
        yield s


def make_client(should_send: bool, message_type: str = "morning_checkin", opening: str = "¿Cómo amaneciste?") -> MagicMock:
    mock = MagicMock()
    mock.messages.create.return_value = MagicMock(
        content=[MagicMock(text=f'{{"should_send": {str(should_send).lower()}, "reason": "test", "message_type": "{message_type}", "suggested_opening": "{opening}"}}')]
    )
    return mock


@pytest.mark.asyncio
async def test_should_not_proact_when_user_responded_recently(store):
    await store.add_message("u1", "user", "hola")
    client = make_client(False)
    engine = ProactivityEngine(client, store, telegram_token="fake")
    decision = await engine.should_proact("u1")
    assert isinstance(decision, ProactDecision)


@pytest.mark.asyncio
async def test_should_proact_when_event_is_today(store):
    today = datetime.now().strftime("%Y-%m-%d")
    await store.add_mentioned_event(MentionedEvent(user_id="u1", event_name="cita médica", scheduled_date=today, emotional_weight=7.0))
    client = make_client(True, "event_followup", "Hoy es tu cita médica. ¿Cómo te sientes?")
    engine = ProactivityEngine(client, store, telegram_token="fake")
    decision = await engine.should_proact("u1")
    assert decision.should_send is True
    assert decision.suggested_opening != ""


@pytest.mark.asyncio
async def test_max_two_proactive_messages_per_day(store):
    await store.add_message("u1", "assistant", "Buenos días!", features_used=["proactive"])
    await store.add_message("u1", "assistant", "¿Cómo estás?", features_used=["proactive"])
    client = make_client(True)
    engine = ProactivityEngine(client, store, telegram_token="fake")
    can_send = await engine._within_daily_limit("u1")
    assert can_send is False


@pytest.mark.asyncio
async def test_decision_has_required_fields(store):
    client = make_client(True)
    engine = ProactivityEngine(client, store, telegram_token="fake")
    decision = await engine.should_proact("u1")
    assert hasattr(decision, "should_send")
    assert hasattr(decision, "message_type")
    assert hasattr(decision, "suggested_opening")
```

- [ ] **Step 2: Run to verify failure**

```bash
python -m pytest tests/test_proactivity.py -v
```

Expected: `FAILED — ModuleNotFoundError: No module named 'scheduler.proactivity'`

- [ ] **Step 3: Create `backend/scheduler/proactivity.py`**

```python
import json
import httpx
from dataclasses import dataclass
from typing import Optional
import anthropic
from memory.store import MemoryStore
from memory.context import ContextBuilder, build_memory_summary
from alma.prompts import PROACTIVITY_DECISION_PROMPT


@dataclass
class ProactDecision:
    should_send: bool
    reason: str = ""
    message_type: Optional[str] = None
    suggested_opening: Optional[str] = None


class ProactivityEngine:
    def __init__(self, client: anthropic.Anthropic, store: MemoryStore, telegram_token: str):
        self._client = client
        self._store = store
        self._token = telegram_token
        self._context_builder = ContextBuilder(store)

    async def should_proact(self, user_id: str) -> ProactDecision:
        if not await self._within_daily_limit(user_id):
            return ProactDecision(should_send=False, reason="daily limit reached")

        ctx = await self._context_builder.build(user_id, "")
        summary = build_memory_summary(ctx)

        last_msg_time = await self._store.get_last_user_message_time(user_id)
        prompt = f"Contexto del usuario:\n{summary}\n\nÚltimo mensaje del usuario: {last_msg_time or 'nunca'}"

        response = self._client.messages.create(
            model="claude-opus-4-7",
            max_tokens=256,
            system=PROACTIVITY_DECISION_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )

        try:
            data = json.loads(response.content[0].text)
            return ProactDecision(
                should_send=bool(data.get("should_send", False)),
                reason=data.get("reason", ""),
                message_type=data.get("message_type"),
                suggested_opening=data.get("suggested_opening"),
            )
        except (json.JSONDecodeError, ValueError):
            return ProactDecision(should_send=False, reason="parse error")

    async def send_proactive_message(self, user_id: str, decision: ProactDecision) -> bool:
        user = await self._store.get_user(user_id)
        if not user or not user.telegram_id:
            return False

        message = decision.suggested_opening or "Hola, ¿cómo estás hoy?"

        async with httpx.AsyncClient() as http:
            resp = await http.post(
                f"https://api.telegram.org/bot{self._token}/sendMessage",
                json={"chat_id": user.telegram_id, "text": message},
                timeout=10.0,
            )
            success = resp.status_code == 200

        if success:
            await self._store.add_message(user_id, "assistant", message, features_used=["proactive", "managed_agent"])

        return success

    async def _within_daily_limit(self, user_id: str) -> bool:
        count = await self._store.count_proactive_today(user_id)
        return count < 2
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_proactivity.py -v
```

Expected: All 4 tests `PASSED`

- [ ] **Step 5: Commit**

```bash
git add backend/scheduler/proactivity.py backend/tests/test_proactivity.py
git commit -m "feat: ProactivityEngine — Opus 4.7 decides if/when to send proactive message, respects 2/day limit"
```

---

### Task 11: APScheduler engine

**Files:**
- Create: `backend/scheduler/engine.py`

- [ ] **Step 1: Create `backend/scheduler/engine.py`**

```python
import os
import asyncio
import anthropic
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from memory.database import get_connection
from memory.store import MemoryStore
from scheduler.proactivity import ProactivityEngine


def create_scheduler(anthropic_client: anthropic.Anthropic, telegram_token: str) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()

    async def run_proactivity_sweep():
        async with await get_connection() as conn:
            store = MemoryStore(conn)
            engine = ProactivityEngine(anthropic_client, store, telegram_token)
            users = await store.get_all_active_users()
            for user in users:
                try:
                    decision = await engine.should_proact(user.user_id)
                    if decision.should_send:
                        await engine.send_proactive_message(user.user_id, decision)
                except Exception as e:
                    print(f"[scheduler] error for user {user.user_id}: {e}")

    scheduler.add_job(
        run_proactivity_sweep,
        trigger=IntervalTrigger(hours=1),
        id="proactivity_sweep",
        replace_existing=True,
    )

    return scheduler
```

- [ ] **Step 2: Commit**

```bash
git add backend/scheduler/engine.py
git commit -m "feat: APScheduler runs proactivity sweep every hour for all active users"
```

---

## Stage 6 — FastAPI Backend

### Task 12: FastAPI app + routes

**Files:**
- Create: `backend/api/app.py`
- Create: `backend/api/routes/health.py`
- Create: `backend/api/routes/chat.py`
- Create: `backend/api/routes/memory.py`
- Create: `backend/tests/test_api.py`

- [ ] **Step 1: Create `backend/api/routes/health.py`**

```python
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "ok", "service": "alma-backend"}
```

- [ ] **Step 2: Create `backend/api/routes/chat.py`**

```python
import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import anthropic
from memory.database import get_connection
from memory.store import MemoryStore
from alma.agent import AlmaAgent
from alma.onboarding import OnboardingAgent
from crisis.detector import CrisisDetector, RiskLevel

router = APIRouter()

_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


class ChatRequest(BaseModel):
    user_id: str
    telegram_id: str
    message: str


class ChatResponse(BaseModel):
    reply: str
    features_used: list[str]
    crisis_level: str = "none"
    escalate: bool = False
    volunteer_brief: str = ""


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    conn = await get_connection()
    store = MemoryStore(conn)

    user = await store.get_user_by_telegram_id(req.telegram_id)
    if not user:
        user = await store.create_user(req.user_id, telegram_id=req.telegram_id)

    crisis_result = await CrisisDetector(_client, store).evaluate(user.user_id, req.message)

    if not user.onboarding_complete:
        agent = OnboardingAgent(_client, store)
        result = await agent.process(user.user_id, req.message)
        return ChatResponse(
            reply=result.reply,
            features_used=["onboarding", "memory_store"],
        )

    agent = AlmaAgent(_client, store)
    result = await agent.respond(user.user_id, req.message)

    volunteer_brief = ""
    if crisis_result.should_escalate:
        volunteer_brief = await CrisisDetector(_client, store).generate_volunteer_brief(user.user_id, req.message)

    await conn.close()

    return ChatResponse(
        reply=result.text,
        features_used=result.features_used,
        crisis_level=crisis_result.level.value,
        escalate=crisis_result.should_escalate,
        volunteer_brief=volunteer_brief,
    )
```

- [ ] **Step 3: Create `backend/api/routes/memory.py`**

```python
import os
from fastapi import APIRouter, HTTPException
from memory.database import get_connection
from memory.store import MemoryStore
from memory.context import ContextBuilder, build_memory_summary

router = APIRouter()


@router.get("/memory/{user_id}")
async def get_memory(user_id: str):
    conn = await get_connection()
    store = MemoryStore(conn)
    user = await store.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    recent_mood = await store.get_recent_mood(user_id, limit=14)
    pending_events = await store.get_pending_events(user_id)
    habits = await store.get_habits(user_id)
    preferences = await store.get_preferences(user_id)

    await conn.close()

    return {
        "user": user.model_dump(),
        "mood_history": [m.model_dump() for m in recent_mood],
        "pending_events": [e.model_dump() for e in pending_events],
        "habits": [h.model_dump() for h in habits],
        "preferences": preferences.model_dump() if preferences else None,
    }
```

- [ ] **Step 4: Create `backend/api/app.py`**

```python
import os
from contextlib import asynccontextmanager
import anthropic
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes.health import router as health_router
from api.routes.chat import router as chat_router
from api.routes.memory import router as memory_router
from scheduler.engine import create_scheduler


def create_app() -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        scheduler = create_scheduler(client, token)
        scheduler.start()
        yield
        scheduler.shutdown()

    app = FastAPI(title="Alma Backend", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router)
    app.include_router(chat_router)
    app.include_router(memory_router)

    return app
```

- [ ] **Step 5: Write API tests**

Create `backend/tests/test_api.py`:

```python
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from httpx import AsyncClient, ASGITransport


@pytest.mark.asyncio
async def test_health_endpoint():
    with patch("scheduler.engine.create_scheduler") as mock_sched:
        mock_sched.return_value = MagicMock(start=MagicMock(), shutdown=MagicMock())
        from api.app import create_app
        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_chat_creates_user_and_returns_reply():
    mock_anthropic = MagicMock()
    mock_anthropic.messages.create.return_value = MagicMock(
        content=[MagicMock(text='{"risk_score": 0.1, "risk_level": "none", "signals": [], "recommended_action": "continue"}')]
    )

    with patch("api.routes.chat._client", mock_anthropic), \
         patch("scheduler.engine.create_scheduler") as mock_sched:
        mock_sched.return_value = MagicMock(start=MagicMock(), shutdown=MagicMock())
        mock_anthropic.messages.create.side_effect = [
            MagicMock(content=[MagicMock(text='{"risk_score": 0.1, "risk_level": "none", "signals": [], "recommended_action": "continue"}')]),
            MagicMock(content=[MagicMock(text="Hola! Soy Alma, ¿cómo te llamas?")]),
        ]
        from api.app import create_app
        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/chat", json={
                "user_id": "u_test",
                "telegram_id": "t_test",
                "message": "Hola"
            })
    assert resp.status_code == 200
    data = resp.json()
    assert "reply" in data
    assert "features_used" in data
```

- [ ] **Step 6: Run API tests**

```bash
python -m pytest tests/test_api.py -v
```

Expected: Both tests `PASSED`

- [ ] **Step 7: Commit**

```bash
git add backend/api/ backend/tests/test_api.py
git commit -m "feat: FastAPI app with /health, /chat (onboarding + agent + crisis), /memory endpoints"
```

---

## Stage 7 — Telegram Bot

### Task 13: Telegram bot handlers

**Files:**
- Create: `bot/alma_bot.py`
- Create: `bot/tests/test_handlers.py`

- [ ] **Step 1: Write failing test**

Create `bot/tests/test_handlers.py`:

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_message_handler_calls_backend():
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_http = AsyncMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=None)
        mock_http.post = AsyncMock(return_value=MagicMock(
            status_code=200,
            json=MagicMock(return_value={"reply": "Hola!", "features_used": ["conversation"], "crisis_level": "none", "escalate": False, "volunteer_brief": ""})
        ))
        mock_client_cls.return_value = mock_http

        from alma_bot import call_backend
        result = await call_backend(telegram_id="123", user_id="u1", message="Hola", backend_url="http://localhost:8000")

    assert result["reply"] == "Hola!"


@pytest.mark.asyncio
async def test_call_backend_returns_error_on_failure():
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_http = AsyncMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=None)
        mock_http.post = AsyncMock(side_effect=Exception("connection refused"))
        mock_client_cls.return_value = mock_http

        from alma_bot import call_backend
        result = await call_backend(telegram_id="123", user_id="u1", message="Hola", backend_url="http://localhost:8000")

    assert "error" in result
```

- [ ] **Step 2: Run to verify failure**

```bash
cd /Users/cristian/Documents/Proyectos/Claude-Hackathon-Opus/claude-hackathon-telegram/bot
source venv/bin/activate  # or create one: python -m venv venv && source venv/bin/activate && pip install -r requirements.txt
python -m pytest tests/test_handlers.py -v
```

Expected: `FAILED — ModuleNotFoundError: No module named 'alma_bot'`

- [ ] **Step 3: Create `bot/alma_bot.py`**

```python
import os
import hashlib
import httpx
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv

load_dotenv()

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")


def make_user_id(telegram_id: str) -> str:
    return "u_" + hashlib.md5(telegram_id.encode()).hexdigest()[:12]


async def call_backend(telegram_id: str, user_id: str, message: str, backend_url: str = BACKEND_URL) -> dict:
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{backend_url}/chat",
                json={"user_id": user_id, "telegram_id": telegram_id, "message": message},
            )
            return resp.json()
    except Exception as e:
        return {"error": str(e), "reply": "Lo siento, hubo un problema. Intenta de nuevo.", "features_used": [], "crisis_level": "none", "escalate": False, "volunteer_brief": ""}


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    telegram_id = str(update.effective_chat.id)
    user_id = make_user_id(telegram_id)
    message = update.message.text or ""

    await context.bot.send_chat_action(chat_id=telegram_id, action="typing")

    result = await call_backend(telegram_id, user_id, message)
    reply = result.get("reply", "...")

    await update.message.reply_text(reply)

    if result.get("escalate"):
        brief = result.get("volunteer_brief", "")
        escalation_msg = (
            "Noto que estás pasando por un momento difícil. "
            "Hay un voluntario disponible ahora para escucharte. ¿Quieres que te conecte?"
        )
        await update.message.reply_text(escalation_msg)


async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    telegram_id = str(update.effective_chat.id)
    user_id = make_user_id(telegram_id)
    result = await call_backend(telegram_id, user_id, "hola")
    await update.message.reply_text(result.get("reply", "Hola! Soy Alma."))


def main() -> None:
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", handle_start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Alma bot running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests**

```bash
cd bot
python -m pytest tests/test_handlers.py -v
```

Expected: Both tests `PASSED`

- [ ] **Step 5: Commit**

```bash
git add bot/
git commit -m "feat: Telegram bot — handles messages, calls FastAPI backend, shows escalation offer on crisis"
```

---

## Stage 8 — Demo Frontend

### Task 14: Next.js setup + Chat UI

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/app/layout.tsx`
- Create: `frontend/lib/api.ts`
- Create: `frontend/components/MessageBubble.tsx`
- Create: `frontend/components/ChatWindow.tsx`
- Create: `frontend/components/MemoryPanel.tsx`
- Create: `frontend/app/page.tsx`

- [ ] **Step 1: Create `frontend/package.json`**

```json
{
  "name": "alma-frontend",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start"
  },
  "dependencies": {
    "next": "14.2.5",
    "react": "^18",
    "react-dom": "^18"
  },
  "devDependencies": {
    "@types/node": "^20",
    "@types/react": "^18",
    "@types/react-dom": "^18",
    "autoprefixer": "^10",
    "postcss": "^8",
    "tailwindcss": "^3",
    "typescript": "^5"
  }
}
```

- [ ] **Step 2: Create `frontend/tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "es5",
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [{ "name": "next" }],
    "paths": { "@/*": ["./*"] }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
```

- [ ] **Step 3: Create `frontend/app/layout.tsx`**

```tsx
import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Alma — Demo",
  description: "Proactive wellness companion powered by Claude Opus 4.7",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body className="bg-gray-100 min-h-screen">{children}</body>
    </html>
  );
}
```

- [ ] **Step 4: Create `frontend/app/globals.css`**

```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

- [ ] **Step 5: Create `frontend/lib/api.ts`**

```typescript
const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

export interface ChatResponse {
  reply: string;
  features_used: string[];
  crisis_level: string;
  escalate: boolean;
  volunteer_brief: string;
}

export interface MemoryState {
  user: { user_id: string; name: string | null; onboarding_complete: boolean };
  mood_history: Array<{ mood_score: number; tone: string; created_at: string }>;
  pending_events: Array<{ event_name: string; scheduled_date: string | null; emotional_weight: number }>;
  habits: Array<{ habit_name: string }>;
  preferences: { preferred_time: string; communication_style: string } | null;
}

export async function sendMessage(userId: string, telegramId: string, message: string): Promise<ChatResponse> {
  const res = await fetch(`${BACKEND}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: userId, telegram_id: telegramId, message }),
  });
  return res.json();
}

export async function getMemory(userId: string): Promise<MemoryState> {
  const res = await fetch(`${BACKEND}/memory/${userId}`);
  if (!res.ok) throw new Error("User not found");
  return res.json();
}
```

- [ ] **Step 6: Create `frontend/components/MessageBubble.tsx`**

```tsx
interface MessageBubbleProps {
  role: "user" | "assistant";
  content: string;
  featuresUsed?: string[];
  timestamp?: string;
}

const FEATURE_COLORS: Record<string, string> = {
  memory_store: "bg-purple-100 text-purple-700",
  proactive: "bg-green-100 text-green-700",
  extended_thinking: "bg-yellow-100 text-yellow-700",
  onboarding: "bg-blue-100 text-blue-700",
  conversation: "bg-gray-100 text-gray-600",
};

export default function MessageBubble({ role, content, featuresUsed = [], timestamp }: MessageBubbleProps) {
  const isUser = role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-2`}>
      <div className={`max-w-xs lg:max-w-md px-4 py-2 rounded-2xl ${isUser ? "bg-green-500 text-white rounded-br-sm" : "bg-white text-gray-800 rounded-bl-sm shadow-sm"}`}>
        <p className="text-sm whitespace-pre-wrap">{content}</p>
        {!isUser && featuresUsed.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-1">
            {featuresUsed.filter(f => f !== "conversation").map(f => (
              <span key={f} className={`text-xs px-1.5 py-0.5 rounded-full font-medium ${FEATURE_COLORS[f] || "bg-gray-100 text-gray-600"}`}>
                {f.replace("_", " ")}
              </span>
            ))}
          </div>
        )}
        {timestamp && <p className={`text-xs mt-1 ${isUser ? "text-green-100" : "text-gray-400"}`}>{timestamp}</p>}
      </div>
    </div>
  );
}
```

- [ ] **Step 7: Create `frontend/components/MemoryPanel.tsx`**

```tsx
"use client";
import { useEffect, useState } from "react";
import { getMemory, type MemoryState } from "@/lib/api";

interface MemoryPanelProps {
  userId: string;
  refreshTrigger: number;
}

export default function MemoryPanel({ userId, refreshTrigger }: MemoryPanelProps) {
  const [memory, setMemory] = useState<MemoryState | null>(null);

  useEffect(() => {
    if (!userId) return;
    getMemory(userId).then(setMemory).catch(() => {});
  }, [userId, refreshTrigger]);

  if (!memory) return (
    <div className="p-4 text-gray-400 text-sm">Esperando primer mensaje...</div>
  );

  return (
    <div className="p-4 space-y-4 text-sm overflow-y-auto h-full">
      <div>
        <h3 className="font-semibold text-purple-700 mb-1">Usuario</h3>
        <p className="text-gray-700">{memory.user.name || "—"}</p>
        <p className="text-xs text-gray-400">{memory.user.onboarding_complete ? "Onboarding completo" : "En onboarding"}</p>
      </div>

      {memory.mood_history.length > 0 && (
        <div>
          <h3 className="font-semibold text-purple-700 mb-1">Estado Emocional Reciente</h3>
          {memory.mood_history.slice(0, 5).map((m, i) => (
            <div key={i} className="flex items-center gap-2 text-xs text-gray-600 mb-1">
              <span className={`w-6 h-6 rounded-full flex items-center justify-center text-white text-xs font-bold ${m.mood_score >= 7 ? "bg-green-400" : m.mood_score >= 4 ? "bg-yellow-400" : "bg-red-400"}`}>
                {m.mood_score.toFixed(0)}
              </span>
              <span>{m.tone}</span>
              <span className="text-gray-300">{m.created_at?.split("T")[0]}</span>
            </div>
          ))}
        </div>
      )}

      {memory.pending_events.length > 0 && (
        <div>
          <h3 className="font-semibold text-purple-700 mb-1">Eventos Pendientes</h3>
          {memory.pending_events.map((e, i) => (
            <div key={i} className="text-xs text-gray-600 mb-1">
              <span className="font-medium">{e.event_name}</span>
              {e.scheduled_date && <span className="text-gray-400 ml-1">({e.scheduled_date})</span>}
              <span className="ml-1 text-orange-500">peso {e.emotional_weight}</span>
            </div>
          ))}
        </div>
      )}

      {memory.habits.length > 0 && (
        <div>
          <h3 className="font-semibold text-purple-700 mb-1">Hábitos Detectados</h3>
          {memory.habits.map((h, i) => (
            <p key={i} className="text-xs text-gray-600">{h.habit_name}</p>
          ))}
        </div>
      )}

      {memory.preferences && (
        <div>
          <h3 className="font-semibold text-purple-700 mb-1">Preferencias</h3>
          <p className="text-xs text-gray-600">Hora: {memory.preferences.preferred_time}</p>
          <p className="text-xs text-gray-600">Estilo: {memory.preferences.communication_style}</p>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 8: Create `frontend/components/ChatWindow.tsx`**

```tsx
"use client";
import { useState, useRef, useEffect } from "react";
import MessageBubble from "./MessageBubble";
import { sendMessage, type ChatResponse } from "@/lib/api";

interface Message {
  role: "user" | "assistant";
  content: string;
  featuresUsed?: string[];
  timestamp?: string;
}

interface ChatWindowProps {
  userId: string;
  telegramId: string;
  onMemoryUpdate: () => void;
}

export default function ChatWindow({ userId, telegramId, onMemoryUpdate }: ChatWindowProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [escalation, setEscalation] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const send = async () => {
    if (!input.trim() || loading) return;
    const userMsg = input.trim();
    setInput("");
    setMessages(prev => [...prev, { role: "user", content: userMsg, timestamp: new Date().toLocaleTimeString("es-PE", { hour: "2-digit", minute: "2-digit" }) }]);
    setLoading(true);

    const result: ChatResponse = await sendMessage(userId, telegramId, userMsg);
    setMessages(prev => [...prev, {
      role: "assistant",
      content: result.reply,
      featuresUsed: result.features_used,
      timestamp: new Date().toLocaleTimeString("es-PE", { hour: "2-digit", minute: "2-digit" }),
    }]);

    if (result.escalate) {
      setEscalation(result.volunteer_brief || "Escalada activada");
    }

    setLoading(false);
    onMemoryUpdate();
  };

  return (
    <div className="flex flex-col h-full bg-[#ECE5DD]">
      <div className="bg-[#075E54] text-white px-4 py-3 flex items-center gap-3">
        <div className="w-10 h-10 rounded-full bg-[#25D366] flex items-center justify-center font-bold text-lg">A</div>
        <div>
          <p className="font-semibold">Alma</p>
          <p className="text-xs text-green-200">Companion de bienestar</p>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-2">
        {messages.map((m, i) => (
          <MessageBubble key={i} role={m.role} content={m.content} featuresUsed={m.featuresUsed} timestamp={m.timestamp} />
        ))}
        {loading && (
          <div className="flex justify-start mb-2">
            <div className="bg-white rounded-2xl px-4 py-2 shadow-sm">
              <div className="flex gap-1">
                <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
              </div>
            </div>
          </div>
        )}
        {escalation && (
          <div className="bg-red-50 border border-red-200 rounded-xl p-3 my-2 text-sm text-red-800">
            <strong>Escalada a voluntario activada</strong>
            <p className="text-xs mt-1 text-red-600">{escalation.slice(0, 200)}...</p>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="px-4 py-3 bg-[#F0F0F0] flex gap-2 items-center">
        <input
          className="flex-1 rounded-full px-4 py-2 text-sm bg-white border-none outline-none shadow-sm"
          placeholder="Escribe un mensaje..."
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === "Enter" && send()}
        />
        <button
          onClick={send}
          disabled={loading || !input.trim()}
          className="w-10 h-10 rounded-full bg-[#25D366] text-white flex items-center justify-center disabled:opacity-50"
        >
          &#9658;
        </button>
      </div>
    </div>
  );
}
```

- [ ] **Step 9: Create `frontend/app/page.tsx`**

```tsx
"use client";
import { useState } from "react";
import ChatWindow from "@/components/ChatWindow";
import MemoryPanel from "@/components/MemoryPanel";

const DEMO_USER_ID = "demo_user_hackathon";
const DEMO_TELEGRAM_ID = "999999999";

export default function Home() {
  const [memoryRefresh, setMemoryRefresh] = useState(0);

  return (
    <div className="flex h-screen">
      <div className="flex-1 flex flex-col max-w-sm border-r border-gray-200">
        <ChatWindow
          userId={DEMO_USER_ID}
          telegramId={DEMO_TELEGRAM_ID}
          onMemoryUpdate={() => setMemoryRefresh(n => n + 1)}
        />
      </div>

      <div className="w-80 bg-white border-r border-gray-100 flex flex-col">
        <div className="bg-purple-700 text-white px-4 py-3">
          <h2 className="font-semibold text-sm">Memoria de Alma</h2>
          <p className="text-xs text-purple-200">4 capas — actualización en tiempo real</p>
        </div>
        <MemoryPanel userId={DEMO_USER_ID} refreshTrigger={memoryRefresh} />
      </div>

      <div className="flex-1 bg-gray-50 p-6 overflow-y-auto">
        <h2 className="text-lg font-bold text-gray-800 mb-4">Por qué Alma es diferente</h2>
        <div className="space-y-4">
          {[
            { icon: "↗", title: "Proactivo", desc: "Alma contacta primero — no espera que abras la app. Revisa cada hora si debe enviarte un mensaje." },
            { icon: "🧠", title: "Memoria de 4 capas", desc: "Estado emocional · Eventos mencionados · Hábitos · Preferencias. Persiste entre conversaciones." },
            { icon: "⚠️", title: "Detección de crisis", desc: "Evalúa riesgo en cada mensaje con Extended Thinking. Genera un brief para el voluntario automáticamente." },
            { icon: "👤", title: "Escalada con contexto", desc: "El voluntario ve quién eres antes de hablar — sin que tengas que repetir todo en el peor momento." },
          ].map(item => (
            <div key={item.title} className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-xl">{item.icon}</span>
                <h3 className="font-semibold text-gray-800">{item.title}</h3>
              </div>
              <p className="text-sm text-gray-600">{item.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 10: Install frontend dependencies**

```bash
cd frontend
npm install
```

Expected: `node_modules` created, no errors.

- [ ] **Step 11: Verify frontend builds**

```bash
npm run build
```

Expected: Compiled successfully.

- [ ] **Step 12: Commit**

```bash
git add frontend/
git commit -m "feat: Next.js demo UI — WhatsApp-style chat + live 4-layer memory panel + value proposition panel"
```

---

## Stage 9 — Integration & Smoke Tests

### Task 15: End-to-end smoke test

**Files:**
- Create: `backend/tests/test_smoke.py`

- [ ] **Step 1: Create `backend/tests/test_smoke.py`**

```python
import pytest
import pytest_asyncio
import aiosqlite
from unittest.mock import MagicMock
from memory.database import init_db
from memory.store import MemoryStore
from memory.models import InteractionPreferences
from alma.agent import AlmaAgent
from crisis.detector import CrisisDetector, RiskLevel
from scheduler.proactivity import ProactivityEngine


def make_mock_client_sequence(*responses):
    mock = MagicMock()
    mock.messages.create.side_effect = [
        MagicMock(content=[MagicMock(text=r)]) for r in responses
    ]
    return mock


@pytest.mark.asyncio
async def test_full_conversation_flow():
    """User sends 3 messages, agent responds with memory context by message 2."""
    async with aiosqlite.connect(":memory:") as conn:
        conn.row_factory = aiosqlite.Row
        await init_db(conn)
        store = MemoryStore(conn)
        await store.create_user("u_smoke", name="Sofía")
        await store.upsert_preferences(InteractionPreferences(user_id="u_smoke"))
        await store.update_onboarding_step("u_smoke", step=5, complete=True)

        client = make_mock_client_sequence(
            "Hola Sofía, qué bueno tenerte aquí.",
            "Entiendo, mañana tienes la presentación. ¿Cómo te estás preparando?",
            "Te escucho. Eso suena estresante.",
        )
        agent = AlmaAgent(client, store)

        r1 = await agent.respond("u_smoke", "hola")
        assert r1.text != ""

        r2 = await agent.respond("u_smoke", "mañana tengo una presentación importante")
        assert r2.text != ""

        r3 = await agent.respond("u_smoke", "estoy muy nerviosa")
        assert r3.text != ""

        messages = await store.get_recent_messages("u_smoke", limit=20)
        assert len(messages) == 6


@pytest.mark.asyncio
async def test_crisis_escalation_flow():
    """Crisis message triggers high risk and generates volunteer brief."""
    async with aiosqlite.connect(":memory:") as conn:
        conn.row_factory = aiosqlite.Row
        await init_db(conn)
        store = MemoryStore(conn)
        await store.create_user("u_crisis", name="Lucas")

        client = make_mock_client_sequence(
            '{"risk_score": 0.88, "risk_level": "critical", "signals": ["ideacion_suicida"], "recommended_action": "escalate"}',
            "Brief confidencial: Lucas, 24 años, está en crisis severa. Tono sugerido: calmado, no alarmista.",
        )
        detector = CrisisDetector(client, store)

        result = await detector.evaluate("u_crisis", "ya no quiero seguir")
        assert result.level == RiskLevel.CRITICAL
        assert result.should_escalate is True

        brief = await detector.generate_volunteer_brief("u_crisis", "ya no quiero seguir")
        assert len(brief) > 10
```

- [ ] **Step 2: Run smoke tests**

```bash
python -m pytest tests/test_smoke.py -v
```

Expected: Both smoke tests `PASSED`

- [ ] **Step 3: Run all tests together**

```bash
python -m pytest tests/ -v --tb=short
```

Expected: All tests pass. (If any fail, fix before proceeding.)

- [ ] **Step 4: Commit**

```bash
git add backend/tests/test_smoke.py
git commit -m "test: end-to-end smoke tests for full conversation flow and crisis escalation"
```

---

## Stage 10 — Final Wiring & .env Setup

### Task 16: Create `.env`, run the system locally

**Files:**
- Create: `backend/.env` (from `.env.example` — NOT committed)
- Create: `bot/.env` (from `.env.example` — NOT committed)
- Create: `frontend/.env.local`

- [ ] **Step 1: Create `backend/.env`** (fill in real values)

```bash
ANTHROPIC_API_KEY=<your_key>
TELEGRAM_BOT_TOKEN=<your_bot_token>
DATABASE_URL=alma.db
BACKEND_URL=http://localhost:8000
```

- [ ] **Step 2: Create `frontend/.env.local`**

```
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
```

- [ ] **Step 3: Verify `.gitignore` excludes `.env` files**

Check that `backend/.gitignore` (or root `.gitignore`) contains:
```
.env
.env.local
*.db
__pycache__/
venv/
.venv/
node_modules/
.next/
```

- [ ] **Step 4: Start backend**

```bash
cd backend
source venv/bin/activate
python main.py
```

Expected: `Uvicorn running on http://0.0.0.0:8000`

- [ ] **Step 5: Verify health endpoint**

```bash
curl http://localhost:8000/health
```

Expected: `{"status":"ok","service":"alma-backend"}`

- [ ] **Step 6: Start frontend**

```bash
cd frontend
npm run dev
```

Expected: `Ready — started server on 0.0.0.0:3000`

Open `http://localhost:3000` — should show 3-panel layout: chat | memory | value props.

- [ ] **Step 7: Start Telegram bot**

```bash
cd bot
source venv/bin/activate
python alma_bot.py
```

Expected: `Alma bot running...`

- [ ] **Step 8: Send a test message via the web UI**

Type "hola" in the chat. Verify:
- Response appears in chat bubble
- Memory panel updates (shows user created, onboarding step)
- Feature badge appears on Alma's response

- [ ] **Step 9: Send a message with an event**

Type "mañana tengo una entrevista de trabajo muy importante". Verify:
- Pending events section in memory panel shows the event
- Alma's response acknowledges it

- [ ] **Step 10: Trigger crisis detection**

Type "ya no quiero seguir, para qué todo". Verify:
- Escalation banner appears in the chat UI
- Volunteer brief is shown in the banner

- [ ] **Step 11: Final commit**

```bash
git add .
git commit -m "chore: env examples, gitignore, final integration — system runs end-to-end"
```

---

## Summary

| Stage | Tasks | Key output |
|-------|-------|-----------|
| 1 — Foundation | 1 | Dirs, deps, main.py |
| 2 — Database & Memory | 2-5 | SQLite schema, MemoryStore, ContextBuilder |
| 3 — Alma Agent | 6-8 | Prompts, AlmaAgent, OnboardingAgent |
| 4 — Crisis | 9 | CrisisDetector, volunteer brief |
| 5 — Proactivity | 10-11 | ProactivityEngine, APScheduler |
| 6 — API | 12 | FastAPI /chat /memory /health |
| 7 — Bot | 13 | Telegram bot + backend client |
| 8 — Frontend | 14 | Next.js chat + memory panel |
| 9 — Integration | 15 | Smoke tests, all tests green |
| 10 — Wiring | 16 | System runs end-to-end locally |

**Total tests:** ~30 unit + integration tests across all modules.
