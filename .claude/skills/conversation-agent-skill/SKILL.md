---
name: conversation-agent-skill
description: Manages patient conversation flow for the appointment booking agent — greets the patient, identifies new vs. returning, collects name and phone number, confirms the appointment. Uses the Claude API for natural language understanding. HIPAA-aware: always discloses it is an AI. Implementation only, no spec/planning logic. Use when building or modifying the conversational/NLU layer that sits on top of the SMS transport.
---

# Conversation Agent Skill

Implementation-only skill for the patient-facing conversation logic of the appointment booking agent. Sits on top of [[sms-handler-skill]] — the SMS skill moves messages in and out over Twilio; this skill decides what the agent says and tracks where each patient is in the booking flow. Work covered by this skill goes straight to implementation — do not route it through `/sp.specify`, `/sp.plan`, or `/sp.tasks`.

## Stack

- Python 3.11+, FastAPI
- Anthropic Python SDK (`anthropic`) for the Claude API
- PostgreSQL for conversation/patient state (shares the database from [[sms-handler-skill]])

## Conversation state machine

Each `sms_conversations` row (from the SMS skill) additionally tracks a `stage`:

1. **`greeting`** — First inbound message from a phone number with no existing conversation. Immediately advances to `consent_pending` — see [[hipaa-compliance-skill]] for the disclosure + consent message sent at this point and the yes/no/stop handling. No name, phone confirmation, or booking data may be collected before consent is given.
2. **`consent_pending`** — Owned by [[hipaa-compliance-skill]]. Blocks all further progress until the patient affirmatively consents (→ `identify`) or opts out (→ terminal).
3. **`identify`** — Look up `patient_phone` (the SMS `From` number) in the `patients` table.
   - Found → returning patient. Greet by name, skip name collection, move to `booking_intent`.
   - Not found → new patient, move to `collect_name`.
4. **`collect_name`** — Ask for the patient's full name; extract it from their reply via Claude; store on `patients`. (Storage of `patients.name` is encrypted at the application layer — see [[hipaa-compliance-skill]].)
5. **`collect_phone`** — The SMS `From` number is the phone of record by default. Only prompt explicitly for a different number if the patient indicates the appointment is for someone else or the callback number differs from the texting number.
6. **`booking_intent`** — Determine what the patient wants (new appointment, reschedule, cancel, question). Appointment/slot logic itself is out of scope for this skill — see below.
7. **`confirm_appointment`** — Once name and appointment details are known, send an explicit summary and require a clear yes/no confirmation before finalizing. Do not treat silence or an ambiguous reply as confirmation. Once confirmed, add one optional low-friction ask before advancing: "Want an email confirmation too? Reply with your email, or skip." — not a gate, just an offer; a skip/no-reply proceeds normally. Store a valid-looking reply on `patients.email` (nullable — see [[appointment-confirmation-skill]], which added this column; most patients will leave it unset and that's an expected, not an error, case for that skill's email channel).
8. **`done`** — Conversation resolved; return to `booking_intent` on the next inbound message if the patient starts a new request.

## Claude integration

- Client: `anthropic.Anthropic()` (reads `ANTHROPIC_API_KEY` from the environment — never hardcode).
- Model: `claude-opus-4-8` by default, per this project's model policy. Because this call runs on every inbound SMS (potentially high volume), if latency/cost becomes a concern, moving to `claude-sonnet-5` or `claude-haiku-4-5` is a reasonable cost/quality trade-off — but that's a deliberate decision to make explicitly, not a default to assume.
- Use **structured outputs** (`output_config={"format": {"type": "json_schema", "schema": ...}}`) so each turn returns a typed decision object instead of free text to parse:
  ```json
  {
    "intent": "greeting | provide_name | provide_email | booking_request | confirm | deny | ask_is_ai | off_topic | opt_out",
    "extracted_name": "string | null",
    "extracted_email": "string | null",
    "reply_text": "string",
    "next_stage": "identify | collect_name | collect_phone | booking_intent | confirm_appointment | done"
  }
  ```
  This avoids assistant-turn prefill (unsupported on Opus 4.8) and keeps the state machine deterministic and testable.
- This is a classification/extraction-style task, not open-ended reasoning — omit `thinking` (Opus 4.8 runs without it when the field is unset) and keep `output_config.effort` at `"low"` or `"medium"` to control latency and cost per message.
- Validate `reply_text` (non-empty, reasonable length, no leaked internal state) before handing it to [[sms-handler-skill]]'s `send_sms` — never forward raw model output unchecked.

### System prompt requirements

- Always identify as an automated/AI assistant. Never imply a human is responding.
- Never give medical advice or interpret symptoms — redirect any clinical question to practice staff.
- Stay strictly within scheduling scope: greeting, identity, booking intent, confirmation. Escalate (i.e. hand off / flag for a human) anything else.
- Don't ask the patient to repeat sensitive health information over SMS beyond what's operationally necessary to book an appointment.

## HIPAA / compliance guardrails

AI disclosure, consent capture, PHI field encryption, and outbound clinical-content filtering are owned by [[hipaa-compliance-skill]] — see that skill for the concrete implementation. What this skill is responsible for directly:

- Store only the minimum PHI needed for scheduling: name, phone, appointment time. Don't persist free-text health details from patient messages beyond what's needed for the booking itself.
- `ANTHROPIC_API_KEY` and Twilio credentials via env vars only, never logged.
- Prefer logging conversation stage transitions over full raw PHI-bearing message bodies where possible.
- Honor `STOP`/opt-out replies immediately at any stage (not just `consent_pending`) — treat as a terminal `intent: "opt_out"` that ends the conversation and suppresses further outbound messages to that number.
- No unattended clinical decision-making — this skill only handles scheduling logistics.

## Out of scope

- Actual calendar/slot-availability and booking persistence logic — this skill produces a `booking_request` intent and structured details; a separate booking-core component owns availability and the source of truth for appointments.
- SMS transport mechanics (webhook validation, `send_sms`, message persistence) — covered by [[sms-handler-skill]].
- Spec, plan, or task generation.

## Testing

- Mock the Anthropic client in unit tests — no real API calls.
- Table-driven tests over the state machine: full new-patient flow (through `consent_pending`), short returning-patient flow, ambiguous/off-topic replies, `STOP`/opt-out handling at multiple stages, and clinical-question redirection.
- Disclosure/consent-specific tests live in [[hipaa-compliance-skill]].
