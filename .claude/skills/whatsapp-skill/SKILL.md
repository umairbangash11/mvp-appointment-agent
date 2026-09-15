---
name: whatsapp-skill
description: Handles the full WhatsApp booking channel (UAE market) via Twilio for the appointment booking agent — Twilio WhatsApp transport (webhook in, text/voice-note out), a bilingual (Arabic/English) conversation state machine, Groq Whisper speech-to-text for voice notes, ElevenLabs text-to-speech for voice-note replies, and a browser-based simulator endpoint/page for local testing without a live Twilio WhatsApp number. Implementation only, no spec/planning logic. Use when building or modifying the Twilio WhatsApp webhook, the WhatsApp conversation flow, STT/TTS wiring, or the /whatsapp-test simulator.
---

# WhatsApp Skill

Implementation-only skill for the WhatsApp booking channel of the appointment booking agent — replaces the earlier US-market `sms-handler-skill` and `voice-call-skill` for the UAE pivot. Transport, bilingual conversation logic, and compliance are one skill for this MVP, matching how the SMS/voice channels were structured before them. Work covered by this skill goes straight to implementation — do not route it through `/sp.specify`, `/sp.plan`, or `/sp.tasks`.

## Reuse — do not reimplement these

WhatsApp is a new *channel*, not a new booking system. This skill calls into what already exists rather than duplicating it:

