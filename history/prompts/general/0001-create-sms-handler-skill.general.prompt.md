---
id: 0001
title: Create SMS handler skill
stage: general
date: 2026-07-23
surface: agent
model: claude-sonnet-5
feature: none
branch: master
user: umairbangash11
command: /sp.skill
labels: ["skills", "twilio", "sms", "fastapi", "postgresql"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
 - .claude/skills/sms-handler-skill/SKILL.md
 - history/prompts/general/0001-create-sms-handler-skill.general.prompt.md
tests:
 - none
---

## Prompt

/sp.skill

Name: sms-handler-skill
Description: Handles incoming and
outgoing SMS messages via Twilio.
Receives patient messages, sends
agent replies, manages conversation
state. No spec or planning logic.
Implementation only.

---

create a skills for this mvp if the command is not in specify you can take this me as a prompt and create skills related to project./sp.skill

Name: sms-handler-skill
Description: Handles incoming and
outgoing SMS messages via Twilio.
Receives patient messages, sends
agent replies, manages conversation
state. No spec or planning logic.
Implementation only.

---

i am using python, fastapi.

---

i will be using postresql

## Response snapshot

`/sp.skill` is not a registered Specify command (only sp.specify/plan/tasks/clarify/checklist/analyze/adr/implement/reverse-engineer/taskstoissues/git.commit_pr/phr exist). Treated the user's message as a request to create a Claude Code Skill instead. Clarified stack (Python + FastAPI, PostgreSQL for state) before writing content, then created `.claude/skills/sms-handler-skill/SKILL.md`: an implementation-only skill covering the Twilio SMS transport layer — inbound webhook contract (signature validation, dedupe on twilio_sid), outbound `send_sms` helper, Postgres schema for `sms_conversations`/`sms_messages`, required env vars, error handling, and testing guidance. Explicitly scoped out booking/NLU logic and spec/plan/tasks generation, per the user's "implementation only" note.

## Outcome

- ✅ Impact: New Claude Code Skill created at `.claude/skills/sms-handler-skill/SKILL.md`, giving future sessions concrete Twilio/FastAPI/Postgres implementation guidance for the SMS transport layer.
- 🧪 Tests: none (skill authoring only, no code written yet)
- 📁 Files: .claude/skills/sms-handler-skill/SKILL.md (created)
- 🔁 Next prompts: Implement the FastAPI routes and SQLAlchemy models described in the skill; wire `send_sms` into the appointment agent's reply path; add Alembic migration for `sms_conversations`/`sms_messages`.
- 🧠 Reflection: User intent was a Claude Code Skill (packaged agent instructions), not a Spec-Kit artifact — confirming stack details first (Python/FastAPI/Postgres) before writing kept the skill concrete instead of generic.

## Evaluation notes (flywheel)

- Failure modes observed: `/sp.skill` is not a real command and no `create-phr.sh` exists in this repo (only PowerShell scripts) — fell back to the agent-native PHR flow per CLAUDE.md step 5.
- Graders run and results (PASS/FAIL): N/A (no automated grading configured)
- Prompt variant (if applicable): none
- Next experiment (smallest change to try): if more skills are requested, ask up front whether they should live under `.claude/skills/` (Claude Code Skill) vs. `specs/` (Spec-Kit feature) rather than inferring it.
