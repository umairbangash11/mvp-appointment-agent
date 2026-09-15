# Doctor Appointment Booking Agent (MVP)

An AI-driven appointment booking system for a single-doctor clinic. Patients book appointments over **SMS** or **voice call**, receive an **email confirmation**, and the doctor manages everything from a web dashboard.

## Channels

| Channel | Transport | AI | Notes |
|---|---|---|---|
| SMS booking | Twilio SMS webhook | Groq (conversation + NLU) | Conversation state machine, insurance check, HIPAA-aware messaging |
| Voice call booking | Twilio Voice webhook | Groq (low-latency turns) | Static FAQ answers (no RAG), same booking core as SMS |
| Email confirmation | SendGrid | — | Basic single-template confirmation, sent after a booking is finalized |

## Architecture

```
backend/    FastAPI + PostgreSQL API
frontend/   Next.js doctor dashboard + public booking page
specs/      Feature specs (Spec-Driven Development)
history/    Prompt History Records (PHRs)
```

### Backend (`backend/`)

- **Framework:** FastAPI, async SQLAlchemy + asyncpg, Alembic migrations (run automatically on startup)
- **Auth:** JWT access/refresh tokens, bcrypt password hashing, email verification, forgot/reset password
- **Agents:** `agents/sms_agent.py`, `agents/voice_agent.py` — conversation logic backed by Groq
- **Services:** `services/` — Groq, Twilio, SendGrid, and auth helpers
- **PHI:** encrypted at rest via Fernet (`ENCRYPTION_KEY`)
- **Scheduler:** APScheduler background job for appointment reminders

**API routes:**

| Prefix | Endpoints |
|---|---|
| `/auth` | `signup`, `verify-email`, `login`, `refresh`, `logout`, `forgot-password`, `reset-password`, `profile` (get/update) |
| `/appointments` | list, `stats`, get by id, `cancel` |
| `/sms` | `webhook` (Twilio inbound SMS) |
| `/voice` | `answer`, `gather` (Twilio inbound voice) |
| `/health` | liveness check |

### Frontend (`frontend/`)

Next.js 14 (App Router) + Tailwind CSS.

- `login`, `signup`, `forgot-password`, `reset-password`, `verify-email` — doctor auth flow
- `dashboard` — doctor's home view
- `appointments` — appointment list/management

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 14+
- Accounts/API keys: [Groq](https://console.groq.com), [Twilio](https://www.twilio.com), [SendGrid](https://sendgrid.com)

### Backend setup

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

Copy `.env.example` to `.env` in the project root and fill in real values:

```bash
cp .env.example .env
```

Required variables (see `.env.example`):

- `DATABASE_URL` — PostgreSQL connection string
- `SECRET_KEY`, `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_DAYS` — JWT config
- `ENCRYPTION_KEY` — Fernet key for PHI encryption (`python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`)
- `GROQ_API_KEY`
- `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER`
- `SENDGRID_API_KEY`, `SENDGRID_FROM_EMAIL`, `SENDGRID_FROM_NAME`
- `FRONTEND_URL`, `NEXT_PUBLIC_API_URL`
- `CLINIC_NAME`, `CLINIC_HOURS`, `CLINIC_ADDRESS`, `CLINIC_PHONE` — used by the voice agent's static FAQ

Run the API (migrations run automatically on startup):

```bash
uvicorn main:app --reload
```

API docs available at `http://localhost:8000/docs`.

### Frontend setup

```bash
cd frontend
npm install
npm run dev
```

Dashboard available at `http://localhost:3000`.

### Twilio webhooks

Point your Twilio SMS and Voice webhooks to:

- SMS: `POST https://<your-host>/sms/webhook`
- Voice: `POST https://<your-host>/voice/answer`

Use a tunnel (e.g. `ngrok http 8000`) for local development.

## Testing

```bash
cd backend
pytest
```

## Out of scope for this MVP

RAG/vector knowledge base, payments (Stripe), multi-template email flows, additional messaging channels (WhatsApp/Facebook/Instagram), and a daily-report cron. See `CLAUDE.md` for the full project scope.
