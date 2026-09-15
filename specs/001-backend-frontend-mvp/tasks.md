---
description: "Task list for Phase 1 MVP — Doctor Appointment Booking System"
---

# Tasks: Phase 1 MVP — Doctor Appointment Booking System

**Input**: Design documents from `/specs/001-backend-frontend-mvp/`
**Prerequisites**: plan.md ✅ | spec.md ✅ | data-model.md ✅ | research.md ✅
**Tests**: Backend integration tests included (constitution requires happy-path test per endpoint).
**Frontend**: Minimal pages included as the approved Phase 1 test harness (see plan.md Complexity Tracking).

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1–US5)
- Exact file paths included in every description

## Path Conventions

- Backend: `backend/` at repository root
- Frontend: `frontend/` at repository root
- Alembic migrations: `backend/alembic/versions/`

---

## Phase 1: Setup

**Purpose**: Create root infrastructure — env config, project scaffolding, dependency manifests.

- [x] T001 Create `.env.example` at repo root with all required vars: `DATABASE_URL`, `SECRET_KEY`, `ALGORITHM=HS256`, `ACCESS_TOKEN_EXPIRE_MINUTES=15`, `REFRESH_TOKEN_EXPIRE_DAYS=7`, `GROQ_API_KEY`, `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER`, `SENDGRID_API_KEY`, `SENDGRID_FROM_EMAIL`, `ENCRYPTION_KEY` (32-byte Fernet key), `FRONTEND_URL=http://localhost:3000`, `NEXT_PUBLIC_API_URL=http://localhost:8000`
- [x] T002 Create `backend/requirements.txt` listing: `fastapi`, `uvicorn[standard]`, `sqlalchemy[asyncio]`, `asyncpg`, `alembic`, `python-jose[cryptography]`, `passlib[bcrypt]`, `groq`, `twilio`, `sendgrid`, `apscheduler`, `pydantic-settings`, `cryptography`, `httpx`, `pytest`, `pytest-asyncio`
- [x] T003 [P] Scaffold `frontend/` as Next.js 14 app: run `npx create-next-app@14 frontend --typescript --tailwind --app --no-src-dir --import-alias "@/*"`, then install `shadcn-ui`, `axios`, `lucide-react`
- [x] T004 [P] Initialise Alembic: run `alembic init backend/alembic` from repo root, update `backend/alembic.ini` `script_location = backend/alembic`, update `backend/alembic/env.py` to import `Base` from `backend/models/base.py` and use `DATABASE_URL` from env

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared infrastructure all user stories depend on — config, DB session, ORM models, migration.

⚠️ **CRITICAL**: No user story implementation begins until this phase is complete.

- [x] T005 Create `backend/config/settings.py` — `pydantic-settings` `Settings` class with fields for all vars in `.env.example`; export singleton `settings = Settings()`
- [x] T006 Create `backend/db/session.py` — async SQLAlchemy engine (`create_async_engine`), `AsyncSessionLocal`, and `get_db` FastAPI dependency that yields an `AsyncSession`
- [x] T007 [P] Create `backend/models/base.py` — `DeclarativeBase` subclass `Base`; `TimestampMixin` with `created_at` and `updated_at` `TIMESTAMPTZ` columns (server-default `now()`, `onupdate` hook)
- [x] T008 [P] Create `backend/models/doctor.py` — `Doctor` model (inherits `Base`, `TimestampMixin`): all columns from data-model.md doctors table; `__tablename__ = "doctors"`
- [x] T009 [P] Create `backend/models/patient.py` — `Patient` model with Fernet-encrypted `TypeDecorator` (`EncryptedString`) for `name`, `date_of_birth`, `email` (optional), `insurance_carrier`, `insurance_member_id`; `phone_hash` VARCHAR(64) for SHA-256 lookup; `__tablename__ = "patients"`
- [x] T010 [P] Create `backend/models/appointment.py` — `Appointment` model with FKs to `doctors.id` and `patients.id`; `status` as Python `Enum` (`scheduled`, `cancelled`, `completed`); `booking_channel` as Enum (`sms`, `voice`); `reason_for_visit` Fernet-encrypted; `insurance_snapshot` JSONB; `__tablename__ = "appointments"`
- [x] T011 [P] Create `backend/models/conversation_session.py` — `ConversationSession` model: `phone_hash`, `channel` Enum, `current_step` VARCHAR(50), `collected_data` JSONB, `expires_at` TIMESTAMPTZ; `__tablename__ = "conversation_sessions"`
- [x] T012 Generate and apply initial Alembic migration: run `alembic revision --autogenerate -m "initial_schema"` to create `backend/alembic/versions/<hash>_initial_schema.py`; verify the generated file creates all 4 tables with correct indexes and FK constraints; run `alembic upgrade head`
- [x] T013 Create `backend/main.py` — FastAPI app with `CORSMiddleware` (allow `settings.FRONTEND_URL`); lifespan event that runs `alembic upgrade head` on startup and starts/stops APScheduler; include routers (auth, appointments, sms, voice) — routers registered as stubs initially and filled in each phase
- [x] T014 [P] Create `frontend/lib/auth.ts` — token helpers: `getAccessToken()`, `getRefreshToken()`, `setTokens(access, refresh)`, `clearTokens()`, `isTokenExpired(token)` (decode JWT exp claim without verifying signature)
- [x] T015 [P] Create `frontend/lib/api.ts` — Axios instance with `baseURL = process.env.NEXT_PUBLIC_API_URL`; request interceptor injects `Authorization: Bearer <accessToken>`; response interceptor on 401: clears tokens, redirects to `/login`