| Concern | Reused from |
|---|---|
| Slot listing, appointment persistence, basic email confirmation | [[appointment-booking-skill]] — the agent calls its `Patient`/`Appointment` models and `send_booking_confirmation_email` directly. Booking facts (available slots, confirmed times) always come from the DB, never invented by an LLM. |
| Patient identity / new-vs-returning lookup | `patients` table, matched on the WhatsApp sender ID (Twilio's `From`, e.g. `whatsapp:+9715...`) hashed the same way as the old SMS channel did. |

## Stack

- Python 3.11+, FastAPI
- Twilio WhatsApp (via the Twilio Python SDK) — sandbox number for dev (`whatsapp:+14155238886`), an approved WhatsApp Business sender for production. Inbound webhook is form-encoded exactly like Twilio SMS; outbound replies are TwiML `<Message>` (text or `<Media>`).
- Groq `llama-3.3-70b-versatile` — used only as a fallback for free-text/off-topic queries outside the deterministic booking state machine (never to generate slot lists or booking confirmations).
- Groq Whisper (`whisper-large-v3`) — speech-to-text for inbound voice notes, auto-detects Arabic vs English.
- ElevenLabs (`eleven_multilingual_v2`, one voice ID) — text-to-speech for voice-note replies. One multilingual voice covers both languages; no separate per-language voice IDs.
- PostgreSQL — shared `conversation_sessions` (channel `whatsapp`) and `patients`/`appointments` tables from [[appointment-booking-skill]].

## Scope

In scope:
- `POST /whatsapp/webhook` — real Twilio inbound webhook (signature-validated outside dev).
- `POST /whatsapp/simulate` — browser-facing dev/test endpoint used by the `/whatsapp-test` frontend page; same conversation core as `/webhook`, no Twilio signature, JSON in/out instead of form/TwiML.
- The bilingual conversation flow: consent → new-vs-returning lookup → collect name → collect insurance (optional, patient-reported) → show slots → confirm → persist → send confirmation.
- Voice-note handling: download/transcribe inbound audio, run the transcript through the same conversation core as text, synthesize the reply back to speech when the inbound message was itself a voice note (text stays text-in/text-out).

Out of scope (do not implement here):
- Slot availability, holds, appointment persistence, email confirmation — [[appointment-booking-skill]].
- Staff-facing dashboard/appointments UI — [[frontend-dashboard-skill]]. The `/whatsapp-test` page here is a developer tool, not the patient- or staff-facing product surface.
- Real-time insurance eligibility verification — patient-reported only, same as the old SMS channel.
- Spec, plan, or task generation.

## API contract

### `POST /whatsapp/webhook` (real Twilio)

Form-encoded fields: `From`, `Body`, `NumMedia`, `MediaUrl0`, `MediaContentType0`.

1. Validate `X-Twilio-Signature` against `TWILIO_AUTH_TOKEN` before trusting the payload (skipped automatically when `ENVIRONMENT=development`, since there's no publicly-signed callback URL in local dev); reject with 403 on failure.
2. If `NumMedia > 0` and the media is `audio/*`: download it (Twilio media requires Basic Auth with the account SID/token), transcribe with Groq Whisper → `(text, language)`.
3. Otherwise: use `Body` as `text`, detect language from an Arabic-Unicode-range heuristic.
4. Run `(text, language)` through the shared conversation core.
5. If the inbound message was a voice note: synthesize the reply via ElevenLabs, write it to `static/audio/<uuid>.mp3` (served via a `/static` mount so Twilio can fetch it), reply with TwiML `<Message><Media>`. If ElevenLabs isn't configured (no API key), fall back to a text TwiML reply.
6. Otherwise: reply with TwiML `<Message><Body>`.

### `POST /whatsapp/simulate` (browser simulator — not a Twilio call)

Multipart form: `phone` (a simulator session identifier standing in for a WhatsApp sender ID), optional `text`, optional `audio` file upload (webm/ogg blob from the browser's `MediaRecorder`).

Same transcribe-or-use-text → conversation-core → reply pipeline as `/webhook`, but:
- No Twilio signature check.
- Returns JSON: `{"reply_text": str, "language": "ar"|"en", "transcribed_text": str|null, "audio_base64"?: str}` — `audio_base64` is present only when the inbound message was a voice note (mirrors input modality in the output, i.e. voice-in gets voice-out, text-in gets text-out).

Both endpoints call the exact same conversation-handling function — there is no duplicated booking logic between the real channel and the dev/test simulator.

## Conversation flow (bilingual, deterministic state machine)

Mirrors the old SMS flow's proven pattern (keyword-driven state machine, not LLM-driven, so booking-critical replies are never hallucinated), simplified per the UAE spec (no DOB collection; phone comes from the WhatsApp sender ID automatically instead of being asked):

1. **`consent`** — first message from a phone number always gets the AI-disclosure + consent request (bilingual, selected by an Arabic-Unicode-range heuristic on the first message, or by Whisper's detected language for a voice note). Yes → look up the phone in `patients`; found → greet by name and skip straight to slot selection or insurance question; not found → `collect_name`. Stop/opt-out keywords (English *and* Arabic) are honored at **any** step, not just here.
2. **`collect_name`** — ask full name.
3. **`collect_insurance`** — one optional question (carrier name, or SKIP/SELF-PAY, bilingual keywords for both) — patient-reported only, never verified against a payer.
4. **`select_slot`** → **`confirm`** — numbered slot list, explicit yes/no confirmation (bilingual yes/no/stop keyword lists — not an LLM classification, for the same reason the SMS channel didn't use one for consent: minimize processing of un-confirmed replies through a third-party API).
5. **`done`** — booking persisted (`booking_channel=whatsapp`), confirmation email sent if the patient gave one. Any further free-text message on a `done` session is answered by the Groq fallback (bilingual system prompt, AI-disclosure/no-diagnosis rules), not the state machine.

A small static FAQ lookup (hours/location/phone/insurance, bilingual, authored not generated) runs ahead of every step, same shortcut role it played in the old voice channel.

## HIPAA / NABIDH rules (this channel)

- Always identify as an AI, in the first outbound message of every conversation (bilingual disclosure string, not model-generated).
- Consent is a hard gate: no name/insurance data is collected or persisted before an explicit "yes".
- No diagnosis or medical advice — the Groq fallback's system prompt forbids it explicitly, and the FAQ table never contains clinical content.
- PHI (patient name, insurance info) stays behind the same `EncryptedString` `TypeDecorator` pattern already used by `patients` — this skill doesn't add new PHI fields.
- `/whatsapp/simulate` is a **dev/test-only** endpoint — it must never be exposed on a production frontend deployment without additional access control, since it accepts arbitrary phone identifiers with no Twilio-level sender verification.

## Testing

- Mock Groq (chat + Whisper), ElevenLabs, and Twilio in tests — no real API calls.
- Agent-level tests exercise the real conversation core against a test DB directly (bypassing the HTTP layer) — full booking flow in English, full flow in Arabic, STOP opt-out at multiple stages, new-vs-returning patient lookup.
- Route-level tests mock the conversation core and only check request/response wiring: TwiML shape for `/webhook`, JSON shape for `/simulate`, voice-note transcribe→synthesize wiring, and signature rejection outside dev.
- A booking with no patient email confirms successfully and skips (not fails) the email send, same guarantee as [[appointment-booking-skill]].
