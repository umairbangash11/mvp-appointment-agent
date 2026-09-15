---
id: 0030
title: Comment Out Database URL Logging
stage: general
date: 2026-09-15
surface: agent
model: claude-sonnet-4-6
feature: none
branch: dev
user: umairbangash11
command: inline edit
labels: ["security","logging","secrets","main"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - backend/main.py
tests:
  - none
---

## Prompt

In backend/main.py

Find this line:
logger.info("DATABASE_URL: %s", settings.DATABASE_URL)

OR

logger.info(f"DATABASE_URL: {settings.DATABASE_URL}")

Delete or comment this line:
# logger.info("DATABASE_URL: %s", settings.DATABASE_URL)

Never log sensitive information
like database URLs, passwords,
API keys in production.

## Response snapshot

Found the line at `backend/main.py:43` inside the `lifespan` context manager. Commented it out:

```python
# logger.info("DATABASE_URL: %s", settings.DATABASE_URL)  # never log secrets
```

## Outcome

- ✅ Impact: DATABASE_URL (which may contain credentials) is no longer written to logs in any environment.
- 🧪 Tests: none
- 📁 Files: backend/main.py
- 🔁 Next prompts: Audit other log statements for API keys, passwords, or tokens.
- 🧠 Reflection: Sensitive connection strings in logs are a common credential-leak vector, especially in cloud environments where logs are aggregated and retained.

## Evaluation notes (flywheel)

- Failure modes observed: none
- Graders run and results (PASS/FAIL): none
- Prompt variant (if applicable): none
- Next experiment (smallest change to try): Grep full codebase for other logger calls that reference settings.* secrets.
