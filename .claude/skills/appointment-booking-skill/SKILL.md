---
name: appointment-booking-skill
description: Handles appointment slot selection and confirmation — checks available slots, presents options to the patient, confirms booking, stores appointment data securely. Implementation only, no spec/planning logic. Use when building or modifying slot availability, holds, booking confirmation, or appointment persistence.
---

# Appointment Booking Skill

Implementation-only skill for the booking core of the appointment booking agent. This is the component [[conversation-agent-skill]] hands off to once it has a `booking_request` intent and a patient identity — it owns availability, holds, and the appointment record itself. Work covered by this skill goes straight to implementation — do not route it through `/sp.specify`, `/sp.plan`, or `/sp.tasks`.

## Stack

- Python 3.11+, FastAPI
- PostgreSQL — **availability is modeled entirely in-house for this MVP**, no external calendar integration (Google Calendar, etc.). If external calendar sync is added later, it's a new sync layer feeding the same `appointment_slots` table, not a replacement for it.

## Scope

In scope:
- Querying open slots within a lookahead window and returning a short list of human-presentable options.
- Atomically holding a slot for a patient while they decide/confirm, with an expiry so abandoned holds free back up.
- Finalizing a held slot into a confirmed appointment.
- Cancelling/releasing appointments and slots.

Out of scope (do not implement here):
- Conversational NLU (parsing "the second one" / "Tuesday at 3pm" into a slot choice) — that's [[conversation-agent-skill]]'s job; this skill exposes plain function calls by slot ID, not free text.
- SMS transport — [[sms-handler-skill]].
- Seeding/managing provider availability (an admin/ops path for creating `appointment_slots` rows) — assumed to exist separately; this skill only reads and mutates slot status.
- Spec, plan, or task generation.

## Data model (Postgres)

- `providers`: `id`, `name`, `active` (bool) — minimal for MVP; supports one or more providers.
- `appointment_slots`: `id`, `provider_id` (FK), `start_time`, `end_time`, `status` (`open` / `held` / `booked` / `cancelled`), `held_by_patient_id` (FK, nullable), `held_until` (timestamp, nullable), `created_at`, `updated_at`.
- `appointments`: `id`, `patient_id` (FK to `patients` from [[conversation-agent-skill]]), `slot_id` (FK, unique — one appointment per slot), `status` (`pending_confirmation` / `confirmed` / `cancelled` / `completed`), `conversation_id` (FK to `sms_conversations`, for traceability), `created_at`, `confirmed_at`, `cancelled_at`.

## API surface (functions, not endpoints)

This skill is called from application code (the conversation handler), not exposed as its own public HTTP API:

- `list_available_slots(provider_id: UUID | None, start_after: datetime, limit: int) -> list[SlotOption]` — returns `open` slots only, ordered by `start_time`. Sweep expired holds (see below) before querying so stale holds don't hide otherwise-available slots.
- `hold_slot(slot_id: UUID, patient_id: UUID, hold_duration_minutes: int = 5) -> HoldResult` — **atomic conditional update**: `UPDATE appointment_slots SET status='held', held_by_patient_id=:patient_id, held_until=now()+interval WHERE id=:slot_id AND status='open'`. If the update affects 0 rows, the slot was already taken — return a "no longer available" result so the caller re-queries `list_available_slots`. Never hold via a read-then-write (SELECT then UPDATE) — that's a race under concurrent SMS replies.
- `confirm_booking(slot_id: UUID, patient_id: UUID) -> Appointment` — transitions `held` → `booked`, creates the `appointments` row. Must verify the hold belongs to `patient_id` and `held_until` hasn't passed; if the hold expired, fail and require the patient to re-select. **After the appointment row is durably committed**, call [[appointment-confirmation-skill]]'s `send_confirmation_notifications(appointment_id)` (SMS + email + outbound voice call). This is a call-out after the transaction, not part of it — a notification-channel failure (e.g. SendGrid down) must never roll back a confirmed booking.
- `release_hold(slot_id: UUID) -> None` — sets the slot back to `open`, clears `held_by_patient_id`/`held_until`. Used on explicit decline, patient picks a different slot, or hold expiry.
- `cancel_appointment(appointment_id: UUID) -> None` — sets the appointment to `cancelled` and releases its slot back to `open`.

### Expired-hold sweep

Held slots must not stay locked forever if a patient abandons the conversation. Sweep on read rather than requiring a background scheduler for the MVP: at the start of `list_available_slots` (and optionally `hold_slot`), release any slot where `status='held' AND held_until < now()` back to `open` in the same transaction before querying.

## Booking flow (called from the conversation handler)

1. Conversation agent reaches `booking_intent` → calls `list_available_slots(...)`, gets back a short list (e.g. top 3), and presents them in plain language.
2. Patient's reply is resolved by the conversation agent into a specific `slot_id` (not by this skill) → calls `hold_slot(slot_id, patient_id)`.
   - If the hold fails (slot taken), tell the patient and re-present current options.
3. Conversation agent moves to `confirm_appointment`, presents the held slot's details, and requires an explicit yes.
   - Yes → `confirm_booking(slot_id, patient_id)`.
   - No / timeout → `release_hold(slot_id)`, return to slot selection.

## Security / data handling

- Appointment records are PHI. Encryption at rest and DB access restriction are an infrastructure requirement (least-privilege DB role for the app, not application-code enforced) — flag this as an ops decision if not already in place, don't assume it.
- Never expose internal slot/appointment UUIDs in outbound SMS text — the conversation agent renders human-readable labels (e.g. "Tuesday, March 3rd at 2:00 PM"), this skill only deals in IDs internally.
- Don't log full appointment details (patient name + time + provider together) at info level; log by ID and status transition only. Reserve full detail logging for error/debug paths behind an explicit flag.
- `confirm_booking` and `cancel_appointment` are the only two operations that create a durable record change visible to the patient as "your appointment is booked/cancelled" — both must be transactional (all-or-nothing) so a partial failure never leaves the slot `held` while telling the patient they're confirmed, or vice versa.

## Testing

- Concurrency test: two simultaneous `hold_slot` calls on the same slot — exactly one succeeds, the other gets "no longer available."
- Expiry test: a held slot past `held_until` is swept back to `open` on the next `list_available_slots`/`hold_slot` call, and a `confirm_booking` against an expired hold fails cleanly.
- Cancellation test: cancelling an appointment releases its slot back to `open` and it reappears in `list_available_slots`.
- Idempotency: calling `confirm_booking` twice on an already-`booked` slot doesn't double-book or error unhelpfully.
