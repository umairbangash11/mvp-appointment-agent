---
id: 0006
title: Create frontend dashboard skill
stage: general
date: 2026-07-23
surface: agent
model: claude-sonnet-5
feature: none
branch: master
user: umairbangash11
command: none
labels: ["skills", "frontend", "nextjs", "stripe", "jwt", "hipaa"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
 - .claude/skills/frontend-dashboard-skill/SKILL.md
 - history/prompts/general/0006-create-frontend-dashboard-skill.general.prompt.md
tests:
 - none
---

## Prompt

Create a skill for frontend:

Name: frontend-dashboard-skill

Description:
Build a professional medical
dashboard frontend for US Doctor
Appointment Booking Agent.

This skill runs AFTER backend
is complete.

Tech Stack:
- Next.js 14 (App Router)
- Tailwind CSS
- Framer Motion (animations)
- Shadcn UI (components)
- Recharts (charts)
- Lucide React (icons)
- Axios (FastAPI connection)

Design Style:
- Medical blue theme
- Glassmorphism cards
- Dark sidebar left
- Smooth page transitions
- Animated charts
- Loading skeletons
- Hover effects
- Mobile responsive

Pages to Build:
1. Doctor Dashboard
   - Total appointments today
   - Revenue chart
   - No-show rate
   - Pending payments
   - Recent bookings list

2. Appointments Page
   - Calendar view
   - All bookings list
   - Filter by date/status
   - Cancel/reschedule option

3. Patient Records Page
   - Patient list
   - Patient history
   - HIPAA compliant display
   - No sensitive data in browser

4. Settings Page
   - Clinic info
   - Working hours
   - Staff management
   - Twilio/Groq config

5. Patient Booking Page
   (Public facing)
   - Select service
   - Pick date and time
   - Fill intake form
   - Pay copay online

HIPAA Rules:
- No patient diagnosis shown
- Encrypted API calls
- JWT authentication
- Auto logout after 15 min
- No sensitive data in localStorage

Connect to:
- FastAPI backend
- http://localhost:8000

Implementation only.
No spec or planning logic.
Run AFTER backend is complete.

## Response snapshot

This request introduced two genuinely new architectural dependencies absent from every prior skill: online payment collection ("pay copay online") and staff authentication/roles ("JWT authentication", "Staff management"). Surfaced both as unforeseen dependencies and asked before writing: which payment processor (user chose Stripe) and whether staff/auth should be a new `staff` table with roles vs. extending `appointment-booking-skill`'s `providers` table (user chose a new `staff`/`users` table with roles, optionally linked to `provider_id`). Created `.claude/skills/frontend-dashboard-skill/SKILL.md` covering the Next.js 14/Tailwind/shadcn/Framer Motion/Recharts/Axios stack, the 5 requested pages, and the stated design system and HIPAA client-side rules (JWT in memory + httpOnly refresh cookie, never localStorage; 15-min inactivity auto-logout backed by short server-side token expiry as the real enforcement; masked-only display of Twilio/Groq config, never raw secrets). Explicitly flagged, in a dedicated warning section, that every prior backend skill exposes only internal Python functions (no HTTP routes), and that staff auth and Stripe payment processing have no backend skill yet — this frontend skill documents the REST contract it needs rather than inventing that backend work itself, consistent with the user's own "runs AFTER backend is complete" framing.

## Outcome

- ✅ Impact: Sixth Claude Code Skill added — the first frontend-facing one — with a clear, explicit list of backend gaps (staff auth, payments, REST wrappers around existing internal functions) that must be closed before this skill can actually be implemented, rather than silently assuming they exist.
- 🧪 Tests: none (skill authoring only)
- 📁 Files: .claude/skills/frontend-dashboard-skill/SKILL.md (created)
- 🔁 Next prompts: Author the missing backend pieces this skill depends on (a staff-auth skill/implementation, a billing/Stripe skill/implementation, REST route wrappers around appointment-booking-skill and patient data) before starting frontend implementation; scaffold the Next.js app itself once those exist.
- 🧠 Reflection: A large feature request that silently assumes infrastructure (auth, payments) not yet built anywhere in the project is exactly the "unforeseen dependencies" case the operating instructions call out — surfacing it explicitly (both as clarifying questions up front and as a standing warning section in the skill file itself) keeps the skill honest about what it depends on instead of quietly hallucinating a backend that doesn't exist.

## Evaluation notes (flywheel)

- Failure modes observed: the invoking message didn't use the `/sp.skill` prefix this time (plain "Create a skill for frontend:") — handled the same way as prior `/sp.skill` requests since intent was unambiguous; command field recorded as "none" to reflect that accurately.
- Graders run and results (PASS/FAIL): N/A (no automated grading configured)
- Prompt variant (if applicable): none
- Next experiment (smallest change to try): if the user follows up asking to actually build the missing backend pieces, treat that as a natural point to suggest `/sp.adr` for the staff-auth + payment-processor decisions (both meet the significance test: long-term consequences, multiple viable alternatives, cross-cutting) rather than letting them pass undocumented.
