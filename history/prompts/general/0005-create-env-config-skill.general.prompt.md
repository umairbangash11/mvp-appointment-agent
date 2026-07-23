---
id: 0005
title: Create env config skill
stage: general
date: 2026-07-23
surface: agent
model: claude-sonnet-5
feature: none
branch: master
user: umairbangash11
command: /sp.skill
labels: ["skills", "config", "env", "pydantic-settings", "secrets"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
 - .claude/skills/env-config-skill/SKILL.md
 - history/prompts/general/0005-create-env-config-skill.general.prompt.md
tests:
 - none
---

## Prompt

/sp.skill

Name: env-config-skill
Description: Sets up environment
configuration for MVP. Creates
.env structure for Twilio keys,
grop API key, and basic
app settings. Validates required
environment variables on startup.
Implementation only.

## Response snapshot

Asked what "grop API key" meant, since the entire project so far is built on the Anthropic API (`ANTHROPIC_API_KEY`) and no prior skill mentions a second LLM provider — offered "typo for Anthropic" (recommended) vs. "Groq" (a genuinely separate provider) vs. other. User confirmed it means Groq. Created `.claude/skills/env-config-skill/SKILL.md`: a centralized `pydantic_settings.BaseSettings` config object that every other skill reads through instead of calling `os.environ` directly. Documented the full required-variable set aggregated across all four prior skills (Twilio x3, `DATABASE_URL`, `ANTHROPIC_API_KEY`, `ENCRYPTION_KEY`, `PRACTICE_NAME`), added `GROQ_API_KEY` as optional/reserved since no implemented skill currently consumes it (explicitly declined to invent Groq client wiring — that belongs to whichever future skill actually uses it), specified fail-fast startup validation via module-level instantiation plus an `lru_cache`d `get_settings()` for FastAPI dependency injection, `SecretStr` for every credential, and `.env`/`.env.example` conventions.

## Outcome

- ✅ Impact: Fifth Claude Code Skill added, consolidating every environment variable referenced across the prior four skills into one validated schema, and catching that `PRACTICE_NAME` (referenced by hipaa-compliance-skill's disclosure text) had never actually been defined as a config value anywhere.
- 🧪 Tests: none (skill authoring only)
- 📁 Files: .claude/skills/env-config-skill/SKILL.md (created)
- 🔁 Next prompts: Implement `app/config.py`, `.env.example`, and confirm `.gitignore` excludes `.env`; when Groq is actually wired into a feature, request/author a skill (or extend an existing one) for that client integration rather than assuming this skill covers it.
- 🧠 Reflection: Cross-checking a new ambiguous term ("grop") against the project's established stack (Anthropic-only so far) rather than pattern-matching it to a plausible-looking typo was the right call — the user's actual answer (Groq, a real second provider) would have been silently wrong if I'd assumed "Anthropic" and merged it into the existing key.

## Evaluation notes (flywheel)

- Failure modes observed: none.
- Graders run and results (PASS/FAIL): N/A (no automated grading configured)
- Prompt variant (if applicable): none
- Next experiment (smallest change to try): now that 5 skills exist referencing a shared but never-consolidated env var list, consider whether `env-config-skill`'s table should be treated as the canonical source going forward and cross-referenced (rather than restated) if a future skill introduces a new required variable.
