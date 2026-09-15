---
id: 0016
title: Simplify MVP skills and scope
stage: general
date: 2026-07-24
surface: agent
model: claude-sonnet-5
feature: none
branch: master
user: umairbangash11
command: none
labels: ["skills", "simplification", "scope-reduction", "claude.md", "restructure"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
 - .claude/skills/sms-handler-skill/SKILL.md
 - .claude/skills/voice-call-skill/SKILL.md (renamed from voice-call-rag-skill/SKILL.md)
 - .claude/skills/appointment-booking-skill/SKILL.md
 - .claude/skills/doctor-auth-admin-skill/SKILL.md
 - .claude/skills/frontend-dashboard-skill/SKILL.md
 - .claude/skills/appointment-confirmation-skill/SKILL.md (deleted)
 - .claude/skills/conversation-agent-skill/SKILL.md (deleted)
 - .claude/skills/env-config-skill/SKILL.md (deleted)
 - .claude/skills/hipaa-compliance-skill/SKILL.md (deleted)
 - CLAUDE.md
 - history/prompts/general/0016-simplify-mvp-skills-and-scope.general.prompt.md
tests:
 - none
---

## Prompt

(Turn 1) I want to simplify this MVP.

Keep ONLY these 3 channels:
1. SMS Booking
2. Voice Call Booking
3. Email Confirmation

Keep ONLY these features:
1. Patient books via SMS
2. Patient books via Voice Call
3. Email confirmation sent
4. Doctor login/signup
5. Doctor dashboard
6. Appointments list
7. Insurance verification
8. Basic reminders

DELETE these from project:
1. RAG system (pgvector)
2. Stripe payments
3. SendGrid complex emails
   (keep only basic confirmation)
4. Brave Search MCP
5. Daily reports cron
6. WhatsApp integration
7. Facebook integration
8. Instagram integration

Keep ONLY these Skills:
1. sms-handler-skill
2. voice-call-skill
3. doctor-auth-admin-skill
4. frontend-dashboard-skill

Keep ONLY these MCPs:
1. PostgreSQL MCP
2. GitHub MCP
3. Filesystem MCP

Simplify to 2 Phases:

PHASE 1 — BACKEND:
- FastAPI setup
- PostgreSQL basic
- Doctor auth
  (login + signup +
   forgot password)
- SMS agent with Groq
- Voice call agent
- Email confirmation
  (SendGrid basic only)
- Insurance check
- Appointments API

PHASE 2 — FRONTEND:
- Doctor login page
- Simple dashboard
- Appointments list
- Basic stats

Update CLAUDE.md with
new simplified structure.

Remove all unused skills.
Remove all unused MCPs.
Keep project clean and simple.

(Turn 2 — clarifying answers, via AskUserQuestion)
- Booking logic conflict → "Keep as 5th skill" (appointment-booking-skill stays, shared by SMS + voice)
- HIPAA compliance → "Fold into sms + voice skills (Recommended)"
- Voice call RAG removal → "Static FAQ answers (Recommended)"
- Insurance verification / reminders → "Fold into existing skills (Recommended)"

(Turn 3) List all MCP servers that are currently connected to this project.

(Turn 4) Show me current project status:
1. List all skills that exist now
2. List all phases defined
3. Show current CLAUDE.md structure
4. What has been deleted?
5. What is remaining?

Give me a clean summary.

(Turn 5 — this execution turn) Yes, proceed with execution.

Do these changes now:

DELETE these skills:
1. appointment-confirmation-skill
2. conversation-agent-skill
3. env-config-skill
4. hipaa-compliance-skill
5. voice-call-rag-skill

KEEP and UPDATE these skills:
1. sms-handler-skill
   + Add HIPAA rules
   + Add insurance check
   + Add basic reminders

2. voice-call-skill
   (rename from voice-call-rag-skill)
   + Remove RAG/pgvector
   + Add static FAQ
   + Add HIPAA rules
   + Add insurance check

3. appointment-booking-skill
   + Keep as shared booking logic

4. doctor-auth-admin-skill
   + Keep as is

5. frontend-dashboard-skill
   + Keep as is

UPDATE CLAUDE.md:
Add this structure:

Project: US Doctor Booking Agent MVP

Channels:
- SMS Booking
- Voice Call Booking
- Email Confirmation

Phases:
PHASE 1 - BACKEND:
- FastAPI + PostgreSQL
- Doctor auth system
- SMS agent
- Voice call agent
- Email confirmation
- Insurance check
- Appointments API

PHASE 2 - FRONTEND:
- Doctor login page
- Simple dashboard
- Appointments list

Now execute all changes!

## Response snapshot

Executed the full restructure. Deleted `appointment-confirmation-skill`, `conversation-agent-skill`, `env-config-skill`, `hipaa-compliance-skill` (`git rm`). Renamed `voice-call-rag-skill` → `voice-call-skill` (`git mv`) and rewrote it: removed pgvector/LangChain/OpenAI-embeddings/Google-Cloud-TTS entirely, replaced the knowledge base with a static `faq_entries` keyword-match table, added inline HIPAA voice rules and insurance-info collection, kept Groq for latency-sensitive turn classification only (never for generating spoken content). Rewrote `sms-handler-skill` as the merged SMS channel owner: folded in `conversation-agent-skill`'s full conversation state machine + Claude NLU (since that logic had no other home and "Patient books via SMS" depends on it — flagged this as an inference beyond the literal instruction list), `hipaa-compliance-skill`'s disclosure/consent/PHI-encryption/clinical-content-filter rules, a new insurance-collection stage, and a basic reminder job spec. Rewrote `appointment-booking-skill` to absorb `appointment-confirmation-skill`'s email-only channel (dropped the SMS/voice/DTMF confirmation-call fan-out, keeping just a fixed-template SendGrid email triggered from `confirm_booking`), added `insurance_provider`/`insurance_member_id` read paths and a `reminder_sent_at` column, and fixed all now-dangling `[[wikilink]]` references to deleted skills. Made minimal fixes to `doctor-auth-admin-skill` and `frontend-dashboard-skill` (per "keep as is") — only repaired broken cross-references to the four deleted skills, without touching scope; flagged to the user that `frontend-dashboard-skill` still contains Stripe/public-booking-page content, which conflicts with the earlier "delete Stripe" instruction and the 3-channel list (no web-booking channel), since "keep as is" was stated explicitly this turn. Verified via grep that no dangling references to deleted skill names remain except one intentional historical prose mention. Added a new "Project: US Doctor Booking Agent MVP" section to `CLAUDE.md` (channels, 2 phases, active-skills list, removed-from-scope list, and an MCP note clarifying that no MCP servers are actually wired up in this repo's config yet — the PostgreSQL/GitHub/Filesystem list is intended scope, not a live connection).