**Checkpoint**: Database created with all 4 tables. FastAPI app starts without errors. Frontend npm install succeeds.

---

## Phase 3: User Story 1 — Doctor Registration & Authentication (Priority: P1) 🎯 MVP

**Goal**: Doctor can register, verify email, log in, auto-logout after 15 min, reset password, update profile.
**Independent Test**: Hit each auth endpoint in sequence: signup → verify-email → login → /auth/profile → refresh → logout. Then visit `/dashboard` in browser unauthenticated — must redirect to `/login`.

### Backend — Auth (US1)

- [ ] T016 [US1] Create `backend/services/auth_service.py` — `hash_password(plain)`, `verify_password(plain, hashed)`, `create_access_token(data, expires_delta)`, `create_refresh_token(data)`, `decode_token(token)`, `generate_secure_token()` (secrets.urlsafe), `send_verification_email(doctor)`, `send_reset_email(doctor)` stubs calling sendgrid_service
- [ ] T017 [P] [US1] Create `backend/middleware/auth_middleware.py` — `get_current_doctor` FastAPI dependency: extracts Bearer token from `Authorization` header, calls `decode_token`, queries `doctors` table by ID, raises `HTTP 401` if token invalid/expired/doctor not found
- [ ] T018 [P] [US1] Create `backend/services/sendgrid_service.py` (initial version) — `send_email(to, subject, html_body)` wrapper around SendGrid `Mail`; `send_verification_email(to_email, token, doctor_name)`; `send_password_reset_email(to_email, token, doctor_name)` — all use single SendGrid basic template (no dynamic templates)
- [ ] T019 [US1] Create `backend/routes/auth.py` — Pydantic request/response schemas inline; implement all endpoints: `POST /auth/signup` (create doctor, send verification email), `POST /auth/verify-email` (validate token, set is_verified=true), `POST /auth/login` (verify credentials, return access+refresh tokens), `POST /auth/refresh` (validate refresh token, return new access token), `POST /auth/logout` (client-side; return 200), `POST /auth/forgot-password` (generate reset token, send email), `POST /auth/reset-password` (validate token, update hashed_password, clear reset fields), `GET /auth/profile` (requires auth), `PUT /auth/profile/update` (requires auth; update name, clinic_name, phone, state)
- [ ] T020 [US1] Update `backend/main.py` — import and `app.include_router(auth_router, prefix="/auth", tags=["auth"])`
- [ ] T021 [US1] Create `backend/tests/test_auth.py` — `pytest` async integration tests using `httpx.AsyncClient(app=app)`: test_signup_success, test_verify_email, test_login_success, test_login_unverified_fails, test_profile_requires_auth, test_forgot_password, test_refresh_token

### Frontend — Auth Pages (US1)

