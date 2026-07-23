---
id: 0009
title: Connect PostgreSQL MCP server
stage: general
date: 2026-07-23
surface: agent
model: claude-sonnet-5
feature: none
branch: master
user: umairbangash11
command: none
labels: ["mcp", "postgresql", "tooling", "read-only"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
 - history/prompts/general/0009-connect-postgresql-mcp-server.general.prompt.md
tests:
 - none
---

## Prompt

Connect PostgreSQL MCP server
for this project.

This will allow direct
database access for:
- Patient records
- Appointments
- Doctor profiles
- RAG documents table

Database: PostgreSQL
ORM: SQLAlchemy

## Response snapshot

This was an actual tooling/config task, not a skill-authoring one. First checked the project for a live database (none exists — no `.env`, no docker-compose, no backend code; every prior skill is documentation only). Asked whether a Postgres instance already exists (user: yes, will provide connection string) and what access level the MCP server should have (user: read-only). Before writing anything, verified via WebFetch that the previously-known `@modelcontextprotocol/server-postgres` reference server is now archived/unmaintained, and that Claude Code's current official docs point to `@bytebase/dbhub` instead, which enforces read-only at the database engine level (session itself set read-only), matching the user's choice without needing a separate DB role. Also confirmed `.mcp.json`/`~/.claude.json` support `${VAR}` environment-variable expansion sourced from the process environment at Claude Code launch (not automatic `.env` loading). Rather than have the user paste their DB password into the chat transcript, gave them the exact `claude mcp add --scope local --transport stdio postgres-db -- npx -y @bytebase/dbhub@latest --dsn "..."` command to run themselves via the `!` prefix, defaulting to local scope (private, not committed to git) and offering project scope + `${DATABASE_URL}` expansion as a later option for team sharing.

## Outcome

- ✅ Impact: Verified current tooling recommendation (archived vs. maintained package) before committing to a config, rather than trusting possibly-stale memory; kept the actual DB credential out of the conversation transcript.
- 🧪 Tests: none
- 📁 Files: none (guidance only — the actual `claude mcp add` command is run by the user, not tracked in this repo)
- 🔁 Next prompts: User runs the given command with their real connection string; verify via `/mcp` that it shows `connected`.
- 🧠 Reflection: For any request to "connect an MCP server," checking current package/documentation status via WebFetch before writing config is worth the extra round trip — the reference implementation I might have recalled from training was archived, and the docs pointed to a different, better-suited tool (engine-level read-only enforcement).

## Evaluation notes (flywheel)

- Failure modes observed: this PHR was written retroactively — the turn itself completed without one, breaking the project's "PHR after every user message" convention. Caught and backfilled here along with the following two turns.
- Graders run and results (PASS/FAIL): N/A
- Prompt variant (if applicable): none
- Next experiment (smallest change to try): treat non-code/tooling turns (MCP setup, config questions) as still requiring a PHR at the time, not just skill-authoring turns — the convention doesn't carve out an exception for "this wasn't a skill file."
