"""
Tests for the WhatsApp booking channel, split in two layers:

- Agent-level tests call `handle_whatsapp_message` directly against a real
  Postgres test DB — this exercises the actual bilingual booking flow and
  persistence without going through the ASGI app.
- Route-level tests go through the HTTP app but mock `handle_whatsapp_message`
  (and STT/TTS) so they only verify request/response wiring (TwiML shape,
  JSON shape, signature validation) — kept separate from the DB-touching
  agent tests because Starlette's BaseHTTPMiddleware (used for this app's
  request-logging middleware) is known to conflict with asyncpg's event-loop
  tracking under httpx's ASGITransport in tests; mocking the DB-touching call
  at the route layer sidesteps that entirely rather than fighting test infra
  unrelated to this feature.

Requires a running PostgreSQL instance (see TEST_DB_URL below). No real
Groq/ElevenLabs/Twilio calls are made.
Run: pytest backend/tests/test_whatsapp.py -v
"""
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import update
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from main import app
from db.session import get_db
from models.base import Base
from models.doctor import Doctor
from models.patient import hash_phone
from models.conversation_session import ConversationSession
from agents.whatsapp_agent import handle_whatsapp_message, detect_language

TEST_DB_URL = "postgresql+asyncpg://postgres:111@localhost:5432/test_booking_agent"

_engine = create_async_engine(TEST_DB_URL, echo=False)
_TestSession = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)

# All async tests/fixtures in this module share one session-scoped event loop —
# the engine above is created at import time, so per-test event loops (pytest-
# asyncio's default) would hand its pooled connections to a loop other than the
# one each test runs on, raising asyncpg "attached to a different loop" errors.
pytestmark = pytest.mark.asyncio(loop_scope="session")


async def override_get_db():
    async with _TestSession() as session:
        yield session


app.dependency_overrides[get_db] = override_get_db


@pytest_asyncio.fixture(scope="module", autouse=True, loop_scope="session")
async def setup_db():
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with _TestSession() as session:
        session.add(
            Doctor(
                name="Dr. Fatima Al Mansoori",
                email="drfatima@example.com",
                hashed_password="x",
                clinic_name="Test Clinic",
                phone="+9715XXXXXXX",
                state="Dubai",
                is_verified=True,
            )
        )
        await session.commit()

    yield
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(loop_scope="session")
async def db_session():
    async with _TestSession() as session:
        yield session


@pytest_asyncio.fixture(loop_scope="session")
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


# ---------------------------------------------------------------------------
# Agent-level tests — real DB, real booking flow
# ---------------------------------------------------------------------------


async def test_first_message_returns_consent_prompt_english(db_session):
    reply, lang = await handle_whatsapp_message(
        "whatsapp:+971500000001", "hi", detect_language("hi"), db_session
    )
    assert lang == "en"
    assert "reply yes" in reply.lower()


async def test_first_message_arabic_returns_arabic_prompt(db_session):
    text = "مرحبا"
    reply, lang = await handle_whatsapp_message(
        "whatsapp:+971500000002", text, detect_language(text), db_session
    )
    assert lang == "ar"
    assert "نعم" in reply or "توافق" in reply


async def test_stop_opts_out_at_any_stage(db_session):
    phone = "whatsapp:+971500000003"
    await handle_whatsapp_message(phone, "hello", detect_language("hello"), db_session)
    reply, _ = await handle_whatsapp_message(phone, "STOP", detect_language("STOP"), db_session)
    assert "opted out" in reply.lower()


async def test_full_booking_flow(db_session):
    phone = "whatsapp:+971500000004"

    reply, _ = await handle_whatsapp_message(phone, "hello", "en", db_session)
    assert "reply yes" in reply.lower()

    reply, _ = await handle_whatsapp_message(phone, "yes", "en", db_session)
    assert "name" in reply.lower()

    reply, _ = await handle_whatsapp_message(phone, "Ahmed Khan", "en", db_session)
    assert "insurance" in reply.lower()

    reply, _ = await handle_whatsapp_message(phone, "skip", "en", db_session)
    assert "available slots" in reply.lower() or "no slots" in reply.lower()

    if "available slots" in reply.lower():
        reply, _ = await handle_whatsapp_message(phone, "1", "en", db_session)
        assert "confirm" in reply.lower()

        reply, _ = await handle_whatsapp_message(phone, "yes", "en", db_session)
        assert "confirmed" in reply.lower()