- [ ] T022 [P] [US1] Create `frontend/app/layout.tsx` — root layout: Inter font, `<html lang="en">`, global Tailwind CSS import, wraps `{children}`
- [ ] T023 [P] [US1] Create `frontend/components/auth-guard.tsx` — client component; on mount reads `getAccessToken()`; if absent or expired calls `router.push('/login')`; renders `null` while checking, then renders `children`
- [ ] T024 [P] [US1] Create `frontend/components/inactivity-logout.tsx` — client component; attaches `mousemove`, `mousedown`, `keydown`, `scroll` event listeners; resets 15-min timer on each event; on timeout: calls `clearTokens()` then `router.push('/login')`
- [ ] T025 [P] [US1] Create `frontend/app/login/page.tsx` — Shadcn UI `Card` with email + password inputs; on submit POSTs to `/auth/login`, calls `setTokens(access, refresh)`, redirects to `/dashboard`; shows error on failure; includes "Forgot password?" link to `/forgot-password`
- [ ] T026 [P] [US1] Create `frontend/app/signup/page.tsx` — Shadcn UI form: name, email, password, clinic_name, phone, state (US state select); POSTs to `/auth/signup`; on success shows "Please check your email to verify your account" message; "Login" link
- [ ] T027 [P] [US1] Create `frontend/app/forgot-password/page.tsx` — email input; POSTs to `/auth/forgot-password`; on success shows "Reset link sent to your email"
- [ ] T028 [P] [US1] Create `frontend/app/reset-password/page.tsx` — reads `?token=` from URL; new password + confirm password form; POSTs to `/auth/reset-password`; on success shows "Password updated" + link to login
- [ ] T029 [P] [US1] Create `frontend/app/verify-email/page.tsx` — reads `?token=` from URL; on mount POSTs to `/auth/verify-email`; shows "Email verified! You can now log in" on success or error message on failure

**Checkpoint**: Doctor can signup → get verification email → verify → login → see /dashboard (redirect) → 15-min idle logout. All `test_auth.py` tests pass.

---

## Phase 4: User Story 2 — SMS Booking Agent (Priority: P2)

**Goal**: Patient texts Twilio number, AI books appointment via multi-step SMS conversation, patient receives SMS confirmation.
**Independent Test**: Use Twilio test webhook (ngrok tunnel to `POST /sms/webhook`) or Twilio dev console; send "Hello" → complete full booking flow → verify ConversationSession row deleted, Appointment row created, patient receives confirmation SMS.

- [ ] T030 [US2] Create `backend/services/groq_service.py` — `GroqClient` wrapping `groq.Groq(api_key=settings.GROQ_API_KEY)`; `async chat(system_prompt: str, messages: list[dict]) -> str` calls `client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role":"system","content":system_prompt}]+messages)` and returns `response.choices[0].message.content`
- [ ] T031 [P] [US2] Create `backend/services/twilio_service.py` — `send_sms(to: str, body: str)` using `twilio.rest.Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN).messages.create(from_=settings.TWILIO_PHONE_NUMBER, to=to, body=body)`; `validate_twilio_request(request_url, params, signature)` using `twilio.request_validator.RequestValidator`
- [ ] T032 [US2] Create `backend/agents/sms_agent.py` — full SMS state machine:
  System prompt: "I am an AI assistant helping schedule your appointment. [disclosure]. Never provide medical advice. Redirect all medical questions to 'Please consult your doctor directly.'"
  State steps: `greeting → collect_name → collect_dob → collect_reason → collect_insurance_carrier → collect_insurance_id → present_slots → confirm_slot → confirmed`
  `get_available_slots(date, doctor_id, db)` → queries appointments table, returns next 3 open 30-min slots in Mon–Fri 9am–5pm window
  `process_message(phone_number, text, db)` → upsert ConversationSession, pass collected_data + user text to Groq, parse response, advance step; on `confirmed`: upsert Patient (encrypt PHI), create Appointment, delete session, call `twilio_service.send_sms(confirmation)`, call `sendgrid_service.send_booking_confirmation_email` + `send_doctor_notification_email`
- [ ] T033 [US2] Create `backend/routes/sms.py` — `POST /sms/webhook`: validates Twilio signature (skip in test mode); extracts `From` and `Body` from form data; calls `sms_agent.process_message`; returns plain 200 with `MessagingResponse` TwiML body; add router to `backend/main.py`

**Checkpoint**: Full SMS booking completes. DB has encrypted Patient and Appointment rows. ConversationSession deleted after booking. SMS confirmation received. Doctor notification email sent.

---

## Phase 5: User Story 3 — Voice Call Agent (Priority: P3)

**Goal**: Patient calls Twilio voice number, AI conducts conversation, books appointment, sends SMS confirmation.
**Independent Test**: Use Twilio dev console to trigger inbound call webhook; step through greeting → FAQ → booking → confirmed; verify Appointment row created and SMS sent.

