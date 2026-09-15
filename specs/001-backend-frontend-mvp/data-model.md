# Data Model: Phase 1 MVP — Doctor Appointment Booking System

**Branch**: `001-backend-frontend-mvp` | **Date**: 2026-07-25

---

## Entity Relationship Overview

```
doctors ──────────────────────────────────────────────────────────┐
   │ id (PK)                                                       │
   │                                                               │
   │ 1                                                             │ 1
   ▼ N                                                             ▼ N
appointments ──────── N ──────── 1 ──── patients          conversation_sessions
   │ doctor_id (FK)                       id (PK)              phone_number
   │ patient_id (FK)                                            channel
   │ scheduled_at                                               current_step
   │ status                                                     collected_data
   └─────────────────────────────────────────────────────────────
```

---

## Table: `doctors`

Stores registered medical professionals. Each doctor has one clinic (single-clinic MVP).

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | UUID | PK, DEFAULT gen_random_uuid() | |
| `name` | VARCHAR(255) | NOT NULL | Full name |
| `email` | VARCHAR(255) | NOT NULL, UNIQUE | Login credential |
| `hashed_password` | VARCHAR(255) | NOT NULL | bcrypt hash, never plain text |
| `clinic_name` | VARCHAR(255) | NOT NULL | |
| `phone` | VARCHAR(20) | NOT NULL | US format |
| `state` | CHAR(2) | NOT NULL | US state abbreviation |
| `is_verified` | BOOLEAN | NOT NULL, DEFAULT false | Email verification gate |
| `email_verification_token` | VARCHAR(255) | NULLABLE | One-time token; cleared after use |
| `email_verification_expires` | TIMESTAMPTZ | NULLABLE | Token expiry (24h from signup) |
| `reset_password_token` | VARCHAR(255) | NULLABLE | One-time token; cleared after use |
| `reset_password_expires` | TIMESTAMPTZ | NULLABLE | Token expiry (1h from request) |
| `reminder_sent` | BOOLEAN | NOT NULL, DEFAULT false | (unused at doctor level; on appointments) |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | Audit field |
| `updated_at` | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | Auto-updated via trigger/hook |

**Indexes**: `email` (UNIQUE index, used for login lookup)

**State transitions**: `is_verified`: false → true (email verification, one-way)

---

## Table: `patients`

Created or matched by phone number during SMS/Voice booking. PHI columns are encrypted at rest.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | UUID | PK, DEFAULT gen_random_uuid() | |
| `name` | TEXT | NOT NULL | Encrypted at rest (Fernet) |
| `phone` | VARCHAR(20) | NOT NULL, UNIQUE | Encrypted; used as the unique patient identifier; plain for lookup before encrypt |
| `date_of_birth` | DATE | NULLABLE | Encrypted at rest |
| `insurance_carrier` | TEXT | NULLABLE | Encrypted; patient-reported |
| `insurance_member_id` | VARCHAR(100) | NULLABLE | Encrypted; patient-reported |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | |
| `updated_at` | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | |

**Indexes**: `phone` (UNIQUE index for patient matching during booking)

**PHI note**: `name`, `date_of_birth`, `insurance_carrier`, `insurance_member_id` MUST be encrypted
before INSERT and decrypted after SELECT. `phone` is stored as a SHA-256 hash for lookup plus the
encrypted value, or use a deterministic encryption scheme that allows equality lookup.

**Implementation note (MVP simplification)**: Store `phone` hashed (SHA-256, salted) for lookup
plus store all PHI fields using Fernet symmetric encryption keyed from `ENCRYPTION_KEY` env var.

---

## Table: `appointments`

