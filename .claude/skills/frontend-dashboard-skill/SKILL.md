---
name: frontend-dashboard-skill
description: Builds the Next.js medical dashboard frontend (staff-facing) and public patient booking page for the appointment booking agent — consumes the FastAPI backend. Implementation only, no spec/planning logic. Runs AFTER the backend skills are complete and their API contract is stable. Use when building any dashboard/public-booking UI, staff auth flow on the client, or Stripe-based copay collection.
---

# Frontend Dashboard Skill

Implementation-only skill for the Next.js frontend. **Sequenced after the backend**: [[whatsapp-skill]] and [[appointment-booking-skill]] are the patient-facing booking backend; this skill is a separate staff dashboard + public web booking surface that talks to that backend over REST. Do not start building this until the backend API contract below actually exists. Work covered by this skill goes straight to implementation — do not route it through `/sp.specify`, `/sp.plan`, or `/sp.tasks`.

## ⚠️ New backend dependencies this skill assumes

Every prior backend skill exposes **internal Python functions**, not HTTP endpoints. This skill cannot be fully implemented until these exist:

- **Doctor auth** — resolved by [[doctor-auth-admin-skill]] (`doctors` table, `/auth/*` endpoints, JWT issuance/revocation). Note: that skill's schema is **doctor-only, no roles** — there is no `staff` table and no `front_desk`/`admin` distinction. Every logged-in user is a doctor with full access to their own dashboard/settings. The "role-gated" language earlier versions of this skill used no longer applies; see the Settings page section below.
- **Payments** — Stripe integration (payment intents, webhooks) for the copay collection step on the public booking page. Still not covered by any existing skill — needs its own backend work (e.g. a `billing-payments-skill`). `GET /dashboard/revenue`'s pending-payments/revenue figures are blocked on this too (see [[doctor-auth-admin-skill]]'s dashboard-data section).
- **REST wrappers** around [[appointment-booking-skill]]'s functions (`list_available_slots`, `hold_slot`, `confirm_booking`, `cancel_appointment`) and [[whatsapp-skill]]'s `patients` data — currently internal, need HTTP routes.

Treat the endpoint list under "Backend API contract" below as what this skill needs to exist, not something it builds itself.

## Stack

- Next.js 14 (App Router)
- Tailwind CSS
- shadcn/ui (components — Skeleton, Card, Table, Dialog, etc.)
- Framer Motion (page transitions, chart entrance animations)
- Recharts (revenue chart and any other data viz)
- lucide-react (icons)
- Axios (API client, base URL from `NEXT_PUBLIC_API_BASE_URL`)
- `@stripe/stripe-js` + `@stripe/react-stripe-js` — required for the copay step (Stripe Payment Element), not in the originally stated list but necessary to fulfill "pay copay online" with Stripe.

## Route structure

- `app/(dashboard)/*` — authenticated staff pages, wrapped in the dark-sidebar layout and an auth guard.
- `app/(public)/book/*` — the public patient booking page, no sidebar, no auth.
- `middleware.ts` — checks the in-memory/session auth state before rendering `(dashboard)` routes; redirects to `/login` if the access token is missing or expired. This is a UX convenience, not the security boundary — every API call must also be authorized server-side regardless of what the client-side guard does.

## Design system

