# Feature Specification: Phase 1 MVP — Doctor Appointment Booking System

**Feature Branch**: `001-backend-frontend-mvp`
**Created**: 2026-07-25
**Status**: Draft
**Input**: User description: "Phase 1 — Backend + Basic Frontend together so I can test backend through frontend immediately."

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Doctor Registration & Authentication (Priority: P1)

A doctor registers on the platform by providing their personal and clinic details. They receive an
email verification link, confirm their account, then log in to access a protected dashboard. They can
reset their password via email if forgotten and update their profile at any time.

**Why this priority**: Authentication is a prerequisite for all dashboard and appointment features;
nothing else can be tested without a working doctor account.

**Independent Test**: A doctor can register, verify their email, log in, view the dashboard, and log
out — independently of SMS, voice, or appointment features.

**Acceptance Scenarios**:

1. **Given** a new doctor provides name, email, password, clinic name, phone, and state, **When** they
   submit signup, **Then** they receive an email verification link and cannot log in until verified.
2. **Given** a doctor clicks the verification link, **When** it is valid and unexpired, **Then** their
   account is activated and they can log in.
3. **Given** a verified doctor provides correct email and password, **When** they log in, **Then** they
   receive an access token and are redirected to the dashboard.
4. **Given** a logged-in doctor is idle for 15 minutes, **When** the inactivity timer expires, **Then**
   they are automatically logged out and redirected to the login page.
5. **Given** a doctor requests a password reset, **When** they submit their email, **Then** they receive
   a time-limited reset link via email.
6. **Given** a doctor uses a valid reset link, **When** they set a new password, **Then** the password
   is updated and the reset link is invalidated immediately.

---

### User Story 2 — Patient Books Appointment via SMS (Priority: P2)

A patient texts the clinic's phone number. An AI assistant greets them, identifies itself as an AI,
collects their personal and insurance information, presents available appointment slots, confirms the
booking, and sends an SMS confirmation.

**Why this priority**: SMS booking is the primary patient-facing channel of this MVP.

**Independent Test**: A patient can send a text and complete a full booking end-to-end without the
frontend or voice channel being involved.

**Acceptance Scenarios**:

1. **Given** a patient sends any text to the clinic number, **When** the system receives it, **Then**
   the AI responds and discloses it is an AI assistant before collecting any information.
2. **Given** the AI collects all required fields (name, date of birth, reason for visit, insurance
   carrier, insurance member ID, preferred slot), **When** the patient confirms, **Then** a booking is
   created and an SMS confirmation with appointment details is sent.
3. **Given** a patient provides their insurance carrier, **When** the AI records it, **Then** it is
   stored as patient-reported only; the AI does NOT attempt real-time verification.
4. **Given** a patient asks for medical advice (e.g., "Do I have diabetes?"), **When** the AI receives
   it, **Then** the AI declines, states it cannot provide medical advice, and redirects to booking.
5. **Given** no available slot exists at the patient's preferred time, **When** the AI presents
   alternatives, **Then** the patient can select a different slot before confirming.

---

### User Story 3 — Patient Books Appointment via Voice Call (Priority: P3)

A patient calls the clinic's voice number. An AI voice agent answers, identifies itself as an AI,
conducts a natural conversation, answers static FAQ questions, collects booking details, and confirms
the appointment. An SMS confirmation is sent to the patient after the call ends.

**Why this priority**: Voice is a secondary booking channel adding accessibility for patients who
prefer calling over texting.

**Independent Test**: A patient can call the voice number, complete a booking through voice conversation,
and receive an SMS confirmation — independently of the SMS or frontend channels.

**Acceptance Scenarios**:

1. **Given** a patient calls the clinic number, **When** the call connects, **Then** the AI voice agent
   answers and discloses it is an AI within the first utterance.
2. **Given** the AI voice agent is active, **When** a patient asks a static FAQ question (clinic hours,
   location, accepted insurance, services offered), **Then** the AI provides the correct predefined
   answer without improvising clinical information.
3. **Given** a patient completes the voice booking flow, **When** the call ends, **Then** an SMS
   confirmation with appointment details is sent to the caller's number within 2 minutes.
4. **Given** a patient asks for medical advice during a call, **When** the AI receives the question,
   **Then** it declines and redirects the caller to speak with a doctor directly.

