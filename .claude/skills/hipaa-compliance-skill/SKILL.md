---
name: hipaa-compliance-skill
description: Enforces HIPAA-aware rules across all agent interactions — AI disclosure, patient consent before data collection, encryption of stored PHI, and blocking diagnosis/clinical content from outbound SMS. Implementation only, no spec/planning logic. Cross-cutting — use when touching disclosure text, consent handling, PHI storage/encryption, or outbound message content filtering in any of the other skills.
---

# HIPAA Compliance Skill

Cross-cutting implementation skill enforced across [[sms-handler-skill]], [[conversation-agent-skill]], [[appointment-booking-skill]], [[frontend-dashboard-skill]] (web booking consent), and [[voice-call-rag-skill]] (voice consent + outbound clinical-content filtering, reused rather than reimplemented there) — not a standalone service. It defines shared gates and utilities the other skills call into. Work covered by this skill goes straight to implementation — do not route it through `/sp.specify`, `/sp.plan`, or `/sp.tasks`.

**This skill changes the conversation state machine.** [[conversation-agent-skill]] must have a `consent_pending` stage inserted between `greeting` and `identify`/`collect_name` — see that skill's file for the updated stage list.

## 1. AI disclosure

- Sent once per conversation — as part of the very first outbound message (combined with the consent request, see below) — plus re-sent whenever the patient explicitly asks whether they're talking to a bot/AI/human.
- **Disclosure text is canned, not model-generated.** Store it as a fixed string (with a version identifier — see consent record below), not something Claude phrases each time. This guarantees the exact wording can't drift or be reworded away by the model.
- `conversation-agent-skill`'s structured-output intent enum must include an `ask_is_ai` (or similar) intent; when classified, the handler sends the canned disclosure text directly rather than a Claude-generated reply.

## 2. Consent — hard gate before any data collection

- New conversation stage: **`consent_pending`**, the first stage after `greeting`. No name, phone confirmation, message content beyond consent classification, or booking data may be collected or persisted while a conversation is in this stage.
- The first outbound message combines the AI disclosure and an explicit consent request, e.g.: *"Hi, I'm an automated scheduling assistant for [Practice]. I need your consent to collect your name and contact info to book an appointment. Reply YES to continue, or STOP to opt out."*
- Classifying the reply to the consent question is a **simple yes/no/stop match, not a full Claude call** — minimize processing of patient text before consent is obtained. A lightweight keyword/pattern check (`yes`, `y`, `ok`, `sure` → consent; `stop`, `no`, `cancel` → decline/opt-out; anything else → re-ask) is sufficient and avoids sending un-consented patient text to a third-party API before consent exists.
- On affirmative consent: write a `consents` row, advance to `identify`.
- On `STOP`/decline: write the `consents` row with `opted_out_at` set, end the conversation, suppress all further outbound messages to that phone number. This is terminal — same as the opt-out handling in [[conversation-agent-skill]], but reachable from `consent_pending` before any patient data exists yet.
- On an unrecognized reply: re-send the consent question once; if still unrecognized, treat as no consent given (do not proceed) rather than assuming intent.

### `consents` table

`id`, `patient_phone` (E.164), `consented_at` (nullable), `opted_out_at` (nullable), `consent_text_version` (string — matches the disclosure/consent text version in effect when sent), `method` (`sms_reply` / `web_form` / `voice_call` — [[frontend-dashboard-skill]]'s public booking page and [[voice-call-rag-skill]]'s phone flow both write consent records here through the same table rather than inventing their own), `created_at`.

Keep the wording version alongside the record so a later change to the consent text doesn't retroactively muddy what a patient actually agreed to.

## 3. Encryption of stored PHI (application-level)

- **Encrypt at the application layer**, in addition to whatever database/infra-level encryption at rest exists — this is defense in depth, not a replacement for infra controls.
- **Fields to encrypt:** `patients.name`, and `sms_messages.body` (inbound patient text can incidentally contain health information even though the agent never asks for it). Phone numbers stay in plaintext — Twilio already has them to deliver SMS, and they're needed as a plaintext lookup key for `identify`; encrypting them would require deterministic encryption or a hash-index workaround that isn't worth the complexity for this MVP.
- **Method:** `cryptography.fernet.Fernet` (symmetric, authenticated encryption) with the key loaded from an `ENCRYPTION_KEY` env var — never hardcoded, never logged, never committed. Keep this to a single active key for the MVP; don't build key-rotation infrastructure (multi-key `MultiFernet`, key IDs, rotation jobs) until compliance actually requires it — that's real complexity not needed yet.
- **Implementation shape:** a thin `encrypt_field(plaintext: str) -> bytes` / `decrypt_field(ciphertext: bytes) -> str` pair, used through a SQLAlchemy `TypeDecorator` (e.g. `EncryptedString`) on the `patients.name` and `sms_messages.body` columns, so callers read/write plain Python strings and never have to remember to encrypt manually.

## 4. No diagnosis/clinical content in outbound SMS

- Primary control: [[conversation-agent-skill]]'s system prompt already restricts Claude to scheduling scope and forbids medical advice.
- **This skill adds a defense-in-depth check on top of that**, not a replacement for it: a synchronous guard, `contains_clinical_content(text: str) -> bool`, runs on every outbound message **inside [[sms-handler-skill]]'s `send_sms`, before the Twilio API call** — not just in the conversation handler, so nothing can bypass it by calling `send_sms` directly.
- The guard is a keyword/pattern check (diagnostic terms, medication names, "diagnosis", "condition", symptom-description patterns) — acknowledged to be an imperfect last-resort net, not a clinical-NLP classifier. Its job is to catch obvious leaks, not to be exhaustive.
- If triggered: **block the send**, replace the outbound text with a generic fallback (e.g. *"Please call the office to discuss details."*), and log the block by conversation ID and reason code only — **never log the blocked content itself**, since the whole point is that it may contain PHI/clinical detail.

## Data model additions (owned by this skill)

- `consents` (see above).
- No new table for encryption — it's a column-level change (`TypeDecorator`) on existing `patients.name` and `sms_messages.body` columns from [[sms-handler-skill]] / [[conversation-agent-skill]].

## Out of scope

- General appointment/booking logic — [[appointment-booking-skill]].
- SMS webhook/send mechanics beyond the outbound content-filter hook — [[sms-handler-skill]].
- Conversational flow beyond the consent gate and disclosure intent — [[conversation-agent-skill]].
- Spec, plan, or task generation.

## Testing

- Disclosure sent exactly once per new conversation (combined with consent), and re-sent verbatim on an explicit "are you a bot" reply — assert exact string match, not just "similar" text.
- No `patients`/booking data is written while a conversation is in `consent_pending`.
- `STOP` at the consent stage is terminal and writes `opted_out_at` — no further outbound messages are sent to that number afterward.
- `patients.name` is stored as ciphertext in the raw DB row (assert the raw column value is not the plaintext name) and decrypts correctly on read.
- A message containing a blocklisted clinical term is blocked before reaching Twilio, replaced with the fallback text, and the log entry contains no clinical content.
