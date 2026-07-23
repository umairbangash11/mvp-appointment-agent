---
name: doctor-auth-admin-skill
description: Doctor authentication and admin system for the appointment booking agent — signup, email verification, login, forgot/reset password, logout, profile update, and doctor-dashboard data queries. Implementation only, no spec/planning logic. Use when building auth endpoints, JWT issuance/revocation, password hashing, SendGrid email flows, or the doctor's own account/profile management.
---

# Doctor Auth & Admin Skill

Implementation-only skill for doctor account authentication and profile/admin management. This is the backend piece [[frontend-dashboard-skill]] was missing for staff login — it resolves that dependency, though not exactly as originally assumed there (see the reconciliation note below). Work covered by this skill goes straight to implementation — do not route it through `/sp.specify`, `/sp.plan`, or `/sp.tasks`.

## Reconciliation with [[frontend-dashboard-skill]]

That skill assumed a generic `staff` table with roles (`doctor`/`front_desk`/`admin`). This skill's actual schema is a single `doctors` table with **no role field** — every account is a doctor account, there is no multi-role staff concept in this MVP. [[frontend-dashboard-skill]] has been updated to match: its "Staff management" settings section now means "the signed-in doctor's own profile," not multi-account admin. If front-desk/admin staff accounts are needed later, that's a schema extension on top of this skill (an additional `role` column or a separate table), not something to add here speculatively.

## Stack

