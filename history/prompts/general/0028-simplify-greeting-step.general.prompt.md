---
id: "0028"
title: Simplify Greeting Step
stage: general
date: 2026-09-15
surface: agent
model: claude-sonnet-4-6
feature: none
branch: dev
user: umairbangash11
command: inline edit request
labels: ["whatsapp-agent","greeting","refactor","simplify"]
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

Find: if step == "greeting":

Replace ENTIRE greeting step
with only these 3 lines:

if step == "greeting":
    data["_next_step"] = "collect_name"
    return _fb("greeting", lang)

Delete everything else
inside greeting step.
Keep it simple.

## Response snapshot

Located the greeting step handler (which had been previously deleted, leaving a blank). Inserted the 3-line greeting step block between the FAQ handler and the collect_name step in `_process_step`.

## Outcome

- ✅ Impact: Greeting step now simply sets next step to collect_name and returns the greeting fallback string — no branching logic
- 🧪 Tests: none run
- 📁 Files: backend/agents/whatsapp_agent.py
- 🔁 Next prompts: test the WhatsApp flow end-to-end
- 🧠 Reflection: Clean minimal handler; previous deletion caused greeting step to fall through to generic_error
