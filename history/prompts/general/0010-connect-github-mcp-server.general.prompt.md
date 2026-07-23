---
id: 0010
title: Connect GitHub MCP server
stage: general
date: 2026-07-23
surface: agent
model: claude-sonnet-5
feature: none
branch: master
user: umairbangash11
command: none
labels: ["mcp", "github", "tooling", "git-remote"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
 - history/prompts/general/0010-connect-github-mcp-server.general.prompt.md
tests:
 - none
---

## Prompt

Connect GitHub MCP server
for this project.

This will allow:
- Code version control
- Branch management
- Commit history
- Pull requests

Repository:
us-doctor-booking-agent

## Response snapshot

Checked `git remote -v` (empty — no remote configured) and attempted `gh auth status` / `gh repo view` (the `gh` CLI isn't installed in this Bash environment). Asked whether the repo already exists and under which owner (user: exists, owner `umairbangash11`), and whether to also wire the local `origin` remote (user: yes). Sanity-checked the constructed URL (`https://github.com/umairbangash11/us-doctor-booking-agent`) via WebFetch before wiring anything to it — got a 404, which is ambiguous (GitHub returns 404 for both nonexistent and private repos to unauthenticated requests) — flagged that explicitly rather than assuming "doesn't exist," and the user confirmed it's private. Set `git remote add origin https://github.com/umairbangash11/us-doctor-booking-agent.git`. For the MCP server itself, followed Claude Code's own documented pattern for GitHub (`https://api.githubcopilot.com/mcp/` with a `Bearer` PAT header, not OAuth) rather than guessing, and gave the user the exact `claude mcp add` command to run themselves with a fine-grained PAT scoped to just this repo (Contents read/write, Pull requests read/write, Metadata read) — again avoiding having the credential pass through the chat transcript, consistent with the Postgres MCP setup two turns earlier.

## Outcome

- ✅ Impact: Local repo now has a real `origin` remote; user has exact, least-privilege instructions to connect the GitHub MCP server without exposing a PAT in this conversation.
- 🧪 Tests: none
- 📁 Files: none tracked in-repo (the `origin` remote is local git config, not a committed file; the MCP server registration happens in the user's own `~/.claude.json`)
- 🔁 Next prompts: User generates the fine-grained PAT and runs the given command; verify via `/mcp` that it shows `connected`.
- 🧠 Reflection: A 404 on an unauthenticated repo check is not evidence of nonexistence for a private repo — worth surfacing that ambiguity explicitly rather than either assuming the repo doesn't exist or silently proceeding as if the check had succeeded.

## Evaluation notes (flywheel)

- Failure modes observed: same PHR-timing gap as the prior turn — backfilled retroactively.
- Graders run and results (PASS/FAIL): N/A
- Prompt variant (if applicable): none
- Next experiment (smallest change to try): none beyond the PHR-timing fix already noted in 0009.
