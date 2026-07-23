---
id: 0003
title: Create appointment booking skill
stage: general
date: 2026-07-23
surface: agent
model: claude-sonnet-5
feature: none
branch: master
user: umairbangash11
command: /sp.skill
labels: ["skills", "postgresql", "booking", "concurrency", "fastapi"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
 - .claude/skills/appointment-booking-skill/SKILL.md
 - history/prompts/general/0003-create-appointment-booking-skill.general.prompt.md
tests:
 - none
---

## Prompt

/sp.skill

Name: appointment-booking-skill
Description: Handles appointment
slot selection and confirmation.
Checks available slots, presents
options to patient, confirms
booking, stores appointment data
securely. Implementation only.

## Response snapshot

Asked one clarifying question — where appointment availability comes from (internal Postgres only vs. an external calendar integration like Google Calendar) — since that fork materially changes the design and the prior two skills didn't establish it. User chose internal Postgres only for the MVP. Created `.claude/skills/appointment-booking-skill/SKILL.md`: the booking core that `conversation-agent-skill` hands off to. Defines `providers`/`appointment_slots`/`appointments` tables, a function-level API (`list_available_slots`, `hold_slot`, `confirm_booking`, `release_hold`, `cancel_appointment`) rather than a public HTTP surface, an atomic conditional-UPDATE hold pattern to prevent double-booking races under concurrent SMS replies, an on-read expired-hold sweep (no background scheduler needed for MVP), and security notes (PHI handling, no UUIDs in outbound SMS text, transactional confirm/cancel). Explicitly scoped out NLU (conversation-agent-skill's job) and provider-availability seeding/admin tooling.

## Outcome

- ✅ Impact: Third Claude Code Skill added, completing the three-skill split (SMS transport / conversation NLU / booking core) with a concrete concurrency-safe hold pattern for slot selection.
- 🧪 Tests: none (skill authoring only)
- 📁 Files: .claude/skills/appointment-booking-skill/SKILL.md (created)
- 🔁 Next prompts: Implement the three skills' actual FastAPI routes and SQLAlchemy models; write the Alembic migrations for all tables across the three skills (sms_conversations, sms_messages, patients, providers, appointment_slots, appointments); decide on provider-availability seeding/admin tooling, which all three skills currently assume exists elsewhere.
- 🧠 Reflection: This skill's design forked hard on one unstated assumption (external calendar vs. internal-only availability) that the earlier two skills didn't need to resolve — worth asking before writing rather than guessing, since an external-calendar design would have been almost entirely different (OAuth, webhook sync, conflict resolution) from an internal-slots design (DB transactions, hold expiry).

## Evaluation notes (flywheel)

- Failure modes observed: none.
- Graders run and results (PASS/FAIL): N/A (no automated grading configured)
- Prompt variant (if applicable): none
- Next experiment (smallest change to try): now that three skills each independently describe adjacent Postgres tables, consider whether a shared `history/prompts/general` or project-level "data model" note (memory or a checked-in doc) should consolidate the schema instead of letting each skill restate its own slice — reduces risk of drift across the three files.
