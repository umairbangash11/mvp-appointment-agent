---
id: "0018"
title: Phase 1 MVP Doctor Booking Spec
stage: spec
date: 2026-07-25
surface: agent
model: claude-sonnet-4-6
feature: 001-backend-frontend-mvp
branch: master
user: umairbangash11
command: /sp.specify
labels: ["spec","mvp","auth","sms","voice","email","appointments","frontend","hipaa"]
links:
  spec: specs/001-backend-frontend-mvp/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/001-backend-frontend-mvp/spec.md
  - specs/001-backend-frontend-mvp/checklists/requirements.md
  - history/prompts/001-backend-frontend-mvp/0018-phase1-mvp-doctor-booking-spec.spec.prompt.md
tests:
  - N/A
---

## Prompt

Phase 1 — Backend + Basic Frontend
together so I can test backend
through frontend immediately.

BACKEND FEATURES:

1. DOCTOR AUTH SYSTEM:
   - Signup with email verify
   - Login with JWT token
   - Forgot/reset password
   - Profile update
   - Auto logout 15 min

2. SMS BOOKING AGENT:
   - Twilio webhook
   - Groq AI conversation
   - Patient info collect
   - Insurance verification
   - Slot selection
   - SMS confirmation

3. VOICE CALL AGENT:
   - Twilio Voice webhook
   - AI picks up call
   - Natural conversation
   - Static FAQ answers
   - Booking confirmed
   - SMS after call

4. EMAIL CONFIRMATION:
   - SendGrid integration
   - Booking confirmation
   - Reminder emails

5. APPOINTMENTS API:
   - List all appointments
   - Dashboard stats
   - Cancel/update

FRONTEND FEATURES:
(Basic — just enough to test backend APIs)

1. Login Page
2. Signup Page
3. Forgot Password Page
4. Dashboard Page (JWT protected, auto-logout 15 min, stats)
5. Appointments Page (list, filter, cancel)

Tech Stack: FastAPI + PostgreSQL + Groq + Twilio + SendGrid + Next.js 14 + Tailwind + Shadcn + JWT + bcrypt

Goal: Backend + Frontend both working together so I can test everything end to end! No extra features. Keep it simple.

## Response snapshot

Created feature branch `001-backend-frontend-mvp` and wrote spec at `specs/001-backend-frontend-mvp/spec.md`.

Spec defines 5 user stories:
- P1: Doctor Registration & Authentication (signup, verify, login, auto-logout 15 min, forgot/reset password, profile)
- P2: Patient Books via SMS (Groq AI, HIPAA disclosure, collect fields, insurance stored as self-reported, SMS confirmation)
- P3: Patient Books via Voice (Groq AI, static FAQ, same fields, SMS confirmation after call)
- P4: Email Confirmation & Reminders (confirmation to patient + doctor within 2 min, 24hr reminder)
- P5: Doctor Dashboard & Appointments page (JWT protected, stats, filter, cancel)

33 Functional Requirements (FR-001–FR-033) defined across all 5 domains.
4 Key Entities: Doctor, Patient, Appointment, ConversationSession.
10 Measurable Success Criteria (SC-001–SC-010) — all technology-agnostic.
Quality checklist created at checklists/requirements.md — all 40 items pass.

## Outcome

- ✅ Impact: Feature spec complete; ready for /sp.plan
- 🧪 Tests: N/A (spec document)
- 📁 Files: specs/001-backend-frontend-mvp/spec.md, specs/001-backend-frontend-mvp/checklists/requirements.md
- 🔁 Next prompts: /sp.plan to generate the implementation architecture
- 🧠 Reflection: Slot availability assumed as default weekday schedule (Mon-Fri 9am-5pm, 30-min slots); no slot management UI in MVP scope. FAQ content assumed configured at deployment. All HIPAA constraints encoded in FR-011, FR-013, FR-017, FR-021 and SC-008/SC-009.

## Evaluation notes (flywheel)

- Failure modes observed: none
- Graders run and results (PASS/FAIL): quality checklist — all 40 items PASS
- Prompt variant (if applicable): initial spec from user description
- Next experiment: run /sp.plan to verify constitution check aligns with all 6 principles
