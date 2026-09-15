---
id: "0026"
title: Add check_returning_patient function
stage: green
date: 2026-09-09
surface: agent
model: claude-sonnet-4-6
feature: none
branch: dev
user: umairbangash11
command: inline edit
labels: ["whatsapp-agent","returning-patient","db-query"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - backend/agents/whatsapp_agent.py
tests:
  - none
---

## Prompt

In agents/whatsapp_agent.py

Find this line:
def _branch_address_block(branch: str):

Before that line add:

async def check_returning_patient(
    phone_hash: str,
    db: AsyncSession
):
    result = await db.execute(
        select(Patient).where(
            Patient.phone_hash == phone_hash
        )
    )
    return result.scalar_one_or_none()

## Response snapshot

Inserted `check_returning_patient` async function at line 260 in `backend/agents/whatsapp_agent.py`, immediately before `_branch_address_block`. The function queries the `Patient` table by `phone_hash` using SQLAlchemy async session and returns the patient record or `None`.

## Outcome

- ✅ Impact: Returning-patient lookup helper available for WhatsApp conversation flow
- 🧪 Tests: none added
- 📁 Files: backend/agents/whatsapp_agent.py
- 🔁 Next prompts: wire call-site in conversation state machine; add unit test
- 🧠 Reflection: Minimal targeted insertion; no unrelated changes

## Evaluation notes (flywheel)

- Failure modes observed: none
- Graders run and results (PASS/FAIL): none
- Prompt variant (if applicable): none
- Next experiment (smallest change to try): add call-site in _handle_greeting or equivalent state handler
