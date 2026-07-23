---
name: sms-handler-skill
description: Handles incoming and outgoing SMS messages via Twilio for the appointment booking agent — receives patient messages, sends agent replies, manages conversation state. Implementation only, no spec/planning logic. Use when building or modifying Twilio SMS webhook handling, outbound messaging, or SMS conversation state in this project.
---

# SMS Handler Skill

Implementation-only skill for the Twilio SMS transport layer of the appointment booking agent. Work covered by this skill goes straight to implementation — do not route it through `/sp.specify`, `/sp.plan`, or `/sp.tasks`.

## Stack

- Python 3.11+, FastAPI
- Twilio Python SDK (`twilio`) for outbound REST calls; Twilio webhook POST for inbound
- PostgreSQL for conversation/message persistence (SQLAlchemy 2.0 async + asyncpg unless the project already has an established DB access pattern — match that instead)

## Scope

In scope:
- Inbound webhook endpoint that receives Twilio SMS POSTs, validates the request, persists the message, and hands it off to the booking agent's reply logic.
- Outbound sending: a `send_sms(to, body)` function used by the agent core to reply to patients.
- Conversation state: per-patient SMS thread persisted in Postgres.

Out of scope (do not implement here):
- Booking/NLU/agent decision logic — this skill only moves messages in and out; the appointment agent core decides what to say.
- Spec, plan, or task generation.

## API contract

- `POST /webhooks/sms/inbound` — Twilio inbound webhook.
  - Validate `X-Twilio-Signature` against `TWILIO_AUTH_TOKEN` before trusting the payload; reject with 403 on failure.
  - Parse `From`, `To`, `Body`, `MessageSid` from the form-encoded Twilio payload (not JSON).
  - Find or create the conversation by `From` (E.164 phone number), persist the inbound message.
  - Respond quickly (empty TwiML `<Response/>` or 204) — don't block the webhook on agent processing. Send the reply asynchronously via the outbound REST call.
- `send_sms(to: str, body: str) -> str` — returns the Twilio message SID.
  - Uses the Twilio REST `messages.create` call, not TwiML, since replies are sent out-of-band from the inbound webhook.
  - Persists the outbound message against the same conversation.

## Data model (Postgres)

- `sms_conversations`: `id`, `patient_phone` (E.164, unique), `status` (`active`/`closed`), `created_at`, `updated_at`
- `sms_messages`: `id`, `conversation_id` (FK), `direction` (`inbound`/`outbound`), `body`, `twilio_sid` (unique), `created_at`

Dedupe inbound webhook retries on `twilio_sid` — Twilio retries on timeout/non-2xx responses, so reprocessing the same `MessageSid` must be a no-op.

## Config / secrets

Required env vars, loaded via `.env` + pydantic settings — never hardcode: `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER`, `DATABASE_URL`.

## Error handling

- Invalid/missing Twilio signature → 403, no processing.
- Malformed payload (missing `From`/`Body`) → 400.
- Twilio send failure → log, mark the message `failed` in `sms_messages`, don't crash the caller.
- Duplicate `twilio_sid` on inbound → treat as already-processed, return 200 without reprocessing.

## Testing

- Mock the Twilio client in unit tests — no real API calls.
- Test signature validation with both valid and tampered signatures.
- Test dedupe behavior by replaying the same `MessageSid`.
- For manual/integration testing, use Twilio's magic test numbers and test credentials rather than a live account.