- Python 3.11+, FastAPI
- PostgreSQL
- `python-jose` for JWT encode/decode
- `bcrypt` for password hashing (used directly — `bcrypt.hashpw` / `bcrypt.checkpw` — not wrapped in `passlib`, since the project only ever hashes one thing with one algorithm)
- SendGrid (`sendgrid` Python SDK) for verification and password-reset emails
- `slowapi` for rate limiting (in-memory limiter; adequate for a single-instance MVP deployment — swap to a Redis-backed store before horizontally scaling, since in-memory counters don't share state across instances)

## Env config additions (owned by [[env-config-skill]])

This skill needs variables that skill didn't yet define — add them to its `Settings` schema, all **required**:

| Variable | Purpose |
|---|---|
| `JWT_SECRET` | Signs/verifies tokens. `SecretStr`, high-entropy, never reused from another purpose. |
| `JWT_EXPIRY_HOURS` | Default `24` — token lifetime (see the "24h token vs. 15-min auto-logout" note below). |
| `SENDGRID_API_KEY` | `SecretStr`. |
| `SENDGRID_FROM_EMAIL` | Verified sender address in SendGrid. |
| `FRONTEND_BASE_URL` | Used to build verification/reset links (e.g. `{FRONTEND_BASE_URL}/verify-email?token=...`) — not previously needed since no email-with-links flow existed before this skill. |

## Database tables

### `doctors` (as specified, with one naming fix)

`id`, `name`, `email` (unique), `password_hash` (renamed from the sketch's `password` — it stores a bcrypt hash, never a plaintext password, and the column name should say so), `clinic_name`, `phone`, `state`, `is_verified` (bool, default `false`), `is_active` (bool, default `true`), `created_at`.

`is_verified` and `is_active` are separate concerns: `is_verified` gates login until the email-verification flow completes; `is_active` is a general account-enabled flag (e.g. for a future admin-disable capability), independent of verification status.

**Integration point with [[appointment-booking-skill]]:** add `provider_id UUID NULL REFERENCES providers(id)` to `doctors`. Dashboard queries (today's appointments, revenue) need to know which `providers` row this doctor's schedule belongs to — without this FK there's no link between "who logged in" and "whose appointments to show." Populate it at signup (create a matching `providers` row, or link to an existing one if the clinic's provider record already exists).

### `password_resets` (as specified)

`id`, `doctor_id` (FK), `token`, `expires_at`, `is_used` (bool, default `false`).

### `email_verifications` (addition — not in the original schema sketch)

The stated requirements ("unique token generated, link expires 24 hours") need somewhere to store that token; the given schema only included `password_resets`. Mirror its shape: `id`, `doctor_id` (FK), `token`, `expires_at`, `is_used` (bool, default `false`).

### `revoked_tokens` (addition — not in the original schema sketch)

JWTs are stateless by default and can't be "invalidated" on logout without tracking something server-side. To satisfy requirement #6 ("JWT token invalidated" on logout), add: `id`, `jti` (the token's unique ID claim, indexed), `doctor_id` (FK), `revoked_at`, `expires_at` (copy the token's original expiry, so this table can be pruned of rows past their `expires_at` without needing to keep them forever).

Every JWT this skill issues must include a `jti` claim (a UUID) so it can be individually revoked. The auth dependency used on every protected endpoint checks the incoming token's `jti` against this table and rejects it if found — one extra indexed lookup per authenticated request, acceptable for MVP; cache it (in-memory/Redis) later if it becomes a bottleneck.

## Endpoints

### `POST /auth/signup`

Body: `name`, `email`, `password`, `clinic_name`, `phone`, `state`. Validate `password` ≥ 8 characters (Pydantic validator). Reject if `email` already exists (case-insensitive). Hash with `bcrypt.hashpw`. Insert `doctors` row (`is_verified=false`, `is_active=true`). Generate a verification token (`secrets.token_urlsafe(32)`), store in `email_verifications` with `expires_at = now() + 24h`. Send the verification email via SendGrid with a link to `{FRONTEND_BASE_URL}/verify-email?token=...`. Response: created doctor profile (never the password hash) + a "check your email" message.

### `POST /auth/verify-email`

Body: `token`. Look up `email_verifications`; reject if not found, expired, or already used. Set `doctors.is_verified = true`, mark the verification row `is_used = true`.

### `POST /auth/login`

Body: `email`, `password`. Rate-limited via `slowapi` (e.g. 5 attempts per 15 minutes per email+IP combination) — apply the same limiter to `forgot-password` too, since it's an equally common target for enumeration/abuse even though only `login` was explicitly specified. Look up by email; on any failure (not found, wrong password, not verified, not active) return a **generic** "invalid credentials" / "account not active" message — never reveal which specific check failed, to avoid leaking which emails are registered. Verify via `bcrypt.checkpw`. On success, issue a JWT (`python-jose`) with `doctor_id`, `email`, a fresh `jti`, and `exp = now() + JWT_EXPIRY_HOURS` (24h by default). Response: the JWT plus the doctor's profile (never the password hash).

**24h token vs. 15-minute auto-logout ([[frontend-dashboard-skill]]):** these are two different layers, not a contradiction. The JWT's 24h expiry is the server-side ceiling — the token is a valid bearer credential against the API for up to that long. The frontend's 15-minute inactivity timer is a client-side UX control that should **call `POST /auth/logout`** (not just discard the token locally) so the token is actually revoked via `revoked_tokens`, not merely forgotten by the browser. Without that call, a token sitting unused past the UI's 15-minute cutoff would still be valid server-side until its natural 24h expiry if it leaked some other way (network capture, XSS). [[frontend-dashboard-skill]] has been updated to reflect this.

### `POST /auth/forgot-password`

Body: `email`. **Always return the same generic success response regardless of whether the email exists** — this is a hard requirement, not a nice-to-have; returning a different response for known vs. unknown emails is a user-enumeration vulnerability. If the email does exist: generate a token, store in `password_resets` with `expires_at = now() + 1h`, email the reset link via SendGrid.

### `POST /auth/reset-password`

Body: `token`, `new_password` (≥ 8 characters). Look up `password_resets`; reject if not found, expired, or already used. Hash the new password with `bcrypt.hashpw`, update `doctors.password_hash`. Mark the reset row `is_used = true`. Also revoke all of that doctor's currently-valid tokens (insert their `jti`s into `revoked_tokens`, or simpler: revoke by `doctor_id` — the auth dependency can check "any token issued before this doctor's most recent password change" instead of tracking every `jti`) — a password reset should force re-login everywhere, not just invalidate the one-time reset token itself.

### `POST /auth/logout`

Requires a valid JWT. Extract its `jti`, insert into `revoked_tokens` with the token's original `expires_at`. Idempotent — logging out an already-revoked token is a no-op success, not an error.

### `GET /auth/profile`

Requires a valid, non-revoked JWT. Returns the authenticated doctor's profile (never `password_hash`).

### `PUT /auth/profile/update`

Requires a valid JWT. Body: any of `name`, `clinic_name`, `phone`, `state` (partial update — only supplied fields change). Email is **not** updatable through this endpoint — it's the login identifier and changing it would require re-running verification; that's out of scope unless explicitly requested later. Optional password change: require the **current** password to be supplied and verified before accepting a new one; on change, hash with bcrypt and apply the same "revoke existing sessions" treatment as `reset-password`.

### Doctor dashboard data (addition — feature #8 has no corresponding endpoint in the given list)

The requirements list "Doctor Dashboard Data" as feature #8, but the API endpoint list at the bottom only covers `/auth/*` — no dashboard endpoint was actually specified. Add these under `/dashboard`, matching exactly what [[frontend-dashboard-skill]] already assumes so the two skills agree on the contract:

- `GET /dashboard/stats` — today's appointment count and pending-payments count for the authenticated doctor's `provider_id` (joins into [[appointment-booking-skill]]'s `appointment_slots`/`appointments`). "No-show rate" from the frontend's original stat list needs an appointment status that distinguishes a no-show from a plain cancellation — check whether [[appointment-booking-skill]]'s `appointments.status` enum needs a `no_show` value added; if it doesn't have one yet, that's a small addition to that skill's schema, not something to work around here.
- `GET /dashboard/revenue` — monthly revenue and pending-payments amounts. **These fields have no data source yet.** No skill in this project has a payments/billing schema — this was already flagged as a gap in [[frontend-dashboard-skill]]. Until a billing/payments skill exists, these endpoints should return `0`/`null` with an explicit "not yet available" indicator rather than fabricating numbers.
- `GET /dashboard/recent-bookings` — most recent N appointments for the doctor's `provider_id`, reusing [[appointment-booking-skill]]'s data.

## Security rules

- Passwords: bcrypt, minimum 8 characters, never logged, never stored/returned in plaintext anywhere including error messages.
- `JWT_SECRET` from env only ([[env-config-skill]]), never hardcoded.
- Rate limiting on `login` and `forgot-password` via `slowapi`.
- Generic error messages on login/forgot-password to prevent user enumeration.
- All `/auth/*` endpoints except `signup`, `login`, `verify-email`, `forgot-password`, `reset-password` require a valid, non-revoked JWT via a shared FastAPI dependency.
- HIPAA-aware: this skill handles account credentials, not PHI directly, but ties into [[hipaa-compliance-skill]]'s broader posture — auto-logout and no-secrets-in-localStorage are enforced on the frontend side ([[frontend-dashboard-skill]]); this skill's job is making sure the tokens it issues can actually be revoked so those frontend controls have real teeth server-side.

## Out of scope

- Multi-role staff accounts (front-desk, admin) — this schema is doctor-only; a role system is a future extension, not built here.
- Payments/billing data backing the revenue dashboard fields — flagged above as a hard dependency gap, tracked separately.
- Spec, plan, or task generation.

## Testing

- Signup rejects a duplicate email and a password under 8 characters.
- Login before verification is rejected with the generic message (not a "please verify your email" message that would leak account existence — decide and document which generic wording is used, and use it consistently).
- Rate limiter blocks the 6th login attempt within the window for the same email+IP.
- `forgot-password` returns identical responses for a registered and an unregistered email.
- A used or expired `password_resets`/`email_verifications` token is rejected.
- After `logout`, the same JWT is rejected by a protected endpoint (`revoked_tokens` lookup works).
- After `reset-password`, a JWT issued before the reset is rejected (session revocation on password change works).
