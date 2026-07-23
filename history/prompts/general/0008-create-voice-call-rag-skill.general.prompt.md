---
id: 0008
title: Create voice call RAG skill
stage: general
date: 2026-07-23
surface: agent
model: claude-sonnet-5
feature: none
branch: master
user: umairbangash11
command: none
labels: ["skills", "voice", "twilio", "rag", "pgvector", "groq", "hallucination", "reconciliation"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
 - .claude/skills/voice-call-rag-skill/SKILL.md
 - .claude/skills/hipaa-compliance-skill/SKILL.md
 - .claude/skills/env-config-skill/SKILL.md
 - history/prompts/general/0008-create-voice-call-rag-skill.general.prompt.md
tests:
 - none
---

## Prompt

Create a skill for voice call
with RAG integration:

Name: voice-call-rag-skill

Description:
Handle inbound voice calls with
RAG (Retrieval Augmented Generation)
to prevent hallucination in US
Doctor Appointment Booking Agent.

[full stack, call flow, TwiML flow, HIPAA voice rules, RAG knowledge base categories,
RAG pipeline, anti-hallucination rules, system prompt, database tables (voice_calls,
call_transcripts, rag_documents, rag_queries), API endpoints, environment variables
as provided verbatim by the user]

Implementation only.
No spec or planning logic.

## Response snapshot

Did not invoke the `claude-api` skill — this request explicitly names Groq and OpenAI as the LLM/embedding providers, which is the documented skip condition (another provider named in the query overrides the Claude/Anthropic trigger). Created `.claude/skills/voice-call-rag-skill/SKILL.md`, leading with an explicit "reuse — do not reimplement" table pointing voice-call handling at existing skills: consent/disclosure and clinical-content filtering from `hipaa-compliance-skill`, live slot/booking data from `appointment-booking-skill` (never letting Groq invent an appointment time), post-call SMS from `sms-handler-skill`, and patient lookup from `conversation-agent-skill`. Explained the deliberate Groq-vs-Claude split (latency-critical live call vs. async SMS) as a design choice, not an inconsistency to fix. Filled several gaps in the given spec: added a `stage` column to `voice_calls` (stateful across webhook round-trips, same reasoning as SMS conversations); designed the "do not answer medical questions" requirement as a pre-retrieval clinical-content check rather than a retrievable RAG document (avoids semantic-similarity search surfacing the refusal list because it matches the forbidden question); added a `HUMAN_HANDOFF_PHONE_NUMBER` env var for the "if unsure → human handoff" `<Dial>` target, missing from the given env var list; flagged that `TWILIO_PHONE_NUMBER` as given duplicates the already-existing `TWILIO_FROM_NUMBER` and should reuse it; flagged the Google TTS auth-mechanism ambiguity (bare API key vs. service-account JSON) without resolving it silently; documented that TwiML `<Play>` needs a public URL, requiring a short-lived audio-serving endpoint, and noted Twilio's native `<Say voice="Google...">` as a much lower-complexity alternative worth raising before building that pipeline; called out the latency budget across embedding + Groq + TTS calls inside a single webhook response as an operational risk. Reconciled cross-skill state: updated `hipaa-compliance-skill`'s `consents.method` field (previously only `sms_reply`, despite `frontend-dashboard-skill` already having been told to use `web_form` in an earlier turn without the source-of-truth table being updated to match) to properly enumerate `sms_reply` / `web_form` / `voice_call`; updated `env-config-skill` to move `GROQ_API_KEY` from optional/reserved to required (now actually consumed) and add `GOOGLE_TTS_KEY`, `OPENAI_API_KEY`, `HUMAN_HANDOFF_PHONE_NUMBER` (required) and `PGVECTOR_ENABLED` (optional, default true).

## Outcome

- ✅ Impact: Eighth Claude Code Skill added — the largest and most cross-cutting one yet, since voice touches consent, content filtering, booking, and SMS confirmation all at once. Caught and fixed a latent inconsistency from an earlier turn (`consents.method` never actually updated to `web_form` despite being referenced that way) while resolving it.
- 🧪 Tests: none (skill authoring only)
- 📁 Files: .claude/skills/voice-call-rag-skill/SKILL.md (created), .claude/skills/hipaa-compliance-skill/SKILL.md (edited — consents.method, cross-reference list), .claude/skills/env-config-skill/SKILL.md (edited — GROQ_API_KEY promoted to required, new vars added)
- 🔁 Next prompts: Confirm Google TTS auth mechanism before implementation; decide whether to keep the separate Google Cloud TTS integration or switch to Twilio's native Google-family `<Say>` voices to cut implementation surface; pick and confirm the OpenAI embedding model/dimensions being targeted; still-open payments/billing gap (flagged in two prior skills) remains unresolved.
- 🧠 Reflection: This is the first skill in the session large enough that "reuse, don't reinvent" needed to be the very first section rather than an afterthought — with eight skills now in play, the biggest risk stopped being missing pieces and became silently rebuilding something (consent gating, content filtering, booking logic) that already exists elsewhere with subtly different behavior. Leading with an explicit reuse table made every subsequent design choice ("what grounds the Groq prompt for booking facts") fall out naturally instead of needing to be re-derived.

## Evaluation notes (flywheel)

- Failure modes observed: found a real cross-skill drift bug from turn 6 (frontend-dashboard-skill referenced `consents.method = 'web_form'` but hipaa-compliance-skill's table definition was never actually updated to include it) — worth noting this can happen silently when an edit "mentions" a change in one file's prose without propagating the actual schema definition in the owning file.
- Graders run and results (PASS/FAIL): N/A (no automated grading configured)
- Prompt variant (if applicable): none
- Next experiment (smallest change to try): when editing a dependent skill to reference a value/field defined in another skill's schema (like `consents.method`), immediately check whether the owning skill's file needs the corresponding edit too, rather than assuming a mention in the dependent file is sufficient — this turn's fix should have happened in turn 6.