- [ ] T034 [US3] Create `backend/agents/voice_agent.py` — Voice TwiML state machine:
  System prompt: same AI disclosure + HIPAA guardrails as SMS; static FAQ dict from `settings.FAQ_CONFIG` (clinic_name, hours, location, phone, accepted_insurance_list)
  Steps: `greeting → faq_or_booking → collect_name → collect_dob → collect_reason → collect_insurance_carrier → collect_insurance_id → present_slots → confirm_slot → confirmed`
  `build_twiml_gather(say_text, action_url)` → returns `<Response><Say>{say_text}</Say><Gather input="speech" action="{action_url}" speechTimeout="3" speechModel="phone_call"><Say>Please speak now</Say></Gather></Response>`
  `process_speech(phone_number, speech_text, call_sid, db)` → same flow as SMS agent but returns TwiML string; on `confirmed`: create Patient+Appointment, send SMS, return `<Response><Say>Your appointment is confirmed. You will receive a text shortly. Goodbye!</Say><Hangup/></Response>`
- [ ] T035 [US3] Create `backend/routes/voice.py` — `POST /voice/webhook`: returns initial greeting TwiML (`build_twiml_gather` with action `/voice/gather`); `POST /voice/gather`: receives `SpeechResult` + `From`/`CallSid`, calls `voice_agent.process_speech`, returns next TwiML; add router to `backend/main.py`

**Checkpoint**: Voice call completes full booking flow. Appointment created. SMS confirmation sent to caller. FAQ questions answered correctly.

---

## Phase 6: User Story 4 — Email Confirmation & Reminders (Priority: P4)

**Goal**: Booking confirmation emails sent to patient (if email provided) and doctor within 2 min; reminder email 24h before appointment.
**Independent Test**: Create a test appointment via the SMS agent; verify doctor receives notification email within 2 min. Set `scheduled_at` to 24h from now; trigger scheduler job manually; verify reminder email sent and `reminder_sent=true` in DB.

- [ ] T036 [P] [US4] Add optional `email` field (encrypted `EncryptedString`, nullable) to `backend/models/patient.py`; generate Alembic migration `alembic revision --autogenerate -m "add_patient_email"` and run `alembic upgrade head`
- [ ] T037 [P] [US4] Update `backend/agents/sms_agent.py` — after `confirm_slot` step, add optional `collect_email` step: ask "Would you like to provide your email for a booking confirmation? (Reply with email or 'skip')"; store in `collected_data["patient_email"]`; upsert Patient with email on booking creation
- [ ] T038 [P] [US4] Update `backend/agents/voice_agent.py` — same optional email collection step as SMS agent; if caller says "skip" or says nothing, proceed without email
- [ ] T039 [US4] Extend `backend/services/sendgrid_service.py` — add:
  `send_booking_confirmation_email(to_email, patient_name, doctor_name, clinic_name, appointment_dt, reference_id)` → basic HTML email template (no dynamic SendGrid template);
  `send_doctor_notification_email(to_email, doctor_name, patient_name, appointment_dt, booking_channel)`;
  `send_reminder_email(to_email, patient_name, doctor_name, clinic_name, appointment_dt)`
- [ ] T040 [US4] Create `backend/scheduler.py` — `AsyncIOScheduler` with timezone `UTC`; add job `send_appointment_reminders` (interval 5 min): query `appointments` WHERE `scheduled_at BETWEEN NOW()+23h55m AND NOW()+24h5m` AND `status='scheduled'` AND `reminder_sent=false`; for each: call `send_reminder_email` (if patient.email exists), set `reminder_sent=true`, commit; export `start_scheduler()` and `stop_scheduler()` functions
- [ ] T041 [US4] Update `backend/main.py` lifespan — call `start_scheduler()` on startup and `stop_scheduler()` on shutdown

**Checkpoint**: After SMS/Voice booking, doctor receives notification email within 2 min. Patient receives confirmation email if email provided. APScheduler job fires correctly and sets `reminder_sent=true`.

---

## Phase 7: User Story 5 — Doctor Dashboard & Appointments Management (Priority: P5)

**Goal**: JWT-protected dashboard shows live stats; appointments page lists bookings with filter and cancel.
**Independent Test**: Log in as doctor via `/login` page. Dashboard shows stats. Navigate to `/appointments`, filter by status, cancel one appointment. Navigating to `/dashboard` without logging in redirects to `/login`.

### Backend — Appointments API (US5)

