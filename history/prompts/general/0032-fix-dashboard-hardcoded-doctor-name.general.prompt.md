---
id: "0032"
title: Fix Dashboard Hardcoded Doctor Name
stage: green
date: 2026-09-16
surface: agent
model: claude-sonnet-4-6
feature: frontend-dashboard
branch: master
user: umairbangash11
command: inline
labels: ["frontend","dashboard","auth","dynamic-data"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - frontend/app/dashboard/layout.tsx
  - frontend/app/dashboard/page.tsx
tests:
  - manual: login as any doctor and verify name/clinic appear in sidebar and greeting
---

## Prompt

Dashboard shows hardcoded "Dr. Wasim" name always.

Fix to show logged in doctor's actual name.

In dashboard page:

1. After login fetch doctor profile:
GET /auth/profile
With auth token.

2. Use response to show:
"Good morning, {doctor.name}"
Not hardcoded "Dr. Wasim"

3. Show correct clinic name in sidebar:
{doctor.clinic_name}
Not hardcoded "Doctor Portal"

4. Fix sidebar doctor name:
Show: {doctor.name}
Show: {doctor.clinic_name}

This way each doctor sees their own name when they login.

## Response snapshot

Updated two files:
- `layout.tsx`: added `useState`/`useEffect`/`authFetch` import; fetch `/auth/profile` on mount; replaced hardcoded "Dr. Wasim" with `{doctor.name || 'Doctor'}` and "Doctor Portal" with `{doctor.clinic_name || 'Doctor Portal'}`.
- `page.tsx`: added `DoctorProfile` interface and `doctor` state; added `/auth/profile` fetch inside `fetchData` alongside stats and appointments; replaced hardcoded greeting with `{doctor.name || 'Doctor'}`; updated avatar initial to use first letter of doctor's name.

## Outcome

- ✅ Impact: Every doctor now sees their own name and clinic in sidebar and greeting after login
- 🧪 Tests: Manual verification required — login as any registered doctor
- 📁 Files: frontend/app/dashboard/layout.tsx, frontend/app/dashboard/page.tsx
- 🔁 Next prompts: None required
- 🧠 Reflection: Simple, minimal change — no extra context or state management needed since both components independently fetch the lightweight profile endpoint

## Evaluation notes (flywheel)

- Failure modes observed: none
- Graders run and results (PASS/FAIL): n/a
- Prompt variant (if applicable): n/a
- Next experiment (smallest change to try): cache profile in localStorage to avoid double fetch between layout and page
