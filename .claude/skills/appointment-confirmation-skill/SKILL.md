---
name: appointment-confirmation-skill
description: Sends multi-channel appointment confirmation (SMS + email + an outbound voice call with DTMF confirm/cancel) when a booking is confirmed. Implementation only, no spec/planning logic. Use when building the post-booking notification fan-out, the outbound voice IVR flow, or email confirmation templates.
---

# Appointment Confirmation Skill

Implementation-only skill for the three-channel confirmation sent when a booking is finalized. Triggered by [[appointment-booking-skill]]'s `confirm_booking()` succeeding — not a standalone entry point. Work covered by this skill goes straight to implementation — do not route it through `/sp.specify`, `/sp.plan`, or `/sp.tasks`.

## Reuse — do not reimplement these

| Channel | Reused from | New in this skill |
|---|---|---|
| SMS | [[sms-handler-skill]]'s `send_sms` | Just the message template |
| Email | SendGrid client pattern already set up in [[doctor-auth-admin-skill]] | The template + call site; don't instantiate a second SendGrid client config |
| Voice | Twilio Voice API / TwiML mechanics from [[voice-call-rag-skill]] | **Outbound** calling — everything built there so far is inbound-only (patient calls the clinic). This is the first outbound-call capability in the project |
| Cancellation (via "Press 2") | [[appointment-booking-skill]]'s `cancel_appointment` | The DTMF handler that calls it |

## Gap: `patients.email` doesn't exist

No skill collects a patient email address anywhere — [[conversation-agent-skill]]'s `patients` table only has phone-derived identity + name; the web intake form in [[frontend-dashboard-skill]] collects name/phone/DOB, no email. "All 3 channels together" can't work until something asks for it.

**Resolution:** add `email` (nullable) to `patients`. Make email collection an **optional, low-friction ask**, not a new hard gate — e.g. [[conversation-agent-skill]] adds a line at `confirm_appointment`: "Want an email confirmation too? Reply with your email, or skip." Don't block booking on it. This skill's fan-out **skips the email channel gracefully** when `patients.email` is null — that's an expected, common case, not an error.

## Trigger

Add a call site in [[appointment-booking-skill]]'s `confirm_booking()`: immediately after the appointment is durably confirmed, call this skill's `send_confirmation_notifications(appointment_id)`. All three channels fire from that single call; each is independent — one channel failing (e.g. SendGrid down) must not roll back the confirmed booking or block the other two.

## `confirmation_log` table (new)

`id`, `appointment_id` (FK), `channel` (`sms` / `email` / `voice`), `status` (`sent` / `failed` / `no_answer` / `skipped`), `sent_at`. Same audit-trail reasoning as `rag_queries`/`call_transcripts` elsewhere in the project — three independent delivery mechanisms firing off one event need somewhere to record what actually happened when a patient says "I never got a confirmation."

## Channel 1 — SMS

Template (as specified): `"Appointment confirmed! {day} {time} Dr. {doctor_last_name}"`. Calls [[sms-handler-skill]]'s existing `send_sms`.

## Channel 2 — Email

Full appointment details via SendGrid, reusing the client setup already established in [[doctor-auth-admin-skill]] rather than configuring a second one. Content: practice name, doctor name, date/time. **Clinic address/working hours have no home table yet** — `doctors.clinic_name` exists but there's no `clinic_settings` schema despite [[frontend-dashboard-skill]]'s Settings page already referencing "clinic info + working hours." Not building that here (out of scope for this feature) — the email template omits address/hours until that gap is closed elsewhere, rather than fabricating placeholder data. Skip sending entirely (log `status='skipped'` in `confirmation_log`) when `patients.email` is null.

## Channel 3 — Outbound voice call (new capability)

This call reads a **fixed template with appointment data substituted in — not an LLM-generated response.** No RAG, no Groq. That's deliberate, and better than RAG-grounding for something this consequential: zero generation step means zero hallucination risk on the message that tells a patient when their appointment is.