## Outcome

- ✅ Impact: Skill count reduced from 9 to 5; RAG/pgvector, multi-channel confirmation fan-out, and the standalone HIPAA/env-config skills are gone, folded into the 5 remaining skills. `CLAUDE.md` now documents the 3-channel, 2-phase MVP scope.
- 🧪 Tests: none (documentation/skill-spec changes only — no code exists yet in this repo)
- 📁 Files: 5 skill files rewritten, 4 skill files deleted, 1 renamed, `CLAUDE.md` updated, this PHR added
- 🔁 Next prompts: user should confirm whether `frontend-dashboard-skill`'s Stripe/public-booking-page content should also be stripped now (flagged conflict, not yet resolved); the git changes are staged/rewritten on disk but not committed — commit only on explicit request per repo convention.
- 🧠 Reflection: two of the "keep as is" skills (frontend-dashboard-skill, doctor-auth-admin-skill) had hard dependencies on deleted skills' content (wikilinks) that couldn't literally be left "as is" without producing broken references — resolved by doing the minimum viable fix (repoint references) while leaving substantive scope untouched, and surfacing the one real scope conflict (Stripe) rather than silently deciding it either way.

## Evaluation notes (flywheel)

- Failure modes observed: none this turn — the earlier destructive git mv/rm was correctly deferred to a fresh explicit instruction after the user asked for a status check first.
- Graders run and results (PASS/FAIL): N/A
- Prompt variant (if applicable): none
- Next experiment (smallest change to try): when a "keep as is" instruction is given for a file with dangling references to concurrently-deleted files, proactively surface the repair-vs-preserve tension before making the call, rather than deciding silently and flagging after the fact.
