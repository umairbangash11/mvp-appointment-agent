---
id: "0018"
title: Fix signup not persisting to PostgreSQL
stage: green
date: 2026-07-26
surface: agent
model: claude-sonnet-4-6
feature: doctor-auth
branch: master
user: umairbangash11
command: debug signup persistence
labels: ["bug","database","session","alembic","sqlalchemy"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - backend/alembic/env.py
  - backend/db/session.py
  - backend/main.py
tests:
  - none
---

## Prompt

New signups from frontend are not appearing in database. Signup shows success message but data not in PostgreSQL.

Check:
1. Is db.commit() called after doctor.save()?
2. Is there a separate test database being used?
3. Print actual DATABASE_URL being used at runtime
4. Check if session is properly closed after commit

Fix so all signups appear in PostgreSQL immediately!

## Response snapshot

Diagnosed three bugs:

1. **`alembic/env.py`**: `load_dotenv()` without a path looked for `.env` in `backend/` (CWD when server starts) — file doesn't exist there, so `DATABASE_URL` was never set in `os.environ`. Alembic fell back to the placeholder `driver://user:pass@localhost/dbname` from `alembic.ini`, breaking migrations on startup. Fixed by replacing the dotenv call with a direct `from config.settings import settings` import, which already handles the correct .env path.

2. **`session.py`**: `get_db` used `async with AsyncSessionLocal() as session:` (which auto-closes on exit) AND also called `await session.close()` in a `finally` block inside the same `with` — double-close. Replaced with an explicit `session = AsyncSessionLocal()` pattern so the single `finally: await session.close()` owns the lifecycle cleanly.

3. **`main.py`**: No visibility into which DATABASE_URL was actually being used at startup. Added `logger.info("DATABASE_URL: %s", settings.DATABASE_URL)` at the start of the lifespan so the target DB is always visible in server logs.

`db.commit()` (auth.py line 90) was already called correctly — the signup route itself had no bug.

## Outcome

- ✅ Impact: Alembic now always migrates the correct database; session lifecycle is single-owner; DATABASE_URL logged at startup
- 🧪 Tests: none run — manual verification via server logs recommended
- 📁 Files: backend/alembic/env.py, backend/db/session.py, backend/main.py
- 🔁 Next prompts: restart server and confirm DATABASE_URL log shows doctor_booking; sign up and query SELECT * FROM doctors in psql to verify row appears
- 🧠 Reflection: root cause was likely alembic running migrations against the wrong/placeholder DB, so the doctors table may not have existed in doctor_booking at all

## Evaluation notes (flywheel)

- Failure modes observed: silent load_dotenv failure, double-close session pattern
- Graders run and results (PASS/FAIL): none
- Prompt variant (if applicable): none
- Next experiment: add an integration test that signs up via the API and queries the DB directly
