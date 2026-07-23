---
id: 0002
title: Create conversation agent skill
stage: general
date: 2026-07-23
surface: agent
model: claude-sonnet-5
feature: none
branch: master
user: umairbangash11
command: /sp.skill
labels: ["skills", "claude-api", "conversation", "hipaa", "sms", "fastapi"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
 - .claude/skills/conversation-agent-skill/SKILL.md
 - history/prompts/general/0002-create-conversation-agent-skill.general.prompt.md
tests:
 - none
---

## Prompt

/sp.skill

Name: conversation-agent-skill
Description: Manages patient
conversation flow. Greets patient,
identifies new vs returning,
collects Name and Phone Number,
confirms appointment. Uses Claude
AI for natural language. HIPAA
compliant — always identifies
as AI. Implementation only.

## Response snapshot

Loaded the `claude-api` skill (mandatory whenever a prompt names Claude/Anthropic and involves LLM integration code) before writing this skill, since it explicitly calls for "Uses Claude AI for natural language." Created `.claude/skills/conversation-agent-skill/SKILL.md`, an implementation-only Claude Code Skill that layers on top of `sms-handler-skill`: a 7-stage conversation state machine (greeting → identify → collect_name → collect_phone → booking_intent → confirm_appointment → done), Claude API integration using `claude-opus-4-8` with structured outputs (`output_config.format`) for deterministic per-turn decisions instead of free-text parsing, a system-prompt contract (always disclose AI identity, never give medical advice, stay in scheduling scope), and HIPAA-aware guardrails (mandatory AI disclosure before collecting PHI, minimum-necessary PHI storage, STOP/opt-out handling, no clinical decision-making). Linked back to `sms-handler-skill` via `[[sms-handler-skill]]` and scoped out actual booking/availability logic as a separate component's responsibility.

## Outcome

- ✅ Impact: Second Claude Code Skill added, giving future sessions concrete guidance for the conversational/NLU layer — state machine stages, structured-output contract with Claude, and HIPAA disclosure requirements — without touching booking/availability logic (out of scope, flagged for a separate component).
- 🧪 Tests: none (skill authoring only)
- 📁 Files: .claude/skills/conversation-agent-skill/SKILL.md (created)
- 🔁 Next prompts: Implement the FastAPI conversation handler and Anthropic structured-output call described here; define the `patients` table migration; decide whether booking/availability logic gets its own skill or lives in application code directly.
- 🧠 Reflection: The user's description explicitly named Claude/Anthropic usage, which is a hard trigger to load the claude-api skill first — doing so caught the Opus-4.8-by-default model policy, the structured-outputs pattern (avoids the assistant-prefill 400 on Opus 4.8), and the omit-thinking-for-classification-tasks guidance, all of which shaped concrete, non-generic content.

## Evaluation notes (flywheel)

- Failure modes observed: none — stack was already established from the prior sms-handler-skill exchange (Python/FastAPI/Postgres), so no further clarification was needed this turn.
- Graders run and results (PASS/FAIL): N/A (no automated grading configured)
- Prompt variant (if applicable): none
- Next experiment (smallest change to try): if a third skill is requested, check whether it should reference a shared "data model" doc instead of each skill independently describing overlapping Postgres tables (`sms_conversations`, `patients`) — early sign of duplication worth consolidating.
