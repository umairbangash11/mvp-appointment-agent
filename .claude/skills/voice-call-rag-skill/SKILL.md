---
name: voice-call-rag-skill
description: Handles inbound voice calls (Twilio Voice) with a RAG pipeline (pgvector + LangChain + Groq) grounding responses in a clinic knowledge base to prevent hallucination. Implementation only, no spec/planning logic. Use when building voice webhooks, speech-to-text/TTS handling, the RAG retrieval pipeline, or the knowledge-base admin endpoints.
---

# Voice Call + RAG Skill

Implementation-only skill for inbound voice calls and the RAG knowledge base backing them. Work covered by this skill goes straight to implementation — do not route it through `/sp.specify`, `/sp.plan`, or `/sp.tasks`.

## Reuse — do not reimplement these

Voice is a new *channel*, not a new booking system or a new compliance model. This skill must call into what already exists rather than duplicating it:

| Concern | Reused from |
|---|---|
| AI disclosure + consent gating | [[hipaa-compliance-skill]] — same `consents` table, new `method: "voice_call"` value (that table's `method` field is now genuinely multi-valued: `sms_reply` / `web_form` / `voice_call` — updated there too) |
| No-diagnosis / no-clinical-content filtering | [[hipaa-compliance-skill]]'s `contains_clinical_content()` — reused on **both** the patient's incoming question (to short-circuit medical questions before RAG search) and the outbound response (before TTS), not reimplemented for voice |
| Slot availability, holding, booking confirmation | [[appointment-booking-skill]]'s functions (`list_available_slots`, `hold_slot`, `confirm_booking`) — called directly, not re-derived from RAG documents. Never let the RAG/Groq layer *invent* an appointment time; live availability always comes from that skill |
| Post-call SMS confirmation | [[sms-handler-skill]]'s `send_sms` |
| Patient identity / lookup | [[conversation-agent-skill]]'s `patients` table, matched on caller phone number the same way SMS matches on `From` |

## Why Groq here and not Claude

[[conversation-agent-skill]] uses Claude for SMS because SMS is asynchronous — a couple seconds of latency is invisible to the patient. A live phone call is not: Twilio expects a webhook response fast enough that the call doesn't sit in dead air, so this skill uses Groq specifically for its low-latency inference. This is a deliberate per-channel choice, not an inconsistency — don't "fix" it by switching either channel to match the other.

## Stack

- Python 3.11+, FastAPI
- Twilio Voice API (TwiML)
- Groq API, `llama-3.3-70b-versatile` (OpenAI-compatible chat completions shape)
- PostgreSQL + `pgvector` extension
- OpenAI embeddings API (verify the current recommended embedding model/dimensions against OpenAI's docs before hardcoding one — this skill assumes 1536-dimensional embeddings, matching `text-embedding-3-small`, but that should be confirmed rather than taken on faith)
- LangChain — used narrowly for the retrieval step; this is a simple enough RAG pipeline (embed → pgvector similarity query → prompt assembly) that hand-rolling it with raw SQL and an HTTP client is also a legitimate, lower-dependency choice. LangChain's import paths shift between versions frequently — verify current syntax against its docs before writing code, don't assume a remembered import path is still correct.
- Google Cloud Text-to-Speech for agent voice. **Auth mechanism needs confirming before implementation**: `GOOGLE_TTS_KEY` as named suggests a bare API key, but Google Cloud TTS typically authenticates via a service-account JSON credential, not a simple key — confirm which is intended. This skill documents the env var as given but flags the ambiguity rather than guessing silently.

## Env vars (additions/changes to [[env-config-skill]])

- `GROQ_API_KEY` — already existed in [[env-config-skill]] as **optional/reserved** ("not consumed by any implemented skill yet"). It's now consumed — move it to the **required** table.
- `GOOGLE_TTS_KEY` — new, required.
- `OPENAI_API_KEY` — new, required (embeddings only — this project does not use OpenAI for chat/generation, only its embeddings endpoint).
- `PGVECTOR_ENABLED` — new, optional, default `true` (feature flag; false disables RAG search and falls straight to human handoff, useful for a deploy where the extension isn't provisioned yet).
- `HUMAN_HANDOFF_PHONE_NUMBER` — new, required. The given env var list didn't include a transfer target for the "if unsure → human handoff" rule; a `<Dial>` to a real clinic line needs a number to dial. Added here since nothing else covers it.
- **`TWILIO_PHONE_NUMBER` vs. the existing `TWILIO_FROM_NUMBER`**: [[env-config-skill]] already defines `TWILIO_FROM_NUMBER` for SMS. A single Twilio number normally handles both SMS and Voice — reuse `TWILIO_FROM_NUMBER` rather than adding a near-duplicate variable, unless the clinic genuinely uses two separate Twilio numbers, in which case name the second one `TWILIO_VOICE_NUMBER` explicitly rather than the ambiguous `TWILIO_PHONE_NUMBER`.

## Database tables

### `voice_calls` (as specified, with one addition)

`id`, `patient_phone`, `call_sid` (Twilio's, unique), `status`, `duration`, `created_at`, **plus `stage`** (addition — not in the original sketch). A call is stateful across multiple webhook round-trips exactly like an SMS conversation is; without a stage column there's nowhere to track "are we still waiting on consent" vs. "mid-conversation" vs. "booking in progress" between one `/voice/gather` POST and the next. Stages: `greeting` → `consent_pending` → `in_conversation` → `booking_in_progress` → `done`.

### `call_transcripts` (as specified)

`id`, `call_id` (FK to `voice_calls`), `speaker` (`patient` / `agent`), `text`, `timestamp`. This is the conversation history — each `/voice/gather` turn reconstructs recent context by querying this table (last ~10 turns, bounded to control prompt size and latency) rather than relying on any in-memory state, since each webhook POST is a fresh, stateless HTTP request.

### `rag_documents` (as specified)

`id`, `category` (`clinic_info` / `doctor_info` / `services_pricing` / `insurance` / `appointment_rules` / `faq`), `title`, `content`, `embedding` (`vector(1536)` — see the embedding-dimension caveat above), `created_at`. Requires `CREATE EXTENSION IF NOT EXISTS vector;` and an approximate-nearest-neighbor index (`ivfflat` or `hnsw`) on `embedding` for query performance once the table has meaningful volume.

**No separate storage for the "do not answer" medical-question list.** Storing "don't answer X" as a retrievable document is the wrong shape — semantic similarity search would retrieve it *because* it's similar to the medical question being asked, which is a confusing way to implement a refusal. Instead, [[hipaa-compliance-skill]]'s `contains_clinical_content()` guard runs on the **incoming patient question** before RAG search even happens: if it looks clinical, skip retrieval entirely and go straight to the canned refusal + handoff response.

### `rag_queries` (as specified)

`id`, `query_text`, `retrieved_docs` (JSON — doc IDs + similarity scores), `response`, `call_id`. Audit trail for what the RAG pipeline actually retrieved and answered on each turn — useful for debugging hallucination complaints and reviewing knowledge-base gaps.

## Part 1 — Voice call flow

### `POST /voice/inbound`

Twilio webhook on an incoming call. Validate the Twilio signature exactly as [[sms-handler-skill]] does for SMS. Create a `voice_calls` row (`stage='greeting'`). Return TwiML: play the AI-disclosure + consent request (same canned wording pattern as [[hipaa-compliance-skill]]'s SMS consent message, phrased for voice — short, since it will be spoken), then `<Gather input="speech">` for a yes/no reply. Advance `stage` to `consent_pending`.

### `POST /voice/gather`

Handles every subsequent turn. Twilio posts `SpeechResult` (transcribed patient speech) and `CallSid`. Look up the `voice_calls` row by `call_sid`; branch on `stage`:

- **`consent_pending`**: classify the reply as yes/no/unclear with a simple keyword check (not a full Groq call — same reasoning as [[hipaa-compliance-skill]]'s SMS consent gate: minimize processing of un-consented speech). Yes → write the `consents` row (`method='voice_call'`), advance to `in_conversation`. No/unclear-after-one-retry → play a polite close and hang up; no further processing.
- **`in_conversation`** / **`booking_in_progress`**: this is the RAG/Groq turn — see Part 2. The classifier first determines whether the turn is a **booking-intent** turn (delegate to [[appointment-booking-skill]]) or an **informational** turn (RAG pipeline). Either way, the grounding context fed to Groq is always either (a) live data from [[appointment-booking-skill]] for booking-related facts, or (b) retrieved `rag_documents` for informational facts — **never Groq's own unguided knowledge**, for booking facts most of all: an invented appointment time is worse than an invented clinic address.

Every turn writes two `call_transcripts` rows (patient speech, agent response) before returning TwiML. The response TwiML plays the synthesized audio (see TTS/audio serving below) and issues another `<Gather>` to continue, unless the turn ended in a booking confirmation or a human handoff, in which case the call proceeds to `<Dial>` (handoff) or a closing message + hangup (booking done).

### `POST /voice/status`

Twilio's call-status callback (fires on call completion/failure/etc.). Update `voice_calls.status`/`duration`. If a booking was confirmed during the call, send the SMS confirmation via [[sms-handler-skill]]'s `send_sms` here — this is the natural place for it since it fires once the call is definitively over, not mid-conversation.

## Part 2 — RAG pipeline

```
patient question (post-consent, post-clinical-content-check)
        ↓
embed query (OpenAI embeddings)
        ↓
pgvector cosine-similarity search over rag_documents → top 3
        ↓
if zero relevant docs found (below a similarity threshold — pick one empirically,
don't retrieve at any similarity no matter how low):
    → canned "I don't have that info, let me connect you to the doctor" + human handoff
else:
    → Groq call, system prompt below, context = the top 3 docs' content ONLY
        ↓
    → contains_clinical_content() check on the response (defense in depth — the
      system prompt already forbids this, this is the backstop, same pattern as
      hipaa-compliance-skill's SMS outbound filter)
        ↓
    → enforce a hard response-length cap (max ~2 sentences) before TTS — same
      defense-in-depth reasoning: don't rely solely on the system prompt telling
      Groq to keep it short; truncate/reject an over-length response rather than
      reading a paragraph aloud on a phone call
```

### System prompt (as specified)

```
You are an AI booking assistant for [Clinic Name].

STRICT RULES:
1. Only use provided context
2. Never make up information
3. Never give medical advice
4. If unsure say: I don't have that info
5. Keep responses SHORT for phone calls
6. Never discuss diagnosis
7. Booking questions only
```

`[Clinic Name]` is `PRACTICE_NAME` from [[env-config-skill]], not hardcoded.

### Anti-hallucination rules (as specified, plus the enforcement mechanism for each)

- Agent ONLY uses RAG data — enforced by only ever including retrieved-document content (or live [[appointment-booking-skill]] data) in the prompt's context, never asking Groq to answer from its own training.
- Never assume or guess — enforced by the "zero relevant docs → refuse + handoff" branch above, gated on a similarity threshold, not "did retrieval return anything at all" (a low-similarity match is still a guess).
- If unsure → human handoff — same branch, plus an explicit patient request ("talk to a person") always triggers handoff regardless of RAG confidence.
- Medical questions → reject — `contains_clinical_content()` on the incoming question, before retrieval.
- Short, clear phone responses, max 2 sentences — enforced by the length cap described above, not just the prompt instruction.

## Text-to-speech and audio serving

TwiML's `<Play>` verb needs a **publicly reachable URL** to an audio file — it cannot play raw bytes inline. After Google TTS synthesizes the response, write the audio to a short-lived location and serve it from a FastAPI endpoint (e.g. `GET /voice/audio/{id}.mp3`), then reference that URL in the `<Play>` response. Don't accumulate these files indefinitely — expire/delete them shortly after the call ends (they're derived, regenerable content, not a record that needs retention).

**Simpler alternative worth considering**: Twilio's own `<Say voice="Google.en-US-Neural2-C">` uses Google-family voices natively, with no separate Google Cloud TTS API call, no `GOOGLE_TTS_KEY`, and no audio-file-serving step at all. The stated stack explicitly calls out a separate Google TTS integration, so this skill documents that path — but if the only goal is "sounds like a Google voice," the native Twilio option is meaningfully less implementation surface and worth raising with the user before building the audio-serving pipeline.

## Operational note: latency budget

Each `/voice/gather` turn does (in the worst case): embed the query → pgvector search → Groq generation → clinical-content/length checks → Google TTS synthesis → write the audio file, all inside a single Twilio webhook response. Twilio has a limited patience window before a call feels broken (dead air). Groq's low latency is the reason it was chosen for this channel, but the embedding call and TTS synthesis are the other two network round-trips in the critical path — budget for them explicitly when this gets built, and consider a "please hold" filler TwiML response if the pipeline can't reliably finish inside an acceptable window.

## Endpoints (RAG admin)

`POST /rag/search`, `POST /rag/add-document`, `GET /rag/documents`, `DELETE /rag/document/{id}` — as specified. **Require the doctor JWT from [[doctor-auth-admin-skill]] on all four** — the given list didn't state an auth requirement, but a knowledge-base-mutation endpoint open to the public internet is an obvious gap to close. `/voice/gather` calls the underlying retrieval function directly (in-process), not over HTTP, for latency; `/rag/search` is the externally-callable version for admin/testing use, and a natural fit for a future knowledge-base management view in [[frontend-dashboard-skill]]'s Settings page (not built now — flagging the fit, not adding a sixth page unasked).

## HIPAA voice rules — enforcement summary

- First message identifies as AI, verbal consent required before proceeding — `consent_pending` stage above, mirroring [[hipaa-compliance-skill]].
- Never record without consent — **this skill does not enable Twilio's full-call audio recording by default.** `<Gather input="speech">` produces a text transcript (`call_transcripts.text`) without requiring Twilio's separate call-recording feature (`<Record>` / `record=true`). Raw audio recording is not needed anywhere in the stated call flow; if it's ever required later (e.g. quality review), that needs its own explicit disclosure ("this call may be recorded") and consent step, separate from the base AI-disclosure consent — don't bundle the two.
- No diagnosis discussed — `contains_clinical_content()`, both directions.
- Keep PHI minimal on call — don't ask the patient to repeat sensitive details over voice beyond what's needed to identify them and book (name, phone, reason limited to a non-clinical category), same principle as [[conversation-agent-skill]]'s SMS flow.

## Out of scope

- Building the LangChain/embedding pipeline's exact current-version syntax without verifying against up-to-date docs — flagged throughout, not resolved here.
- Multi-language voice support.
- Spec, plan, or task generation.

## Testing

- A call that never gives consent hangs up cleanly and writes no PHI beyond the phone number and call metadata.
- A clinical/medical question is refused before any RAG search happens (assert no `rag_queries` row with retrieved docs for that turn — or if logged, logged as a refusal, not a normal answer).
- A query with no sufficiently-similar `rag_documents` triggers the "I don't have that info" + handoff path, not a best-guess answer.
- A response over the length cap is truncated/rejected before reaching TTS.
- Booking facts (available times) always come from [[appointment-booking-skill]]'s live functions in the test fixtures, never from a `rag_documents` row — a regression here (someone adding "available slots" as static RAG content) should fail a test.
- Twilio signature validation rejects a forged webhook on all three voice endpoints, same as the SMS webhook.