- Medical blue color theme (primary blues, high-contrast text, avoid clinical sterility — warm neutrals for backgrounds).
- Glassmorphism cards for stat tiles: `backdrop-blur`, translucent background, subtle border, on the dashboard's stat row.
- Dark sidebar, fixed left, holds primary nav (Dashboard, Appointments, Patients, Settings). No role-gating — every logged-in account is a doctor with the same access (see [[doctor-auth-admin-skill]]; there's no multi-role staff concept in this MVP).
- Page transitions via Framer Motion `AnimatePresence` on route change; chart entrance animation (fade + scale) on mount, not on every re-render.
- Loading skeletons (shadcn `Skeleton`) for every data-fetching region — stat cards, chart, tables — shown until the corresponding query resolves.
- Hover effects on interactive rows/cards (subtle elevation/border color shift), respecting reduced-motion preference.
- Mobile responsive: sidebar collapses to a bottom nav or drawer below the `md` breakpoint.

## Pages

### 1. Doctor Dashboard (`/dashboard`)

- Stat cards (glassmorphism): appointments today, no-show rate, pending payments.
- Revenue chart (Recharts), animated on mount.
- Recent bookings list (most recent N appointments, name + time + status).
- All of the above render skeletons until their query resolves.

### 2. Appointments Page (`/dashboard/appointments`)

- Calendar view — no calendar library was specified in the stack; build a lightweight month-grid with Tailwind rather than pulling in a new heavy dependency (e.g. FullCalendar) unless the user asks for one specifically.
- List view with filters: date range, status (`pending_confirmation` / `confirmed` / `cancelled` / `completed` — matches [[appointment-booking-skill]]'s `appointments.status`).
- Cancel/reschedule actions call the REST wrappers around `cancel_appointment` / a reschedule flow (release + re-hold) from [[appointment-booking-skill]].

### 3. Patient Records Page (`/dashboard/patients`)

- Patient list (name, phone, last visit) and per-patient appointment history.
- **No diagnosis field exists anywhere in the current data model** — [[whatsapp-skill]]'s "never includes diagnosis" rule means there's structurally nothing to accidentally render here. Don't add a notes/diagnosis field to satisfy this page without checking with the user first.
- `patients.name` is stored encrypted at the DB layer per [[whatsapp-skill]], but decryption happens server-side (the SQLAlchemy `TypeDecorator` is transparent) — API responses already contain plaintext name. The frontend never handles encryption/decryption itself.
- No sensitive data cached in browser storage: use in-memory query state (React Query/SWR) only, never persist patient data to `localStorage`/`sessionStorage`.

### 4. Settings Page (`/dashboard/settings`)

- Clinic info (practice name, address) and working hours.
- Doctor profile management — this replaces the originally-planned "Staff management" section, since [[doctor-auth-admin-skill]]'s schema has no multi-role staff concept: form for the signed-in doctor's own `name`/`clinic_name`/`phone`/`state` (maps to `PUT /auth/profile/update`) plus a change-password flow (current password required). If multi-account staff management is needed later, that's a backend schema extension first, not something to build speculatively on the frontend now.
- Twilio/Groq config: **read-only status display only** (e.g. "Twilio: connected", masked account SID) — never render or accept raw secret values (`TWILIO_AUTH_TOKEN`, `ANTHROPIC_API_KEY`, `GROQ_API_KEY`, `ENCRYPTION_KEY`) in the browser, ever. The backend must expose a masked/status endpoint (secrets held as `SecretStr` server-side), not the raw `.env` values. Don't build this page as a form that edits `.env` contents directly.

### 5. Patient Booking Page (`/book`, public, no auth)

- Select service → pick date/time (reads open slots via the REST wrapper around `list_available_slots`) → intake form (name, phone, DOB; no diagnosis/reason-for-visit field beyond a non-clinical category picklist) → pay copay via Stripe Payment Element.
- This page collects PHI from the public internet outside the WhatsApp channel — apply the same consent principle as [[whatsapp-skill]]'s consent flow: web bookings should write a consent record through an equivalent mechanism (method `web_form` instead of `whatsapp`), not silently collect data without an equivalent disclosure/consent step.

## Backend API contract (assumed — see the dependency warning above)

| Endpoint | Purpose |
|---|---|
| `POST /auth/signup`, `POST /auth/verify-email`, `POST /auth/login`, `POST /auth/forgot-password`, `POST /auth/reset-password`, `POST /auth/logout`, `GET /auth/profile`, `PUT /auth/profile/update` | [[doctor-auth-admin-skill]] — full auth + profile lifecycle |
| `GET /dashboard/stats`, `GET /dashboard/revenue`, `GET /dashboard/recent-bookings` | [[doctor-auth-admin-skill]] — revenue/pending-payments fields are placeholder (`0`/`null`) until a payments backend exists |
| `GET /appointments`, `POST /appointments/{id}/cancel`, `POST /appointments/{id}/reschedule` | Wraps [[appointment-booking-skill]] |
| `GET /patients`, `GET /patients/{id}` | Wraps [[whatsapp-skill]] patient data |
| `GET /settings/clinic`, `PUT /settings/clinic` | Clinic info + hours |
| `GET /settings/integrations` | Masked Twilio/Anthropic/Groq status — never raw secrets |
| `GET /public/services`, `GET /public/slots`, `POST /public/bookings`, `POST /public/payments/intent` | Public booking page (last one creates a Stripe payment intent — not yet built) |

No `/staff` endpoints — there's no multi-account staff management in this MVP (see [[doctor-auth-admin-skill]]).

## HIPAA rules (frontend-specific, layered on the HIPAA/NABIDH rules owned by [[whatsapp-skill]])

- **No diagnosis shown** — enforced structurally by the data model having no diagnosis field; never add one to satisfy a UI request without flagging it first.
- **Encrypted API calls** — HTTPS required for any non-local environment. `http://localhost:8000` is fine for local dev only; staging/production must be HTTPS, which is a deployment requirement, not something this skill's code enforces on its own.
- **JWT authentication** — [[doctor-auth-admin-skill]] issues a 24-hour token (`JWT_EXPIRY_HOURS`), sent via `Authorization: Bearer`, kept in memory (React context), never in `localStorage`. Survive page refresh with a silent re-check against `GET /auth/profile` on load (no refresh-token cookie needed for this MVP, since the token itself is long-lived and revocable — see next bullet).
- **Auto logout after 15 min** — client-side inactivity timer (resets on user interaction) that, on firing, **calls `POST /auth/logout`** (not just clears local state) so the token is actually revoked server-side via [[doctor-auth-admin-skill]]'s `revoked_tokens` table, then clears the in-memory token and redirects to `/login`. This matters specifically because the token's own expiry is 24h, much longer than the 15-minute UI window — merely forgetting the token client-side would leave it valid elsewhere for the rest of that 24h if it leaked some other way (network capture, XSS). Calling `logout` closes that gap.
- **No sensitive data in `localStorage`** — no tokens, no patient PHI, no secrets. Non-sensitive UI preferences (theme, sidebar collapsed state) are fine there.

## Frontend env config

`.env.local` (Next.js convention): `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000` for dev. Anything prefixed `NEXT_PUBLIC_` is bundled into client JS and publicly visible — never put a secret there. `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY` is the one safe exception (Stripe's publishable keys are meant to be public); the Stripe secret key stays backend-only.

## Out of scope

- Implementing any backend endpoint listed above, staff auth, or Stripe payment-intent/webhook handling — that's backend work tracked separately from this frontend skill.
- Spec, plan, or task generation.

## Testing

- Auth guard redirects unauthenticated requests to `(dashboard)` routes to `/login`.
- Auto-logout timer fires after 15 minutes of inactivity, calls `POST /auth/logout`, and clears the in-memory token.
- No `localStorage.setItem` call exists anywhere for tokens or patient data (a simple repo-wide grep can enforce this in CI).
- No component ever renders a field named diagnosis/condition or similar — since the data model has none, this should be trivially true; a lint/test catches regressions if one is ever added upstream.
