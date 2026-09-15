---
id: 0025
title: Add collect_branch Step
stage: general
date: 2026-08-25
surface: agent
model: claude-sonnet-4-6
feature: none
branch: dev
user: umairbangash11
command: "Add collect_branch step between collect_reason and slot selection"
labels: ["whatsapp-agent","state-machine","branch-selection"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - backend/agents/whatsapp_agent.py
tests:
  - manual via /whatsapp/simulate
---

## Prompt

In agents/whatsapp_agent.py make these changes:

CHANGE 1: Move collect_reason BEFORE collect_branch. New order: collect_reason → collect_branch → collect_datetime.
CHANGE 2: After collect_reason, set next step to collect_branch.
CHANGE 3: Add collect_branch step (1=F10 Islamabad, 2=Bahria Rawalpindi, else=repeat).
CHANGE 4: _get_available_slots() takes branch param; F10=Mon/Tue/Wed 9-5, Bahria=Thu/Fri/Sat 10-6.
CHANGE 5: Save branch in collected_data throughout conversation.

## Response snapshot

Changes made to `backend/agents/whatsapp_agent.py`:

1. Added `_BRANCH_QUESTION` constant with the exact bilingual branch selection message.
2. `collect_reason` now saves reason, sets `_next_step = "collect_branch"`, returns `_BRANCH_QUESTION`.
3. New `collect_branch` step: choice "1" → branch = "F10 Islamabad", choice "2" → branch = "Bahria Rawalpindi", else → re-show question. On valid choice, Groq asks for day/time preference, next = "collect_datetime".
4. New `collect_datetime` step: calls `_get_available_slots(db, branch=data["branch"])`, filters by patient's day preference via `_filter_slots_by_day()`, shows numbered slot list, next = "select_slot".
5. `_get_available_slots(db, branch=None)` now accepts branch param:
   - "F10 Islamabad" → F10_DAYS (Mon/Tue/Wed), 9:00 AM–5:00 PM
   - "Bahria Rawalpindi" → BAHRIA_DAYS (Thu/Fri/Sat), 10:00 AM–6:00 PM
   - None → all days (backwards compat)
6. `change_slot` updated to pass `branch=data.get("branch")` when re-fetching slots.

New flow: greeting → collect_name → collect_reason → collect_branch → collect_datetime → select_slot → confirm → done

## Outcome

- ✅ Impact: Patients now explicitly choose their clinic branch before seeing slots; slots are filtered to match branch hours and days.
- 🧪 Tests: Manual test via /whatsapp/simulate
- 📁 Files: backend/agents/whatsapp_agent.py
- 🔁 Next prompts: End-to-end test of full booking flow with both branches
- 🧠 Reflection: `collect_datetime` acts as a day-preference filter between branch selection and numbered slot display, keeping `select_slot` unchanged.

## Evaluation notes (flywheel)

- Failure modes observed: none
- Graders run and results (PASS/FAIL): none
- Prompt variant (if applicable): none
- Next experiment: Test Sunday message when patient types "Sunday" in collect_datetime step
