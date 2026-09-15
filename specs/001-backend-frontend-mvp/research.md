# Research: Phase 1 MVP — Doctor Appointment Booking System

**Branch**: `001-backend-frontend-mvp` | **Date**: 2026-07-25
**Purpose**: Resolve all NEEDS CLARIFICATION items and document key architectural decisions.

---

## Decision 1: JWT Token Strategy

**Decision**: Dual-token model — short-lived access token (15 min) stored in `localStorage` +
long-lived refresh token (7 days) stored in `localStorage`.

**Rationale**: User explicitly specified `JWT localStorage` for the frontend. The access token
enforces the 15-min inactivity requirement. The refresh token allows transparent session extension
while the user is active, preventing disruptive logouts during active use.

**Security trade-off documented**: `localStorage` is accessible to JavaScript (XSS risk). For this
MVP the risk is accepted; a production hardening pass would move refresh tokens to `httpOnly` cookies.

**Alternatives considered**:
- httpOnly cookies (more secure, XSS-resistant) — rejected by user preference for localStorage
- Single token (15 min only, no refresh) — rejected; too disruptive for doctors reviewing appointments

---

## Decision 2: Conversation State Storage (SMS & Voice)

**Decision**: Store in-progress booking conversations in the `conversation_sessions` PostgreSQL table.
Each row tracks `phone_number`, `channel` (SMS/Voice), `current_step`, and `collected_data` (JSONB),
with a TTL of 30 minutes (`expires_at`).

**Rationale**: PostgreSQL is already required for appointments. Adding Redis would be an extra
infrastructure dependency for MVP. JSONB is flexible enough for the evolving data collected step by
step during booking.

**Alternatives considered**:
- Redis (in-memory, faster TTL management) — rejected; adds infra complexity; PostgreSQL sufficient at MVP scale
- In-memory dict (process memory) — rejected; loses state on server restart; not horizontally scalable

---

## Decision 3: Appointment Slot Availability

**Decision**: Hardcoded default clinic availability in `config/settings.py`: Monday–Friday, 9:00am–
5:00pm, 30-minute slots. The system computes available slots dynamically by querying existing
`scheduled` appointments in the `appointments` table for the requested date.

**Rationale**: No slot-management UI is in MVP scope. Hardcoded config is the smallest viable
implementation. Existing appointments act as the only availability constraint.

**Alternatives considered**:
- Doctor-managed availability table — rejected; out of MVP scope
- External scheduling API (Calendly etc.) — rejected; adds third-party dependency and cost

---

## Decision 4: Voice AI Architecture (Twilio + Groq)

**Decision**: Use Twilio's `<Gather>` TwiML verb for speech input (STT handled by Twilio) and
`<Say>` for voice output (TTS handled by Twilio). The FastAPI backend receives the transcribed text
from Twilio, sends it to Groq (llama-3.3-70b) for intent/response generation, and returns TwiML
with the next `<Say>` + `<Gather>` or `<Hangup>`.

**Flow**:
```
Patient calls → Twilio STT → POST /voice/webhook (transcribed text)
→ Groq generates response → TwiML response → Twilio TTS → Patient hears response
```

**Rationale**: Twilio handles all telephony, STT, and TTS. Groq provides the conversational
intelligence. This avoids integrating a separate STT/TTS service and keeps the backend stateless
(conversation state is in PostgreSQL).

**Alternatives considered**:
- Twilio + OpenAI Realtime API — rejected; not in approved tech stack (Groq is designated)
- ElevenLabs TTS — rejected; scope creep; Twilio built-in TTS is sufficient for MVP

---

## Decision 5: Email Reminder Scheduling

**Decision**: Use APScheduler (in-process scheduler, `AsyncIOScheduler`) running inside the FastAPI
process. A job fires every 5 minutes, queries appointments where `scheduled_at` is between
`[now + 23h 55m, now + 24h 5m]` and `status = scheduled` and no reminder sent, sends reminder
email via SendGrid, marks reminder as sent.

**Rationale**: APScheduler requires zero additional infrastructure (no Redis, no Celery worker). For
MVP scale (~100 appointments/day), a 5-minute polling interval is more than sufficient.

**Alternatives considered**:
- Celery + Redis — rejected; requires two extra services (Redis broker, Celery worker); over-engineered for MVP
- Cron job (OS-level) — rejected; requires server-level config outside the application; harder to deploy
- Cloud scheduled functions (AWS Lambda) — rejected; out of MVP scope; adds cloud config complexity

---

## Decision 6: Database Migrations

**Decision**: Alembic (official SQLAlchemy migration tool). `alembic upgrade head` is run at
application startup (or manually before deploying).

**Rationale**: Standard SQLAlchemy ecosystem tool. Auto-generates migration scripts from model
changes. Required for production-safe schema evolution.

---

## Decision 7: PHI Encryption at Rest

**Decision**: Use PostgreSQL `pgcrypto` extension to encrypt sensitive columns (patient phone, DOB,
insurance carrier, insurance member ID) at the database level using symmetric encryption. The
encryption key is loaded from the `ENCRYPTION_KEY` env var.

**Rationale**: Constitution Principle I requires encrypted PHI at rest. Column-level encryption in
the database ensures data is protected even if the database file is accessed directly.

**Simpler alternative considered**: Application-level encryption before INSERT — equivalent security
but moves complexity into the application layer; `pgcrypto` is well-tested and transparent.

**Note**: For MVP, application-level encryption via Python's `cryptography` library (Fernet) is used
to keep complexity manageable, with a migration path to `pgcrypto` post-MVP.

---

## Decision 8: CORS Configuration

**Decision**: FastAPI `CORSMiddleware` allows the frontend origin (`http://localhost:3000` in dev,
`FRONTEND_URL` env var in prod). All other origins are denied.

---

## Resolved NEEDS CLARIFICATION Items

| Item | Resolution |
|------|-----------|
| Slot availability mechanism | Hardcoded Mon–Fri 9am–5pm, 30-min slots; dynamic conflict-check against DB |
| FAQ content for Voice agent | Defined as a config dict in `config/settings.py`: clinic name, hours, location, phone, accepted insurance list |
| Reminder email timing | 24 hours before appointment (FR-024); APScheduler polls every 5 minutes |
| Token storage mechanism | localStorage per user spec; access=15min, refresh=7d |
| Single-doctor vs multi-doctor | Single clinic/doctor model for MVP; `doctor_id` FK on appointments for future multi-tenant extension |
