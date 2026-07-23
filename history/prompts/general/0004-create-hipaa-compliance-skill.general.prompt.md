---
id: 0004
title: Create HIPAA compliance skill
stage: general
date: 2026-07-23
surface: agent
model: claude-sonnet-5
feature: none
branch: master
user: umairbangash11
command: /sp.skill
labels: ["skills", "hipaa", "compliance", "encryption", "consent", "cross-cutting"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
 - .claude/skills/hipaa-compliance-skill/SKILL.md
 - .claude/skills/conversation-agent-skill/SKILL.md
 - history/prompts/general/0004-create-hipaa-compliance-skill.general.prompt.md
tests:
 - none
---

## Prompt

/sp.skill

Name: hipaa-compliance-skill
Description: Enforces HIPAA rules
across all agent interactions.
Ensures AI disclosure on every
message, gets patient consent
before data collection, encrypts
stored data, never includes
diagnosis in SMS messages.
Implementation only.

## Response snapshot

Flagged a direct conflict with the existing `conversation-agent-skill`, which only disclosed AI status on the first message of a conversation, versus this new skill's literal "every message" wording. Asked three clarifying questions (disclosure cadence, consent model — hard gate vs. implied, encryption scope — application-level vs. infra-only); user chose the recommended option on all three: once-per-conversation-plus-on-request disclosure, a hard consent gate requiring explicit opt-in before any data collection, and application-level field encryption. Created `.claude/skills/hipaa-compliance-skill/SKILL.md` as a cross-cutting skill (not a standalone service) covering: canned (non-model-generated) AI disclosure text; a new `consent_pending` conversation stage with keyword-based yes/no/stop classification (deliberately not a full Claude call, to minimize processing of un-consented patient text) and a `consents` table; application-level Fernet field encryption for `patients.name` and `sms_messages.body` via a SQLAlchemy `TypeDecorator`, explicitly deferring key-rotation infrastructure as unneeded complexity for the MVP; and a defense-in-depth `contains_clinical_content()` guard enforced inside `sms-handler-skill`'s `send_sms`, before every Twilio call. Then updated `conversation-agent-skill/SKILL.md` to insert the `consent_pending` stage into its state machine, add an `ask_is_ai` intent, and replace its duplicated HIPAA guardrail text with a pointer to the new skill to avoid the two files drifting out of sync.

## Outcome

- ✅ Impact: Fourth Claude Code Skill added, and a real design inconsistency between it and the existing conversation skill was caught and resolved by editing both files rather than leaving them contradictory.
- 🧪 Tests: none (skill authoring only)
- 📁 Files: .claude/skills/hipaa-compliance-skill/SKILL.md (created), .claude/skills/conversation-agent-skill/SKILL.md (edited — state machine, intent enum, guardrails section, testing section)
- 🔁 Next prompts: Implement the `consents` table migration and the SQLAlchemy `EncryptedString` TypeDecorator; wire `contains_clinical_content()` into `sms-handler-skill`'s actual `send_sms` implementation once it exists; decide on `ENCRYPTION_KEY` provisioning (secrets manager vs. env var) for each deployment environment.
- 🧠 Reflection: A cross-cutting compliance skill requested after the subsystem skills already exist is likely to contradict something already written — worth explicitly diffing the new skill's requirements against prior skills' stated behavior (here: disclosure cadence) before writing, and editing the earlier file in place rather than letting two skills silently disagree.

## Evaluation notes (flywheel)

- Failure modes observed: none — the conflict was caught before writing rather than after.
- Graders run and results (PASS/FAIL): N/A (no automated grading configured)
- Prompt variant (if applicable): none
- Next experiment (smallest change to try): when a fifth skill is requested, proactively grep the existing `.claude/skills/*/SKILL.md` files for overlapping stage names/tables before writing, rather than relying on remembering prior content from conversation context alone.