Because the content is static, **use Twilio's native `<Say voice="Google.en-US-Neural2-C">`** (or whichever Google-family voice) directly in TwiML — skip [[voice-call-rag-skill]]'s Google Cloud TTS API + audio-file-serving pipeline entirely. That pipeline exists to handle dynamic, RAG-generated text; a fixed template doesn't need it. This is the "simpler alternative" that skill already flagged as worth considering, and here it's a clear win, not just an option.

### Initiating the call

`send_confirmation_notifications` calls Twilio's REST API directly: `client.calls.create(to=patient_phone, from_=TWILIO_FROM_NUMBER, url=f"{API_BASE_URL}/voice/outbound/confirm?appointment_id={id}")`. Requires a new env var, **`API_BASE_URL`** — the backend's own publicly reachable base URL, needed so Twilio knows where to fetch TwiML from once the call connects. Not previously needed since every other Twilio interaction so far has been *inbound* (Twilio calling a webhook URL configured in the Twilio console, not constructed by our own code). Add to [[env-config-skill]] as required.

### `POST /voice/outbound/confirm`

Fires when the patient answers. Returns TwiML: `<Say>` the AI disclosure + confirmation script (as specified — the disclosure line is still first, per [[voice-call-rag-skill]]'s HIPAA voice rules, even though...), then `<Gather input="dtmf" numDigits="1" action="/voice/outbound/gather?appointment_id={id}">`.

**No fresh consent gate.** Unlike an inbound call from an unknown number, this patient already consented when they initiated the original booking (recorded in [[hipaa-compliance-skill]]'s `consents` table, whichever channel they used). Re-running the full `consent_pending` yes/no gate here would be redundant friction on a call *we* placed to close the loop on a booking *they* started — the AI disclosure line stays (it's a courtesy/identification, not a consent request), but there's no blocking yes/no before proceeding.

### `POST /voice/outbound/gather`

Handles the DTMF digit:

- `Digits=1` — reconfirm. Log to `confirmation_log`. `<Say>` "Thank you, see you then!" and hang up. No appointment-state change needed (it's already `confirmed`).
- `Digits=2` — cancel. Call [[appointment-booking-skill]]'s `cancel_appointment(appointment_id)`. `<Say>` "Your appointment has been cancelled. Please call us to reschedule." and hang up. Also fire a cancellation SMS via [[sms-handler-skill]]'s `send_sms` for a written record — a voice-only cancellation with no text trail is a bad pattern for something this consequential.
- No input / invalid digit — replay the prompt once (`<Gather>` again); if still nothing, hang up gracefully with no state change. The SMS and email confirmations already went out independently, so a missed IVR response isn't a failure of the booking, just of this one bonus channel.

### `POST /voice/outbound/status`

Twilio's outbound call-status callback. Log the outcome (`no-answer` / `busy` / `failed` / `completed`) to `confirmation_log`. **Voice is a best-effort third channel — no retry logic.** SMS and email are the reliable channels (they don't require the patient to pick up in real time); a missed or unanswered confirmation call is an acceptable degraded case, not something to re-queue or alert on for this MVP.

## Env vars (additions to [[env-config-skill]])

- `API_BASE_URL` — required, new (see above). No other new credentials — this skill reuses `TWILIO_*` and `SENDGRID_*`, already configured.

## Out of scope

- Building the `clinic_settings` schema (address/working hours) that the email template is currently missing — flagged, not resolved here.
- Retry/alerting logic for missed voice confirmations.
- Spec, plan, or task generation.

## Testing

- Booking a patient with no email on file sends SMS + voice, skips email, and logs `status='skipped'` for the email row in `confirmation_log` — not an error.
- Pressing 2 on the outbound call actually cancels the appointment via [[appointment-booking-skill]] and fires a cancellation SMS.
- A `no-answer` outbound call still leaves the booking `confirmed` — voice failure never rolls back the appointment.
- The outbound call's TwiML never triggers the RAG pipeline or a Groq call — assert on this directly (a regression here would silently reintroduce hallucination risk on a fixed-template message).
- One channel failing (e.g. mock SendGrid raising) doesn't prevent the other two from sending.