---

### User Story 4 — Email Confirmation & Reminders (Priority: P4)

When an appointment is booked via any channel (SMS or Voice), the system sends a booking confirmation
email to the patient and a notification email to the doctor. A reminder email is sent to the patient
before the appointment time.

**Why this priority**: Email confirmation provides patients and doctors with a reliable paper trail
outside of SMS.

**Independent Test**: After a booking is created, both patient and doctor receive confirmation emails
within 2 minutes — testable independently of the frontend.

**Acceptance Scenarios**:

1. **Given** a new appointment is booked via SMS or Voice, **When** it is saved, **Then** a confirmation
   email is sent to the patient and a notification email to the doctor within 2 minutes.
2. **Given** an upcoming appointment, **When** 24 hours remain before it, **Then** a reminder email is
   sent to the patient.

---

### User Story 5 — Doctor Views & Manages Appointments via Dashboard (Priority: P5)

A logged-in doctor can view all their appointments on a dashboard, see today's appointment count and
total patient statistics, and navigate to an appointments page where they can filter, view patient
details, and cancel appointments. The frontend makes the backend fully testable through a browser.

**Why this priority**: The frontend is required for end-to-end browser-based testing of all backend
APIs without external tools like Postman.

**Independent Test**: A logged-in doctor can view the dashboard with real data, browse and filter
the appointments list, and cancel an appointment — verifiable from any browser.

**Acceptance Scenarios**:

1. **Given** a logged-in doctor lands on the dashboard, **When** the page loads, **Then** today's
   appointment count, total patient count, and a list of recent bookings display live data.
2. **Given** a logged-in doctor is on the appointments page, **When** they apply a date or status
   filter, **Then** the list updates to show only matching appointments.
3. **Given** a doctor cancels an appointment, **When** the action is confirmed, **Then** the
   appointment status changes and the updated status is reflected immediately in the list.
4. **Given** an unauthenticated visitor navigates to the dashboard or appointments page, **When** the
   page loads, **Then** they are redirected to the login page without any appointment data exposed.

---

### Edge Cases

- What happens when a patient sends a blank or unintelligible SMS during an active booking session?
- What happens when a voice call is disconnected mid-booking?
- What happens when the email verification link is clicked after it has expired?
- What happens when a doctor's access token expires mid-session on the frontend?
- What happens when the same patient number starts a new SMS booking while one is already in progress?
- What happens when no appointment slots are available for the patient's requested date range?

## Requirements *(mandatory)*

### Functional Requirements

**Doctor Authentication**

- **FR-001**: The system MUST allow a doctor to register with name, email, password, clinic name,
  phone number, and US state.
- **FR-002**: The system MUST send an email verification link upon signup; the account MUST remain
  inactive until the link is clicked.
- **FR-003**: The system MUST allow a verified doctor to log in with email and password and receive a
  time-limited access token.
- **FR-004**: The system MUST automatically terminate a doctor's session after 15 minutes of inactivity
  on both backend and frontend.
- **FR-005**: The system MUST allow a doctor to request a password reset link sent to their registered
  email address.
- **FR-006**: The system MUST allow a doctor to set a new password using a valid, unexpired reset link;
  the link MUST be invalidated immediately after use.
- **FR-007**: The system MUST allow a logged-in doctor to view and update their profile information
  (name, clinic name, phone, state).
- **FR-008**: All doctor passwords MUST be stored in hashed form; plain-text passwords MUST NEVER be
  stored, logged, or transmitted.
- **FR-009**: All dashboard and appointment API endpoints MUST reject requests without a valid access
  token and return an authentication error.

**SMS Booking Agent**

- **FR-010**: The system MUST receive and process inbound SMS messages from patients.
- **FR-011**: The AI SMS agent MUST identify itself as an AI at the start of every new conversation
  before collecting any patient data.
- **FR-012**: The AI MUST collect all of the following before confirming a booking: patient name, date
  of birth, reason for visit, insurance carrier, insurance member ID, and preferred appointment slot.
- **FR-013**: The AI MUST NOT provide medical diagnoses, treatment recommendations, or clinical advice.
- **FR-014**: The system MUST send an SMS booking confirmation to the patient upon successful booking.
- **FR-015**: Patient-reported insurance information MUST be stored as-is; no real-time insurance
  eligibility verification is performed.

