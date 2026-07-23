---
id: 0014
title: Add multi-channel appointment confirmation
stage: general
date: 2026-07-23
surface: agent
model: claude-sonnet-5
feature: none
branch: master
user: umairbangash11
command: none
labels: ["skills", "twilio", "outbound-voice", "sendgrid", "sms", "gap-filling"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
 - .claude/skills/appointment-confirmation-skill/SKILL.md
 - .claude/skills/env-config-skill/SKILL.md
 - .claude/skills/conversation-agent-skill/SKILL.md
 - .claude/skills/appointment-booking-skill/SKILL.md
 - history/prompts/general/0014-add-voice-call-confirmation-channel.general.prompt.md
tests:
 - none
---

## Prompt

Add voice call confirmation
in addition to SMS and Email.

When appointment is booked:

1. SMS Confirmation:
   "Appointment confirmed!
    Monday 10AM Dr. Smith"

2. Email Confirmation:
   Full appointment details
   via SendGrid

3. Voice Call Confirmation:
   Agent calls patient back:
   "Hello! This is AI assistant
    from Dr. Smith's Clinic.
    Your appointment is confirmed
    for Monday at 10AM.
    Press 1 to confirm
    Press 2 to cancel"

All 3 channels together!

## Response snapshot

This followed a rejected clarifying-question attempt (email vs. SMS vs. both) where the user chose to answer with the full spec directly instead. Created `.claude/skills/appointment-confirmation-skill/SKILL.md` as a new skill rather than extending an existing one, since it reuses pieces from three different skills without being a natural fit for any single one: SMS from `sms-handler-skill`, the SendGrid client pattern from `doctor-auth-admin-skill`, and Twilio Voice/TwiML mechanics from `voice-call-rag-skill` — but the last one only had *inbound* call handling built, so outbound calling (Twilio's `calls.create()`, a new `API_BASE_URL` env var so Twilio knows where to fetch TwiML from, new `/voice/outbound/confirm` and `/voice/outbound/gather` DTMF-handling endpoints) is new capability, not reuse. Caught and closed a real blocking gap before it could silently break: no skill anywhere collects a patient email address (`conversation-agent-skill`'s `patients` table has no email column, the web intake form doesn't ask for one either) — added `patients.email` (nullable) and a low-friction optional ask at the `confirm_appointment` stage rather than a new hard gate, with the email channel gracefully skipping (not erroring) when unset. Made a deliberate design call for the voice channel: since the confirmation message is a fixed template with appointment data substituted in (not LLM-generated), skip `voice-call-rag-skill`'s heavier Google Cloud TTS + audio-file-serving pipeline entirely and use Twilio's native `<Say voice="Google...">` instead — simpler, and structurally immune to hallucination since there's no generation step at all on a message this consequential. Designed the "Press 2 to cancel" path to call `appointment-booking-skill`'s existing `cancel_appointment` (reused, not reimplemented) plus fire a cancellation SMS for a written record. Added a `confirmation_log` table for auditing across all three independent delivery channels, and wired the actual trigger point into `appointment-booking-skill.confirm_booking()` as a post-commit call-out (explicitly not part of the transaction, so a notification failure can never roll back a confirmed booking). Updated `env-config-skill` (`API_BASE_URL`) and `conversation-agent-skill` (optional email ask, new `provide_email` intent) to match.

## Outcome

- ✅ Impact: Ninth skill added, closing a real cross-cutting gap (no patient email anywhere in the system) that would have silently broken "all 3 channels together" if not caught, and adding the project's first outbound-calling capability distinct from `voice-call-rag-skill`'s inbound-only design.
- 🧪 Tests: none (skill authoring only)
- 📁 Files: .claude/skills/appointment-confirmation-skill/SKILL.md (created), .claude/skills/env-config-skill/SKILL.md (edited — API_BASE_URL), .claude/skills/conversation-agent-skill/SKILL.md (edited — optional email step, intent enum), .claude/skills/appointment-booking-skill/SKILL.md (edited — confirm_booking trigger call-out)
- 🔁 Next prompts: Still-open gaps this turn didn't resolve (and shouldn't have, out of scope): the `clinic_settings` table (address/working hours) the email template wants but doesn't have, and the recurring payments/billing gap (now surfaced four times). Implementation of the actual outbound TwiML endpoints and confirmation_log queries is still pending, same as every other skill in this project.
- 🧠 Reflection: Treating "all 3 channels together" literally (rather than silently making email best-effort without flagging why) surfaced a gap — no patient email exists anywhere — that would otherwise have been discovered only at implementation or runtime. The deliberate choice to keep the outbound voice message template-only (no LLM) rather than routing it through the existing RAG pipeline for consistency is worth noting as a case where *not* reusing an existing pattern was the right call — reuse is the default, but a fixed, highly consequential message is exactly the case where adding a generation step is a regression, not an improvement.

## Evaluation notes (flywheel)

- Failure modes observed: an AskUserQuestion call was rejected by the user mid-turn (they wanted to answer via free text instead of the offered options) — handled by asking what they'd like to clarify directly, per the tool's guidance, rather than re-issuing the same structured question.
- Graders run and results (PASS/FAIL): N/A (no automated grading configured)
- Prompt variant (if applicable): none
- Next experiment (smallest change to try): when a rejected AskUserQuestion is followed by a full free-text answer that supersedes the original question entirely, don't re-ask the original structured question afterward — the user's answer already resolved it, as happened here (they specified "SMS + Email + Voice, all three" which answers the channel question directly).
