---
id: 0012
title: Connect Twilio MCP server (declined - misconception)
stage: general
date: 2026-07-23
surface: agent
model: claude-sonnet-5
feature: none
branch: master
user: umairbangash11
command: none
labels: ["mcp", "twilio", "tooling", "pushback"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
 - history/prompts/general/0012-connect-twilio-mcp-server.general.prompt.md
tests:
 - none
---

## Prompt

Connect Twilio MCP server
for this project.

This will allow:
- Send SMS messages
- Handle voice calls
- Manage phone numbers
- Check message status

Used for:
- Patient SMS booking
- Voice call handling
- Appointment reminders

## Response snapshot

Pushed back on a mismatch between what a Twilio MCP server actually does and what the user's stated purpose implies. An MCP server here would give the coding assistant (this chat session) interactive Twilio tools — not the deployed application. The user's "Used for: Patient SMS booking, voice call handling, appointment reminders" framing reads as if connecting this MCP server would power those patient-facing features; it wouldn't. That capability comes from the FastAPI backend calling the Twilio Python SDK directly, per `sms-handler-skill` and `voice-call-rag-skill` — code that hasn't been implemented yet, and which an MCP connection does nothing to advance. Asked whether the user wanted (a) nothing, since app-level Twilio integration is a backend-code task unrelated to MCP, or (b) an MCP server specifically for the coding assistant's own interactive testing/debugging (send a test SMS, check delivery status) — a real but much narrower use case than "powering the app." User confirmed nothing is needed right now.

## Outcome

- ✅ Impact: Avoided connecting tooling based on a misunderstanding of what MCP servers do versus what the application's runtime needs — same category of catch as the filesystem MCP turn.
- 🧪 Tests: none
- 📁 Files: none — no action taken, by design.
- 🔁 Next prompts: If the user wants interactive Twilio testing/debugging during development later, that's a legitimate, narrower follow-up request, distinct from "powering the patient-facing app." The actual app-level Twilio integration is still pending implementation of `sms-handler-skill`/`voice-call-rag-skill`.
- 🧠 Reflection: A pattern is forming across the last two MCP requests (filesystem, Twilio): the user seems to be reaching for "connect an MCP server" as a general mechanism for "make this project able to do X," when in both cases X was actually either already covered by built-in tooling or was a backend-code responsibility unrelated to MCP. Worth staying alert for this same conflation on any future "connect Y MCP server" request in this project — check whether Y is something the *application* needs to do at runtime (not an MCP concern) versus something *I* need as a session tool (the actual MCP use case) before proceeding.

## Evaluation notes (flywheel)

- Failure modes observed: none — caught before any action was taken. PHR recorded in the same turn this time, not backfilled retroactively like the previous three.
- Graders run and results (PASS/FAIL): N/A
- Prompt variant (if applicable): none
- Next experiment (smallest change to try): given the emerging pattern (2 of the last 2 MCP requests were misconceptions), proactively ask "is this for the app's runtime, or for me during this session?" as the first question on any future MCP connection request, rather than waiting to notice the mismatch case-by-case.
