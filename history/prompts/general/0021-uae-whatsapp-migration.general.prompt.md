---
id: 0021
title: UAE WhatsApp migration — replace SMS/Voice with WhatsApp
stage: green
date: 2026-07-29
surface: agent
model: claude-sonnet-5
feature: none
branch: master
user: umairbangash11
command: none
labels: ["whatsapp", "twilio", "groq-whisper", "elevenlabs", "uae", "migration", "backend", "frontend"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
 - backend/config/settings.py
 - backend/models/appointment.py
 - backend/models/conversation_session.py
 - backend/alembic/versions/004_whatsapp_channel.py
 - backend/services/twilio_service.py
 - backend/services/groq_service.py
 - backend/services/elevenlabs_service.py
 - backend/agents/whatsapp_agent.py
 - backend/routes/whatsapp.py
 - backend/main.py
 - backend/pytest.ini
 - backend/tests/test_whatsapp.py
 - backend/routes/sms.py (deleted)
 - backend/routes/voice.py (deleted)
 - backend/agents/sms_agent.py (deleted)
 - backend/agents/voice_agent.py (deleted)
 - frontend/app/whatsapp-test/page.tsx
 - frontend/app/dashboard/page.tsx
 - .env
 - .env.example
 - .claude/skills/whatsapp-skill/SKILL.md
 - .claude/skills/sms-handler-skill/ (deleted)
 - .claude/skills/voice-call-skill/ (deleted)
 - .claude/skills/appointment-booking-skill/SKILL.md
 - .claude/skills/doctor-auth-admin-skill/SKILL.md
 - .claude/skills/frontend-dashboard-skill/SKILL.md
 - CLAUDE.md
tests:
 - backend/tests/test_whatsapp.py (9 tests, all passing against a local Postgres test DB)
---

## Prompt

Update this MVP for UAE market.

REMOVE these US-based features:
1. Remove Twilio SMS webhook
   (DELETE /sms/webhook endpoint)
2. Remove Twilio Voice call
   (DELETE /voice/answer endpoint)
3. Remove SMS related code
4. Remove Voice call related code

ADD these UAE WhatsApp features:

FEATURE 1 — WhatsApp TEXT:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Create POST /whatsapp/webhook

When patient sends WhatsApp
text message:
1. Receive text from Twilio
2. Process with Groq llama
   (llama-3.3-70b-versatile)
3. Same booking flow:
   - Greet as AI assistant
   - Collect name + phone
   - Show available slots
   - Confirm booking
   - Save to PostgreSQL
4. Send text reply back
   via Twilio WhatsApp

FEATURE 2 — WhatsApp VOICE MESSAGE:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
When patient sends WhatsApp
voice message (audio):
1. Receive audio file
   from Twilio webhook
2. Download audio file
3. Convert Speech to Text:
   Use Groq Whisper API
   Model: whisper-large-v3
   Supports Arabic + English
   Auto detect language!
4. Process text with
   Groq llama agent
   Same booking flow
5. Generate reply text
6. Convert Text to Voice:
   Use ElevenLabs API
   Same language as input!
   Arabic in = Arabic voice out
   English in = English voice out
7. Send voice message reply
   via Twilio WhatsApp

FEATURE 3 — FRONTEND WHATSAPP SIMULATOR:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Add new page in Next.js:
/whatsapp-test

Design like WhatsApp UI:
- Green theme
- Chat bubbles
- Left = Patient messages
- Right = Agent replies

Features:
- Text input field
- Send button
- Voice record button 🎤
  (Record voice in browser)
- Messages display
- Show agent text replies
- Play agent voice replies

This page connects to:
POST /whatsapp/webhook
directly from browser!

So doctor/developer can test:
Type message → Agent replies
Record voice → Agent voice replies

KEEP these existing features:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Doctor signup/login (JWT)
✅ Doctor dashboard
✅ Appointments list
✅ Profile update
✅ Forgot password
✅ PostgreSQL database
✅ All auth endpoints

UPDATE .env with:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886
ELEVENLABS_API_KEY=your_key
GROQ_API_KEY=existing_key

APIs needed:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Twilio WhatsApp Sandbox (FREE)
Groq Whisper (FREE)
Groq llama (FREE)
ElevenLabs FREE tier

Language Support:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Arabic + English both!
Auto detect from patient!
Reply in same language!

Booking Flow Same:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Greet patient as AI
2. Ask new or returning
3. Collect name + phone
4. Show available slots
5. Confirm appointment
6. Save to database
7. Send confirmation

HIPAA/NABIDH Rules:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Always identify as AI
Get consent first
No diagnosis in messages
Encrypt patient data

## Response snapshot

Clarified three architectural decisions up front (webhook dual-mode design, ElevenLabs voice strategy, DB enum cutover strategy) via AskUserQuestion, then entered plan mode to design the full migration before touching code; user approved the plan.

Implemented:
- Removed `routes/sms.py`, `routes/voice.py`, `agents/sms_agent.py`, `agents/voice_agent.py`, `build_twiml_say`, `TWILIO_PHONE_NUMBER`.
- Added `routes/whatsapp.py` with two endpoints sharing one conversation core: `POST /whatsapp/webhook` (real Twilio, form-encoded in / TwiML out, signature-validated outside dev) and `POST /whatsapp/simulate` (browser dev/test endpoint, JSON in/out, no signature check) — per the user's chosen "shared core, two thin endpoints" design.
- New `agents/whatsapp_agent.py`: bilingual (Arabic/English) deterministic state machine (consent → collect_name → collect_insurance → select_slot → confirm → done), reusing the proven keyword-driven pattern from the old `sms_agent.py` rather than routing booking facts through an LLM; Groq `chat()` used only as a fallback for free-text/FAQ queries.
- `services/groq_service.py`: added `transcribe_audio` (Groq Whisper `whisper-large-v3`, auto language detection).
- New `services/elevenlabs_service.py`: `text_to_speech` via `eleven_multilingual_v2` (single voice ID for both languages), graceful no-op when no real API key is configured.
- `services/twilio_service.py`: added WhatsApp send/TwiML helpers, Twilio media download, and `validate_twilio_signature`.
- DB: `BookingChannel`/`SessionChannel` enums replaced with a single `whatsapp` value; new Alembic migration `004_whatsapp_channel.py` does a hard cutover (per user's choice) via enum-type recreation.
- Frontend: new `/whatsapp-test` WhatsApp-styled chat simulator (green theme, patient-left/agent-right per the user's explicit layout, text input + 🎤 voice recording via the browser's native `MediaRecorder`, posts to `/whatsapp/simulate`), plus a nav link from the dashboard.
- Skills: deleted `sms-handler-skill`/`voice-call-skill`, added `whatsapp-skill/SKILL.md`, fixed cross-references in `appointment-booking-skill`, `doctor-auth-admin-skill`, `frontend-dashboard-skill`.
- `CLAUDE.md`: updated channel list, Phase 1 bullets, active-skills list, removed-from-scope list.
- `.env`/`.env.example`: WhatsApp/ElevenLabs/Whisper vars, UAE-flavored clinic placeholders and insurer list.

Found and fixed two real bugs while writing tests: (1) the session-persistence filter was stripping `_available_slots` between conversation turns (inherited from the same flawed pattern in the now-deleted `sms_agent.py` — never previously caught since no SMS tests existed); (2) `send_booking_confirmation_email` was being awaited with a wrong keyword arg (`appointment_time` vs. the function's actual `appointment_dt`) and missing its required `reference_id` — also inherited from `sms_agent.py`. Also discovered pytest-asyncio needed `loop_scope="session"` (module-level engine + per-test event loops otherwise collide with asyncpg) and that the pre-existing `test_appointments.py`/`test_auth.py` use a hardcoded DB password that doesn't match this environment's actual Postgres password — pre-existing, unrelated to this change, left as-is.

## Outcome

- ✅ Impact: SMS and Voice channels fully removed; WhatsApp (text + voice note, bilingual) is now the sole automated booking channel, with a working dev-time browser simulator.
- 🧪 Tests: `backend/tests/test_whatsapp.py` — 9/9 passing (agent-level real-DB flow tests + route-level wiring tests with mocked Groq/ElevenLabs/Twilio). `npx tsc --noEmit` clean on the frontend.
- 📁 Files: see `files:` above — new WhatsApp service/agent/route/test files, deleted SMS/voice files, updated config/models/migration/skills/CLAUDE.md/env files, new frontend simulator page.
- 🔁 Next prompts: obtain real ElevenLabs/Twilio WhatsApp sandbox credentials and manually verify the voice-note round trip end-to-end; consider fixing the pre-existing `test_appointments.py`/`test_auth.py` DB-password mismatch separately.
- 🧠 Reflection: writing tests immediately surfaced two latent bugs inherited from copy-pasting the proven `sms_agent.py` pattern (JSONB key-stripping, wrong email-helper call signature) — validates always running the new test suite against a real DB before declaring a ported pattern correct, rather than trusting that "it matches the reference implementation" is sufficient.

## Evaluation notes (flywheel)

- Failure modes observed: asyncpg "attached to a different loop" when a module-level SQLAlchemy async engine is combined with pytest-asyncio's default per-test event loop scope; Starlette's `BaseHTTPMiddleware` (this app's request-logging middleware) also conflicts with asyncpg under httpx's `ASGITransport` in tests — worked around by keeping DB-touching tests at the agent level (no HTTP layer) and mocking the conversation-core call for HTTP-level wiring tests, rather than fixing the middleware itself (out of scope, works fine under real uvicorn).
- Graders run and results (PASS/FAIL): `pytest backend/tests/test_whatsapp.py -v` — PASS (9/9). `npx tsc --noEmit` — PASS (no errors).
- Prompt variant (if applicable): n/a
- Next experiment (smallest change to try): n/a