async def test_returning_patient_is_greeted_by_name(db_session):
    phone = "whatsapp:+971500000005"
    await handle_whatsapp_message(phone, "hello", "en", db_session)
    await handle_whatsapp_message(phone, "yes", "en", db_session)
    await handle_whatsapp_message(phone, "Sara Ali", "en", db_session)
    reply, _ = await handle_whatsapp_message(phone, "skip", "en", db_session)
    if "no slots" in reply.lower():
        pytest.skip("no available slots in test window")
    await handle_whatsapp_message(phone, "1", "en", db_session)
    await handle_whatsapp_message(phone, "yes", "en", db_session)

    # Force the "done" session to expire so the next message starts a genuinely
    # new conversation (handle_whatsapp_message only looks up non-expired
    # sessions) — the patient row itself persists, so this exercises the
    # new-vs-returning lookup rather than just continuing the same session.
    await db_session.execute(
        update(ConversationSession)
        .where(ConversationSession.phone_hash == hash_phone(phone))
        .values(expires_at=datetime.now(timezone.utc) - timedelta(hours=1))
    )
    await db_session.commit()

    reply, _ = await handle_whatsapp_message(phone, "hi again", "en", db_session)
    reply, _ = await handle_whatsapp_message(phone, "yes", "en", db_session)
    assert "sara ali" in reply.lower()


# ---------------------------------------------------------------------------
# Route-level tests — HTTP wiring only, DB-touching agent call mocked out
# ---------------------------------------------------------------------------


async def test_webhook_returns_twiml_text(client: AsyncClient):
    with patch(
        "routes.whatsapp.handle_whatsapp_message",
        new=AsyncMock(return_value=("Hello there", "en")),
    ):
        res = await client.post(
            "/whatsapp/webhook",
            data={"From": "whatsapp:+971500000099", "Body": "hi"},
        )
    assert res.status_code == 200
    assert "<Message>" in res.text
    assert "Hello there" in res.text


async def test_simulate_returns_json_text(client: AsyncClient):
    with patch(
        "routes.whatsapp.handle_whatsapp_message",
        new=AsyncMock(return_value=("Hello there", "en")),
    ):
        res = await client.post(
            "/whatsapp/simulate", data={"phone": "whatsapp:+971500000098", "text": "hi"}
        )
    assert res.status_code == 200
    body = res.json()
    assert body["reply_text"] == "Hello there"
    assert body["language"] == "en"
    assert "audio_base64" not in body


async def test_simulate_voice_note_transcribes_and_synthesizes(client: AsyncClient):
    with patch(
        "routes.whatsapp.handle_whatsapp_message",
        new=AsyncMock(return_value=("Sure, here's a reply", "en")),
    ), patch(
        "routes.whatsapp.transcribe_audio",
        new=AsyncMock(return_value={"text": "hello", "language": "en"}),
    ), patch(
        "routes.whatsapp.text_to_speech",
        new=AsyncMock(return_value=b"fake-mp3-bytes"),
    ):
        res = await client.post(
            "/whatsapp/simulate",
            data={"phone": "whatsapp:+971500000097"},
            files={"audio": ("note.webm", b"fake-audio-bytes", "audio/webm")},
        )
    assert res.status_code == 200
    body = res.json()
    assert body["transcribed_text"] == "hello"
    assert body["audio_base64"]


async def test_webhook_rejects_invalid_signature_outside_dev(client: AsyncClient):
    with patch("routes.whatsapp.settings") as mock_settings:
        mock_settings.ENVIRONMENT = "production"
        with patch("routes.whatsapp.validate_twilio_signature", return_value=False):
            res = await client.post(
                "/whatsapp/webhook",
                data={"From": "whatsapp:+971500000096", "Body": "hi"},
                headers={"X-Twilio-Signature": "forged"},
            )
    assert res.status_code == 403
