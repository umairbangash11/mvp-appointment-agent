---
id: 0007
title: Create doctor auth and admin skill
stage: general
date: 2026-07-23
surface: agent
model: claude-sonnet-5
feature: none
branch: master
user: umairbangash11
command: none
labels: ["skills", "auth", "jwt", "bcrypt", "sendgrid", "fastapi", "reconciliation"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
 - .claude/skills/doctor-auth-admin-skill/SKILL.md
 - .claude/skills/env-config-skill/SKILL.md
 - .claude/skills/frontend-dashboard-skill/SKILL.md
 - history/prompts/general/0007-create-doctor-auth-admin-skill.general.prompt.md
tests:
 - none
---

## Prompt

Create a skill for doctor 
authentication and admin:

Name: doctor-auth-admin-skill

Description:
Build complete authentication
and admin system for US Doctor
in appointment booking agent.

Tech Stack:
- Python + FastAPI
- PostgreSQL
- JWT tokens (python-jose)
- bcrypt (password hashing)
- SendGrid (email service)
- Implementation only

Features to Build:

1. SIGNUP:
   - Doctor registration
   - Fields: name, email,
     password, clinic name,
     phone, state
   - Email verification
   - Password encrypted bcrypt

2. EMAIL VERIFICATION:
   - Send verification email
   - Unique token generated
   - Link expires 24 hours
   - Account active after verify

3. LOGIN:
   - Email + password login
   - JWT token generated
   - Token expires 24 hours
   - Return doctor profile

4. FORGOT PASSWORD:
   - Doctor enters email
   - Reset link sent via email
   - Link expires 1 hour

5. RESET PASSWORD:
   - New password set
   - Old token invalidated
   - bcrypt encrypted

6. LOGOUT:
   - JWT token invalidated
   - Session cleared

7. PROFILE UPDATE:
   - Update name
   - Update clinic info
   - Update phone
   - Change password option

8. DOCTOR DASHBOARD DATA:
   - Today appointments count
   - Total patients count
   - Monthly revenue
   - Pending payments
   - Recent bookings list

Database Tables:
- doctors
  (id, name, email, password,
   clinic_name, phone, state,
   is_verified, is_active,
   created_at)

- password_resets
  (id, doctor_id, token,
   expires_at, is_used)

Security Rules:
- HIPAA compliant
- Auto logout 15 minutes
- Password min 8 characters
- JWT secret in .env
- No plain passwords stored
- Rate limiting on login

API Endpoints:
POST /auth/signup
POST /auth/verify-email
POST /auth/login
POST /auth/forgot-password
POST /auth/reset-password
POST /auth/logout
GET  /auth/profile
PUT  /auth/profile/update

Implementation only.
No spec or planning logic.

## Response snapshot

This request supplied a concrete `doctors` schema (no role field, doctor-only accounts) that conflicts with [[frontend-dashboard-skill]]'s earlier "staff/users table with roles" decision from the prior turn. Treated this newer, more detailed spec as authoritative rather than asking again, and reconciled by editing frontend-dashboard-skill in place. Also identified and filled three real gaps in the given spec without asking: (1) no table was given for email-verification tokens despite "unique token generated, 24h expiry" being required — added an `email_verifications` table mirroring `password_resets`; (2) JWT is stateless by default and can't be "invalidated" on logout as literally required — added a `revoked_tokens` table keyed on the token's `jti` claim, checked on every protected request; (3) feature #8 "Doctor Dashboard Data" has no corresponding endpoint in the given API list — added `/dashboard/stats`, `/dashboard/revenue`, `/dashboard/recent-bookings`, matching exactly what frontend-dashboard-skill already assumed. Flagged that monthly revenue/pending payments have no data source anywhere in the project yet (same payments gap frontend-dashboard-skill already surfaced) and that dashboard queries need a new `provider_id` FK linking `doctors` to appointment-booking-skill's `providers` table. Reconciled the 24-hour JWT expiry against frontend-dashboard-skill's earlier assumption of a ~15-minute access token: documented both as distinct layers, and changed the frontend's auto-logout behavior to actually call `POST /auth/logout` (revoking the token server-side) rather than merely discarding it client-side, closing what would otherwise be a real gap between a 15-minute UI timeout and a 24-hour server-valid token. Updated env-config-skill with the five new required variables this skill introduces (`JWT_SECRET`, `JWT_EXPIRY_HOURS`, `SENDGRID_API_KEY`, `SENDGRID_FROM_EMAIL`, `FRONTEND_BASE_URL`).

## Outcome

- ✅ Impact: Seventh Claude Code Skill added, resolving the staff-auth dependency frontend-dashboard-skill had flagged as missing — with the three files (doctor-auth-admin-skill, frontend-dashboard-skill, env-config-skill) now internally consistent rather than silently disagreeing on the JWT lifetime, the account model (doctor-only vs. role-based staff), and which env vars exist.
- 🧪 Tests: none (skill authoring only)
- 📁 Files: .claude/skills/doctor-auth-admin-skill/SKILL.md (created), .claude/skills/env-config-skill/SKILL.md (edited — new required vars), .claude/skills/frontend-dashboard-skill/SKILL.md (edited — dependency section, sidebar/settings copy, API contract table, JWT/auto-logout section, testing section)
- 🔁 Next prompts: Add a `payments`/billing skill (Stripe payment intents + a revenue-bearing schema) to unblock the dashboard revenue fields both this skill and frontend-dashboard-skill now depend on; add a `no_show` value to appointment-booking-skill's `appointments.status` enum if the no-show-rate stat needs to distinguish it from a plain cancellation; implement the actual `app/config.py`, migrations, and auth routes.
- 🧠 Reflection: When a later, more concrete spec conflicts with an earlier abstract decision made for a dependent skill, treating the concrete spec as authoritative and propagating the fix backward (editing the earlier file) kept the skill set internally consistent without another round of clarifying questions — appropriate here since the user had just supplied exact field names and endpoint lists, leaving little genuine ambiguity to ask about.

## Evaluation notes (flywheel)

- Failure modes observed: the given spec had two internal gaps (missing verification-token table, missing endpoint for feature #8) that would have caused implementation to stall or silently improvise if not caught and documented at the skill-authoring stage.
- Graders run and results (PASS/FAIL): N/A (no automated grading configured)
- Prompt variant (if applicable): none
- Next experiment (smallest change to try): now that a real cross-skill contradiction has occurred and been resolved (JWT lifetime, staff vs. doctor model), consider whether a lightweight "decisions log" memory (not a per-skill file) would help catch these faster in future sessions, before writing conflicting content in the first place.