**Voice Call Agent**

- **FR-016**: The system MUST receive and handle inbound voice calls.
- **FR-017**: The AI voice agent MUST identify itself as an AI at the start of every call before
  any data collection begins.
- **FR-018**: The AI MUST answer a predefined set of static FAQ questions (clinic hours, location,
  accepted insurance plans, available services) without improvising clinical information.
- **FR-019**: The AI MUST collect the same booking fields as the SMS agent (see FR-012) during a
  voice booking.
- **FR-020**: Upon completing a voice booking, the system MUST send an SMS confirmation to the
  caller's phone number within 2 minutes of call completion.
- **FR-021**: The AI voice agent MUST NOT provide medical diagnoses, treatment recommendations, or
  clinical advice.

**Email Confirmation**

- **FR-022**: The system MUST send a booking confirmation email to the patient within 2 minutes of
  appointment creation.
- **FR-023**: The system MUST send an appointment notification email to the doctor within 2 minutes
  of a new booking being created for them.
- **FR-024**: The system MUST send a reminder email to the patient 24 hours before their scheduled
  appointment.

**Appointments API**

- **FR-025**: Authenticated doctors MUST be able to retrieve a list of all their appointments.
- **FR-026**: Authenticated doctors MUST be able to retrieve the full details of a single appointment
  by ID.
- **FR-027**: Authenticated doctors MUST be able to cancel or update the status of an appointment.
- **FR-028**: A dashboard statistics endpoint MUST return: today's appointment count, total unique
  patient count, and a list of the most recent bookings.

**Frontend**

- **FR-029**: The login page MUST store the doctor's access token client-side and redirect to the
  dashboard upon successful authentication.
- **FR-030**: The signup page MUST submit doctor registration data and display confirmation that a
  verification email has been sent.
- **FR-031**: The forgot-password page MUST submit the doctor's email and display confirmation that
  a reset link has been sent.
- **FR-032**: The dashboard page MUST be accessible only to authenticated doctors, display live
  appointment statistics, and automatically log out the doctor after 15 minutes of inactivity.
- **FR-033**: The appointments page MUST list all appointments with filtering by date and status,
  display patient details per appointment, and allow the doctor to cancel an appointment.

### Key Entities

- **Doctor**: A registered medical professional who uses the dashboard. Key attributes: name, email
  (unique), hashed password, clinic name, phone number, US state, email-verified status, created date.
- **Patient**: A person booking an appointment via SMS or Voice. Key attributes: name, phone number
  (unique identifier for matching), date of birth, insurance carrier, insurance member ID.
- **Appointment**: A booking linking a doctor to a patient at a specific date and time. Key
  attributes: patient reference, doctor reference, scheduled date/time, reason for visit, status
  (scheduled / cancelled / completed), booking channel (SMS / Voice), insurance snapshot.
- **ConversationSession**: The in-progress state of an SMS or Voice booking interaction. Tracks the
  current step of the booking flow and collects interim patient responses. Cleaned up after booking
  is confirmed or abandoned.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A doctor can complete registration, verify their email, and reach the dashboard within
  5 minutes of starting signup.
- **SC-002**: A patient can complete an appointment booking via SMS in 10 or fewer conversational
  exchanges.
- **SC-003**: A patient can complete a full voice booking in under 5 minutes of call duration.
- **SC-004**: Booking confirmation emails and SMS messages reach the patient within 2 minutes of
  appointment creation.
- **SC-005**: 100% of protected pages redirect unauthenticated visitors to the login page without
  exposing any appointment data.
- **SC-006**: A doctor is automatically logged out after 15 minutes of inactivity without any manual
  action required.
- **SC-007**: The dashboard loads and displays accurate statistics within 3 seconds for a doctor with
  up to 100 appointments.
- **SC-008**: 100% of AI responses in SMS and Voice interactions include an explicit AI disclosure
  statement before any patient data is collected.
- **SC-009**: No PHI (patient name, phone number, insurance details) appears in any SMS message body,
  system log entry, or API error response.
- **SC-010**: A cancelled appointment is reflected in the appointments list immediately without
  requiring a page refresh.
