---
name: env-config-skill
description: Sets up environment configuration for the MVP — .env structure for Twilio, Anthropic, and Groq API keys plus basic app settings, with required environment variables validated on startup (fail fast, not mid-request). Implementation only, no spec/planning logic. Use when adding a new config value, wiring app settings, or touching .env / .env.example.
---

# Env Config Skill

Implementation-only skill for centralized environment configuration. Every other skill in this project ([[sms-handler-skill]], [[conversation-agent-skill]], [[hipaa-compliance-skill]], [[appointment-booking-skill]], [[doctor-auth-admin-skill]], [[voice-call-rag-skill]], [[appointment-confirmation-skill]]) reads its secrets and settings through this skill's `Settings` object rather than calling `os.environ` directly. Work covered by this skill goes straight to implementation — do not route it through `/sp.specify`, `/sp.plan`, or `/sp.tasks`.

## Stack

- Python 3.11+, FastAPI
- `pydantic-settings` (`pydantic_settings.BaseSettings`) — the standard config-validation idiom for FastAPI apps, matching the "load via `.env` + pydantic settings" convention already assumed by [[sms-handler-skill]].

## Settings schema

A single `Settings` class (e.g. in `app/config.py`), loading from `.env` via `SettingsConfigDict(env_file=".env")`. Use `pydantic.SecretStr` for every credential field — it prevents the value from appearing in `repr()`/logs by accident; call `.get_secret_value()` only at the point of actual use (e.g. constructing the Twilio/Anthropic client).

### Required (app fails to start without these)

| Variable | Used by | Notes |
|---|---|---|
| `TWILIO_ACCOUNT_SID` | [[sms-handler-skill]] | |
| `TWILIO_AUTH_TOKEN` | [[sms-handler-skill]] | Also used to validate inbound webhook signatures |
| `TWILIO_FROM_NUMBER` | [[sms-handler-skill]] | E.164 format |
| `DATABASE_URL` | all skills | Postgres connection string |
| `ANTHROPIC_API_KEY` | [[conversation-agent-skill]] | |
| `ENCRYPTION_KEY` | [[hipaa-compliance-skill]] | Fernet key for `patients.name` / `sms_messages.body` field encryption |
| `PRACTICE_NAME` | [[hipaa-compliance-skill]] | Interpolated into the canned AI-disclosure/consent text — must not silently default to a placeholder in production |
| `JWT_SECRET` | [[doctor-auth-admin-skill]] | Signs/verifies doctor auth tokens. High-entropy, never reused for another purpose |
| `SENDGRID_API_KEY` | [[doctor-auth-admin-skill]] | Verification and password-reset emails |
| `SENDGRID_FROM_EMAIL` | [[doctor-auth-admin-skill]] | Must be a verified sender in SendGrid |
| `FRONTEND_BASE_URL` | [[doctor-auth-admin-skill]] | Used to build verification/reset links (e.g. `{FRONTEND_BASE_URL}/verify-email?token=...`) |
| `GROQ_API_KEY` | [[voice-call-rag-skill]] | **No longer reserved/optional** — was added speculatively in an earlier pass, now actually consumed for voice-call RAG generation (chosen over Anthropic there specifically for latency; see that skill) |
| `GOOGLE_TTS_KEY` | [[voice-call-rag-skill]] | Text-to-speech for the agent's voice. Auth mechanism (bare key vs. service-account JSON) needs confirming — see that skill's note |
| `OPENAI_API_KEY` | [[voice-call-rag-skill]] | Embeddings only, for RAG document/query vectors — this project does not use OpenAI for chat/generation |
| `HUMAN_HANDOFF_PHONE_NUMBER` | [[voice-call-rag-skill]] | Number a voice call transfers to when RAG can't answer or the patient asks for a person |
| `API_BASE_URL` | [[appointment-confirmation-skill]] | The backend's own publicly reachable base URL — needed so Twilio knows where to fetch TwiML from when *we* initiate an outbound call (`calls.create(url=...)`). Not needed by any earlier skill since every prior Twilio interaction was inbound (Twilio calling a URL configured in its own console, not one we construct) |

### Optional / reserved

| Variable | Default | Notes |
|---|---|---|
| `APP_ENV` | `"development"` | `development` \| `staging` \| `production` |
| `LOG_LEVEL` | `"INFO"` | |
| `JWT_EXPIRY_HOURS` | `24` | [[doctor-auth-admin-skill]] — token lifetime; see that skill for why this is 24h rather than the frontend's 15-minute auto-logout window |
| `PGVECTOR_ENABLED` | `true` | [[voice-call-rag-skill]] — when `false`, RAG search is skipped and voice calls go straight to human handoff for informational questions; useful before the `pgvector` extension is provisioned in a given environment |

## Validation on startup

Instantiate `Settings()` once at **module import time** in `app/config.py` (not lazily inside a request handler), so a missing/invalid required variable raises `pydantic.ValidationError` and crashes the app on boot — never partway through serving a request. Expose it via a cached singleton for dependency injection:

```python
from functools import lru_cache

@lru_cache
def get_settings() -> Settings:
    return Settings()
```

FastAPI routes depend on `Settings` via `Depends(get_settings)`, not by importing a module-level instance directly, so it stays mockable in tests.

## `.env` files

- `.env.example` — checked into the repo, documents every variable from the table above with placeholder values, no real secrets. This is the reference for what a new environment needs.
- `.env` — local secrets, **must** be in `.gitignore`. Verify this before considering the skill's setup complete; a leaked `.env` is a credential leak, not just a config bug.
- Never commit real values for any field in the Required or Optional tables above.

## Security

- Every credential field is `SecretStr`, not `str`.
- When logging or printing settings for debugging, log field *names* present/missing, never values.
- `PRACTICE_NAME` is not a secret but does end up in patient-facing text — validate it's non-empty and not a placeholder value before allowing `APP_ENV=production` to boot (a simple startup check, not a hard schema constraint).

## Out of scope

- Secrets-manager integration (Vault, AWS Secrets Manager, etc.) for non-local environments — `.env` is the MVP mechanism; swapping the loading source later is a config-loader change, not a schema change.
- Spec, plan, or task generation.

## Testing

- Startup fails with a clear error when a required variable is missing (test by unsetting one at a time, not all at once — confirms each is independently enforced).
- Startup succeeds with only the required variables set and `PGVECTOR_ENABLED` absent (falls back to its default).
- `get_settings()` returns the same cached instance across calls; overriding it via FastAPI's dependency-override mechanism works in tests without touching real env vars.
- Assert no `SecretStr` field ever appears in a log line or exception message (test by triggering an error path and inspecting captured log/output text).
