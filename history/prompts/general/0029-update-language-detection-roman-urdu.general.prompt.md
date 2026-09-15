---
id: 0029
title: Update Language Detection Roman Urdu
stage: general
date: 2026-09-15
surface: agent
model: claude-sonnet-4-6
feature: none
branch: dev
user: umairbangash11
command: inline edit
labels: ["language-detection","roman-urdu","groq","whatsapp-agent"]
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

Update language detection
and Groq system prompt.

LANGUAGE RULES:

1. If patient messages in English:
   Agent replies in English only.
   Example:
   Patient: "Hi I need appointment"
   Agent: "Hi! How are you? 😊
           Welcome to Dr. Wasim Clinic.
           May I know your full name?"

2. If patient messages in Roman Urdu:
   Agent replies in Roman Urdu only.
   Example:
   Patient: "Hi mujhe appointment chahiye"
   Agent: "Assalam o Alaikum! 😊
           Dr. Wasim Clinic mein
           khush aamdeed!
           Apna poora naam batayein?"

3. NEVER use Arabic script.
4. NEVER use Urdu script.
5. Only Roman Urdu or English.
6. Match patient language exactly.

Update detect_language() function:
If Arabic script detected:
Treat as Roman Urdu.
Reply in Roman Urdu.

Update Groq system prompt:
Add these language rules clearly.
Agent must follow strictly.

## Response snapshot

Updated `backend/agents/whatsapp_agent.py` with the following changes:

1. **Added `_ROMAN_URDU_RE`** — regex matching common Roman Urdu words (mujhe, chahiye, hoon, theek, etc.) to detect when patient is writing in Roman Urdu using Latin script.

2. **Updated `detect_language()`** — now returns `"ru"` (Roman Urdu) if Arabic script OR Roman Urdu keywords detected; returns `"en"` otherwise. Arabic script input is treated as Roman Urdu intent — no Arabic replies ever generated.

3. **Replaced `"ar"` language code with `"ru"`** throughout — `FALLBACK`, `YES_WORDS`, `NO_WORDS`, `STOP_WORDS`, all logic branches.

4. **All Roman Urdu fallback strings updated** — greeting, name_invalid, ask_reason, no_slots, slot_invalid, sunday_closed, change_slot, opted_out, no_doctor, help, off_topic, generic_error now have proper Roman Urdu text.

5. **Updated `_build_system_prompt()`** — explicit STRICT LANGUAGE RULE block for both `"en"` and `"ru"`, with concrete examples, prohibition on Arabic/Urdu script, and instruction to never mix languages.

6. **Updated `handle_whatsapp_message()`** — language detection only runs on messages longer than 3 chars; short replies like "1", "2", "yes" inherit the session language to avoid false switches.

7. **Updated `_faq_answer()`**, `_build_schedule_display()`, `_build_slot_list()`, `_format_confirmation()** — Roman Urdu versions for all fixed-format output.

## Outcome

- ✅ Impact: Agent now strictly mirrors patient language — English in, English out; Roman Urdu (or Arabic script) in, Roman Urdu out. Arabic script is never generated.
- 🧪 Tests: No automated tests run; manual smoke test via WhatsApp simulator recommended.
- 📁 Files: backend/agents/whatsapp_agent.py
- 🔁 Next prompts: Test both language paths in /whatsapp-test simulator; optionally add Roman Urdu test cases.
- 🧠 Reflection: Language code renamed from "ar" to "ru" to accurately reflect Roman Urdu (not Arabic). Arabic script input redirected to Roman Urdu reply path cleanly.

## Evaluation notes (flywheel)

- Failure modes observed: none
- Graders run and results (PASS/FAIL): none
- Prompt variant (if applicable): none
- Next experiment (smallest change to try): Test with mixed-language inputs to verify session language inheritance on short replies.
