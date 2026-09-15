---
id: "0022"
title: Baileys WhatsApp Bot Integration
stage: green
date: 2026-08-16
surface: agent
model: claude-sonnet-4-6
feature: none
branch: dev
user: umairbangash11
command: direct
labels: ["baileys","whatsapp","nodejs","fastapi","integration"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - baileys-bot/package.json
  - baileys-bot/index.js
  - baileys-bot/.env
  - backend/routes/whatsapp.py
  - backend/config/settings.py
  - .env
tests:
  - manual end-to-end via QR scan
---

## Prompt

I am building a UAE/Pakistan WhatsApp Clinic Booking Agent. I need to integrate Baileys (WhatsApp Web library) with my existing FastAPI backend.

PROJECT LOCATION: E:\appointment_booking_agent\

CURRENT STRUCTURE:
- backend/ (FastAPI + Python)
- baileys-bot/ (Node.js - just created)
- frontend/ (Next.js 14)

TECH STACK:
- Backend: FastAPI + PostgreSQL
- AI: Groq LLaMA + Whisper STT
- TTS: ElevenLabs
- WhatsApp: Baileys (Node.js)

BAILEYS INSTALLED: @whiskeysockets/baileys, axios, pino, qrcode-terminal

WHAT I NEED:
1. Create baileys-bot/index.js
2. Update FastAPI backend with /whatsapp/baileys endpoint
3. Connect everything end-to-end

## Response snapshot

Created `baileys-bot/` directory with:
- `package.json` (ESM, node >=18)
- `index.js` — Baileys bot that handles text + voice messages, forwards to FastAPI, sends reply back
- `.env` with FASTAPI_URL and BAILEYS_SECRET

Added `POST /whatsapp/baileys` to `backend/routes/whatsapp.py`:
- Accepts JSON `{ phone, text, audio_base64? }`
- Verifies `X-Baileys-Secret` header against `settings.BAILEYS_SECRET`
- Calls existing `handle_whatsapp_message` (same state machine as Meta webhook)
- Transcribes audio via Groq Whisper if `audio_base64` provided
- Returns `{ reply_text, language }`

Added `BAILEYS_SECRET` to `backend/config/settings.py` and root `.env`.
Ran `npm install` — 93 packages installed, 0 vulnerabilities.

## Outcome

- ✅ Impact: WhatsApp messaging via Baileys (QR-based, no Meta Cloud API needed) fully wired to existing FastAPI booking agent
- 🧪 Tests: Requires manual QR scan to test; existing state machine tests still apply
- 📁 Files: 4 new files, 3 updated
- 🔁 Next prompts: Run FastAPI backend, run `node index.js` in baileys-bot/, scan QR, test booking flow with a real phone number
- 🧠 Reflection: Reused the existing `handle_whatsapp_message` core — zero logic duplication between Baileys and Meta webhook channels

## Evaluation notes (flywheel)

- Failure modes observed: none during implementation
- Graders run and results (PASS/FAIL): none automated
- Prompt variant (if applicable): none
- Next experiment (smallest change to try): add TTS reply for voice messages (call ElevenLabs, send audio back via Baileys)