Links a doctor to a patient at a specific time slot.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | UUID | PK, DEFAULT gen_random_uuid() | Public-facing reference ID |
| `doctor_id` | UUID | NOT NULL, FK → doctors.id, ON DELETE RESTRICT | |
| `patient_id` | UUID | NOT NULL, FK → patients.id, ON DELETE RESTRICT | |
| `scheduled_at` | TIMESTAMPTZ | NOT NULL | Appointment date + time (UTC) |
| `duration_minutes` | INTEGER | NOT NULL, DEFAULT 30 | Fixed 30-min slots for MVP |
| `reason_for_visit` | TEXT | NOT NULL | Encrypted at rest |
| `status` | VARCHAR(20) | NOT NULL, DEFAULT 'scheduled' | Enum: scheduled / cancelled / completed |
| `booking_channel` | VARCHAR(10) | NOT NULL | Enum: sms / voice |
| `insurance_snapshot` | JSONB | NULLABLE | Encrypted JSON snapshot of patient insurance at booking time |
| `reminder_sent` | BOOLEAN | NOT NULL, DEFAULT false | Set true after 24h reminder email sent |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | |
| `updated_at` | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | |

**Indexes**:
- `(doctor_id, scheduled_at)` — for dashboard stats and date-filtered queries
- `(scheduled_at, status, reminder_sent)` — for APScheduler reminder query
- `patient_id` — for patient history queries

**State transitions**:
```
scheduled → cancelled  (doctor cancels via API)
scheduled → completed  (future: mark complete after appointment time passes)
```

**Slot conflict rule**: Before inserting a new appointment, verify no existing `scheduled` appointment
exists for the same `doctor_id` with overlapping `[scheduled_at, scheduled_at + 30min)`.

---

## Table: `conversation_sessions`

Tracks in-progress SMS or Voice booking conversations. Auto-expires after 30 minutes of inactivity.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | UUID | PK, DEFAULT gen_random_uuid() | |
| `phone_number` | VARCHAR(20) | NOT NULL | Caller/texter's phone (hashed for lookup) |
| `channel` | VARCHAR(10) | NOT NULL | Enum: sms / voice |
| `current_step` | VARCHAR(50) | NOT NULL | Step name in the booking state machine |
| `collected_data` | JSONB | NOT NULL, DEFAULT '{}' | Partial booking data collected so far |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | |
| `expires_at` | TIMESTAMPTZ | NOT NULL | Set to NOW() + 30 min; refreshed on each interaction |

**Indexes**: `(phone_number, channel)` — for fast lookup on incoming message/call

**Lifecycle**: Row is created on first patient contact, updated after each exchange, and DELETED
(not soft-deleted) when booking is confirmed or session expires.

**SMS Booking State Machine Steps**:
```
greeting → collect_name → collect_dob → collect_reason →
collect_insurance_carrier → collect_insurance_id →
present_slots → confirm_slot → confirmed (terminal)
```

**Voice Booking State Machine Steps**:
```
greeting → faq_or_booking → collect_name → collect_dob → collect_reason →
collect_insurance_carrier → collect_insurance_id →
present_slots → confirm_slot → confirmed (terminal)
```

---

## Validation Rules

| Entity | Field | Rule |
|--------|-------|------|
| Doctor | email | Valid email format; unique in `doctors` table |
| Doctor | password | Min 8 characters; hashed with bcrypt before storage |
| Doctor | state | Must be a valid 2-letter US state abbreviation |
| Doctor | phone | US phone format (10 digits, optional country code) |
| Appointment | scheduled_at | Must be in the future; must be within clinic hours (Mon–Fri 9am–5pm); must not overlap existing `scheduled` appointment for same doctor |
| Appointment | status | Must be one of: `scheduled`, `cancelled`, `completed` |
| Appointment | booking_channel | Must be one of: `sms`, `voice` |
| ConversationSession | channel | Must be one of: `sms`, `voice` |
| Patient | phone | Must be a valid US phone number |

---

## Alembic Migration Strategy

1. **Initial migration**: Creates all 4 tables with indexes and FK constraints.
2. **Run on deploy**: `alembic upgrade head` runs automatically at application startup
   (FastAPI lifespan event).
3. **Rollback**: `alembic downgrade -1` reverts the last migration.
