---
id: 0023
title: Dr. Wasim Clinic Agent Redesign
stage: general
date: 2026-08-24
surface: agent
model: claude-sonnet-4-6
feature: none
branch: dev
user: umairbangash11
command: "Redesign the WhatsApp booking agent with Dr. Wasim's clinic schedule and 6-step flow"
labels: ["whatsapp-agent","state-machine","groq","bilingual","two-locations"]
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

Redesign the WhatsApp booking agent with this exact flow and schedule.

DOCTOR INFORMATION:
Doctor: Dr. Wasim
Monday/Tuesday/Wednesday: F10 Clinic
Thursday/Friday/Saturday: Bahria Phase 4 Clinic
Sunday: OFF (no appointments)
Timing: 9:00 AM to 5:00 PM
Appointment duration: 30 minutes
Clinic Phone: +92 300 0000000

CONVERSATION FLOW:
STEP 1 — Patient sends any message → warm greeting, ask for full name
STEP 2 — Patient gives name → validate (min 2 words, no blacklisted words), ask reason for visit
STEP 3 — Patient gives reason → save reason, show full weekly schedule AND available slots (numbered)
STEP 4 — Patient replies with number → save selected slot, show confirmation with location
STEP 5 — Patient says YES → book and confirm (fixed format with location)
STEP 6 — Patient says NO → ask which day works better, re-filter and show slots

SLOT GENERATION RULES:
Mon/Tue/Wed → F10 Clinic
Thu/Fri/Sat → Bahria Phase 4
Sunday → no slots / closed message
Hours: 9:00 AM to 5:00 PM, every 30 minutes, show 5 slots at a time
Include location name in each slot

GLOBAL RULES:
START → always reset, STOP → always opt out, No insurance questions, No consent questions,
Always validate name (minimum 2 words), Always show schedule after reason,
Always show location with slot, Support Arabic and English, Use Groq AI, Fallback strings if Groq fails,
Sunday shows closed message, Off-topic → redirect politely

## Response snapshot

Complete rewrite of `backend/agents/whatsapp_agent.py`:
- F10_DAYS = {0,1,2}, BAHRIA_DAYS = {3,4,5}, Sunday closed
- Slots generated as dicts: {display, location, label, iso}
- Flow: greeting → collect_name → collect_reason → select_slot → confirm → done + change_slot branch
- `_is_valid_name()`: min 2 words, any blacklisted word = reject
- `_build_schedule_display(lang)`: static bilingual schedule text
- `_build_slot_list(slots, lang)`: numbered slot display (fixed, not Groq)
- `_format_confirmation(data, lang)`: fixed 5-field block
- `_format_booking_confirmed(data, lang)`: fixed 5-field block
- Groq used for conversational steps; fixed strings for all structured data
- Arabic detected via Unicode range; language stored in session
- FAQ answers (hours/location/phone) are hardcoded — never hallucinated
- `change_slot` step filters slots by day preference, Sunday = closed message
- STOP / START / help handled globally before step dispatch

## Outcome

- ✅ Impact: Agent now correctly handles two clinic locations, validates 2-word names, shows location in every slot, and produces fixed-format confirmations immune to Groq hallucination.
- 🧪 Tests: Manual test via /whatsapp/simulate endpoint
- 📁 Files: backend/agents/whatsapp_agent.py (full rewrite)
- 🔁 Next prompts: Delete Baileys endpoint and directories (pending since earlier session), test complete flow end-to-end
- 🧠 Reflection: Separating structured data (slot list, confirmation, booking confirmed) from Groq-generated prose prevents hallucinated dates/locations while keeping the conversation warm.

## Evaluation notes (flywheel)

- Failure modes observed: None yet
- Graders run and results (PASS/FAIL): none
- Prompt variant (if applicable): none
- Next experiment: Test Arabic conversation path end-to-end; verify slot ISO parsing handles year boundary correctly