- [ ] T042 [US5] Create `backend/routes/appointments.py` with all endpoints (requires `get_current_doctor` middleware):
  `GET /appointments` — query params: `date` (ISO date, optional), `status` (optional), `page=1`, `limit=20`; joins `patients` for patient name (decrypt); returns paginated list;
  `GET /appointments/{id}` — full detail including decrypted patient name, DOB, insurance;
  `PUT /appointments/{id}` — body `{"status": "cancelled" | "completed"}`; validates transition; returns updated appointment;
  `GET /dashboard/stats` — returns `{"today_count": int, "total_patients": int, "recent_bookings": list[5]}`
- [ ] T043 [US5] Update `backend/main.py` — import and `app.include_router(appointments_router, prefix="", tags=["appointments"])`

### Frontend — Dashboard & Appointments Pages (US5)

- [ ] T044 [US5] Create `frontend/app/dashboard/page.tsx` — client component; wraps `<AuthGuard>` + `<InactivityLogout>`; on mount calls `GET /dashboard/stats`; renders 3 Shadcn UI `<Card>` tiles (Today's Appointments, Total Patients, — placeholder for future metric); renders "Recent Bookings" table with columns: Patient ID, Date/Time, Channel, Status; medical blue header (`bg-blue-700 text-white`); "View All" link to `/appointments`
- [ ] T045 [US5] Create `frontend/app/appointments/page.tsx` — client component; wraps `<AuthGuard>` + `<InactivityLogout>`; renders date picker input + status dropdown filter (shadcn `<Select>`); on filter change calls `GET /appointments?date=&status=`; renders appointments table: Patient Name (decrypted by backend), Date/Time, Reason, Channel, Status badge, Cancel button; Cancel button POSTs `PUT /appointments/{id}` `{status:"cancelled"}`; optimistically updates row status to "cancelled" without page reload

**Checkpoint**: Full browser flow works: `/login` → `/dashboard` (shows real counts) → `/appointments` (lists bookings from SMS/Voice tests) → Cancel appointment → status updates immediately. Unauthenticated `/dashboard` redirects to `/login`.

---

## Phase N: Polish & Cross-Cutting Concerns

**Purpose**: Final quality gate — integration tests, .gitignore, end-to-end verification.

- [ ] T046 [P] Create `backend/tests/test_appointments.py` — pytest async tests: create_appointment fixture, test_list_appointments, test_get_appointment_detail, test_cancel_appointment, test_dashboard_stats (all with valid JWT)
- [ ] T047 [P] Create `.gitignore` at repo root — Python: `__pycache__/`, `*.pyc`, `.env`, `venv/`, `.pytest_cache/`, `*.egg-info`; Node: `node_modules/`, `.next/`, `.env.local`, `*.tsbuildinfo`; Alembic: do NOT ignore `backend/alembic/versions/`
- [ ] T048 [P] Add `FAQ_CONFIG` dict to `backend/config/settings.py` — `clinic_name`, `clinic_hours` (Mon–Fri 9am–5pm EST), `clinic_address`, `clinic_phone`, `accepted_insurance` (list of 5 major carriers); used by `voice_agent.py`
- [ ] T049 Run `pytest backend/tests/ -v` — verify all tests pass; fix any failures before proceeding
- [ ] T050 Manual end-to-end browser verification: signup → verify email → login → dashboard (data shows) → appointments (list filters work) → cancel appointment (status updates) → wait 15 min idle (auto-logout occurs) — document result in a comment at the bottom of this file

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Foundational — provides auth for all subsequent browser testing
- **US2 (Phase 4)**: Depends on Foundational + T030 groq_service — can start after Phase 2
- **US3 (Phase 5)**: Depends on Foundational + T030 groq_service + T031 twilio_service — can start after US2 is complete (reuses groq/twilio services)
- **US4 (Phase 6)**: Depends on US2 and US3 (email triggered from agents) + Foundational
- **US5 (Phase 7)**: Depends on Foundational + US1 (auth middleware) — backend can start after Phase 2; frontend needs US1 auth pages
- **Polish (Phase N)**: Depends on all user stories being implemented

### User Story Dependencies

- **US1 (P1)**: No dependency on other stories — complete independently first
- **US2 (P2)**: Depends only on Foundational (models, DB) — can develop in parallel with US1
- **US3 (P3)**: Depends on T030 + T031 (groq/twilio services created in US2) — start after US2
- **US4 (P4)**: Depends on T032 (sms_agent) and T034 (voice_agent) already existing — start after US2 + US3
- **US5 (P5)**: Backend API depends only on Foundational + US1 middleware; frontend depends on US1 auth pages

### Within Each Story

- Services → Models (already in Foundational) → Routes → Frontend
- Backend must work (curl test or integration test) before adding frontend page

### Parallel Opportunities

- T003 (frontend scaffold) and T004 (Alembic init) can run in parallel
- T007–T011 (all 4 ORM models + base) can all run in parallel
- T014 (auth.ts) and T015 (api.ts) run in parallel
- T016 (auth_service) and T017 (middleware) and T018 (sendgrid basic) run in parallel
- T022–T029 (all frontend auth pages) can run in parallel after T022 (layout)
- T030 (groq_service) and T031 (twilio_service) run in parallel
- T036 (patient email field) and T039 (sendgrid extend) run in parallel
- T046 (test_appointments) and T047 (.gitignore) and T048 (FAQ_CONFIG) run in parallel

---

## Parallel Execution Examples

### Phase 2 Foundational — Run All Models Together

```text
In parallel (different files, no inter-dependencies):
  T007: Create backend/models/base.py
  T008: Create backend/models/doctor.py
  T009: Create backend/models/patient.py
  T010: Create backend/models/appointment.py
  T011: Create backend/models/conversation_session.py
Then sequential:
  T012: Generate + apply Alembic migration (depends on all models)
  T013: Create backend/main.py (depends on all models being importable)
```

### Phase 3 US1 — Auth Pages Run Together

```text
Sequential:
  T016: auth_service.py (base for everything)
In parallel:
  T017: middleware/auth_middleware.py
  T018: services/sendgrid_service.py (basic version)
Then sequential:
  T019: routes/auth.py (depends on T016, T017, T018)
  T020: Register router in main.py
In parallel (all different page files):
  T022: frontend/app/layout.tsx
  T023: frontend/components/auth-guard.tsx
  T024: frontend/components/inactivity-logout.tsx
  T025: frontend/app/login/page.tsx
  T026: frontend/app/signup/page.tsx
  T027: frontend/app/forgot-password/page.tsx
  T028: frontend/app/reset-password/page.tsx
  T029: frontend/app/verify-email/page.tsx
```

---

## Implementation Strategy

### MVP First (US1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL)
3. Complete Phase 3: US1 Doctor Auth — backend + login/signup/dashboard pages
4. **STOP and VALIDATE**: Doctor can register, log in, and see the (empty) dashboard
5. Proceed to US2

### Incremental Delivery

1. Setup + Foundational → DB running, app starts
2. US1 → Doctor auth working in browser → MVP demo #1
3. US2 → SMS booking working via Twilio → MVP demo #2
4. US3 → Voice booking working via Twilio → MVP demo #3
5. US4 → Email confirmations flowing → MVP demo #4
6. US5 → Dashboard shows real booking data from demos → MVP demo #5 (Phase 1 complete)

---

## Summary

| Phase | Stories | Tasks | Parallel Tasks |
|-------|---------|-------|---------------|
| Setup | — | T001–T004 (4) | T003, T004 |
| Foundational | — | T005–T015 (11) | T007–T011, T014, T015 |
| Phase 3 | US1 Auth | T016–T029 (14) | T017, T018, T022–T029 |
| Phase 4 | US2 SMS | T030–T033 (4) | T030, T031 |
| Phase 5 | US3 Voice | T034–T035 (2) | — |
| Phase 6 | US4 Email | T036–T041 (6) | T036, T037, T038, T039 |
| Phase 7 | US5 Dashboard | T042–T045 (4) | T043, T044, T045 (after T042) |
| Polish | — | T046–T050 (5) | T046, T047, T048 |
| **Total** | **5 stories** | **50 tasks** | **25 parallelizable** |

---

## Notes

- `[P]` tasks = different files, no dependencies — safe to execute concurrently
- `[US?]` label maps each task to its user story for traceability to spec.md
- Each user story has a **Checkpoint** — stop and verify before moving to the next story
- Tests (`test_auth.py`, `test_appointments.py`) are required per constitution Principle V
- All PHI fields must use `EncryptedString` TypeDecorator from `backend/models/patient.py`
- No SMS body EVER contains PHI — only reference ID, date, clinic name (constitution Principle VI)
- Every AI agent response MUST include disclosure statement (constitution Principle II)
