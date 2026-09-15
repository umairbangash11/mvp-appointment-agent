---
id: "0017"
title: Create Doctor Booking Agent Constitution
stage: constitution
date: 2026-07-25
surface: agent
model: claude-sonnet-4-6
feature: none
branch: master
user: umairbangash11
command: /sp.constitution
labels: ["constitution","hipaa","mvp","fastapi","twilio","groq","sendgrid","jwt","nextjs"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - .specify/memory/constitution.md
tests:
  - N/A
---

## Prompt

Create constitution for
US Doctor Appointment
Booking Agent MVP.

Project Name:
us-doctor-appointment-booking-agent

Channels:
- SMS Booking (Twilio)
- Voice Call (Twilio)
- Email Confirmation (SendGrid)

Tech Stack:
- Python + FastAPI
- PostgreSQL
- Groq API (llama-3.3-70b)
- Twilio SMS + Voice
- SendGrid Email
- Next.js 14 Frontend
- Tailwind CSS
- Shadcn UI
- JWT Authentication (python-jose)
- bcrypt (password hashing)

Folder Structure:
appointment_booking_agent/
├── backend/
│   ├── main.py
│   ├── config/
│   │   └── settings.py
│   ├── models/
│   │   ├── doctor.py
│   │   ├── patient.py
│   │   └── appointment.py
│   ├── routes/
│   │   ├── auth.py
│   │   ├── appointments.py
│   │   ├── sms.py
│   │   └── voice.py
│   ├── services/
│   │   ├── groq_service.py
│   │   ├── twilio_service.py
│   │   └── sendgrid_service.py
│   ├── agents/
│   │   ├── sms_agent.py
│   │   └── voice_agent.py
│   └── requirements.txt
│
├── frontend/
│   ├── app/
│   │   ├── login/
│   │   │   └── page.tsx
│   │   ├── signup/
│   │   │   └── page.tsx
│   │   ├── forgot-password/
│   │   │   └── page.tsx
│   │   ├── dashboard/
│   │   │   └── page.tsx
│   │   └── appointments/
│   │       └── page.tsx
│   ├── components/
│   └── package.json
│
├── .env.example
├── .gitignore
├── CLAUDE.md
└── README.md

PHASE 1 — BACKEND:
folder: /backend

Features:
1. FastAPI project setup
2. PostgreSQL connection
3. Database models: Doctor, Patient, Appointment

4. Doctor Auth System:
   - POST /auth/signup
   - POST /auth/verify-email
   - POST /auth/login
   - POST /auth/forgot-password
   - POST /auth/reset-password
   - POST /auth/logout
   - GET  /auth/profile
   - PUT  /auth/profile/update

5. JWT Dashboard Protection:
   - All dashboard routes protected by JWT
   - Auto logout after 15 minutes inactivity
   - Role: doctor only
   - Token refresh system

6. SMS Booking Agent:
   - Twilio webhook receiver
   - Groq AI conversation
   - Patient info collection
   - Insurance verification
   - Slot selection
   - Booking confirmation SMS

7. Voice Call Agent:
   - Twilio Voice webhook
   - AI voice answers call
   - Natural conversation
   - Static FAQ answers
   - Booking via voice
   - SMS confirmation after call

8. Email Confirmation:
   - SendGrid integration
   - Booking confirmation email
   - Appointment reminder email
   - Doctor notification email

9. Appointments API:
   - GET /appointments
   - GET /appointments/{id}
   - PUT /appointments/{id}
   - GET /dashboard/stats

Exit Criteria Phase 1:
- Doctor can signup/login
- JWT protects all routes
- SMS booking works
- Voice call booking works
- Email confirmation sent
- Insurance verified
- All APIs tested

PHASE 2 — FRONTEND:
folder: /frontend

Features:
1. Login Page
2. Signup Page
3. Forgot Password Page
4. Doctor Dashboard (JWT protected, auto-logout 15 min)
5. Appointments Page

Design: Medical blue theme, Shadcn UI, mobile responsive

Exit Criteria Phase 2:
- Doctor can login via browser
- Dashboard shows real data
- JWT authentication working
- Appointments visible

Global Rules:
1. One phase at a time
2. No skipping phases
3. HIPAA compliant always
4. Every AI says I am AI
5. JWT for all auth routes
6. Passwords always bcrypt
7. Auto logout 15 minutes
8. No plain passwords stored
9. No medical advice given
10. Test before next phase
11. Constitution never changes

HIPAA Rules:
- AI disclosure on every call
- Consent before data collect
- No PHI in SMS content
- No diagnosis in messages
- Encrypted data storage
- US servers only

Do NOT recreate this constitution again. This is ONE TIME only.

## Response snapshot

Created `.specify/memory/constitution.md` at version 1.0.0, ratified 2026-07-25.

The constitution defines 6 core principles:
I. HIPAA Compliance & Patient Privacy (NON-NEGOTIABLE)
II. AI Transparency & Ethical Boundaries
III. Phase-Gated Delivery (NON-NEGOTIABLE)
IV. Secure Authentication & Session Management
V. Test-Before-Advance Gate
VI. Data Minimization & Channel Scope

Two additional sections define HIPAA compliance rules and the full development workflow with Phase 1
and Phase 2 exit criteria checklists. The Governance section documents the amendment procedure and
version policy. All 4 templates verified compatible.

## Outcome

- ✅ Impact: Project constitution created at v1.0.0; all development work must now reference it
- 🧪 Tests: N/A (constitution document, not code)
- 📁 Files: .specify/memory/constitution.md (created/overwritten), history/prompts/constitution/0017-create-doctor-booking-agent-constitution.constitution.prompt.md (created)
- 🔁 Next prompts: /sp.specify for a feature spec, /sp.plan for architecture planning, /sp.tasks for task generation
- 🧠 Reflection: Constitution covers all user-supplied global rules and HIPAA requirements; Phase-Gated Delivery and Test-Before-Advance principles operationalize the "One phase at a time" and "Test before next phase" rules

## Evaluation notes (flywheel)

- Failure modes observed: none
- Graders run and results (PASS/FAIL): N/A
- Prompt variant (if applicable): initial constitution creation
- Next experiment: run /sp.specify to create the first feature spec and verify constitution gates apply correctly
