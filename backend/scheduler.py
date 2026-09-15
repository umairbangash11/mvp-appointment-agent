"""
APScheduler in-process scheduler for appointment reminders.
Runs a reminder job every hour to find appointments 24h away.
"""
import asyncio
from datetime import datetime, timezone, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

_scheduler = AsyncIOScheduler()


def start_scheduler() -> None:
    _scheduler.add_job(
        _send_reminders,
        trigger="interval",
        hours=1,
        id="reminder_job",
        replace_existing=True,
    )
    _scheduler.start()


def stop_scheduler() -> None:
    if _scheduler.running:
        _scheduler.shutdown(wait=False)


async def _send_reminders() -> None:
    from db.session import AsyncSessionLocal
    from models.appointment import Appointment, AppointmentStatus
    from models.patient import Patient
    from models.doctor import Doctor
    from services.sendgrid_service import send_reminder_email
    from config.settings import settings

    now = datetime.now(timezone.utc)
    window_start = now + timedelta(hours=23)
    window_end = now + timedelta(hours=25)

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Appointment).where(
                Appointment.scheduled_at >= window_start,
                Appointment.scheduled_at <= window_end,
                Appointment.status == AppointmentStatus.scheduled,
                Appointment.reminder_sent.is_(False),
            )
        )
        appointments = result.scalars().all()

        for appt in appointments:
            patient_result = await db.execute(select(Patient).where(Patient.id == appt.patient_id))
            patient = patient_result.scalar_one_or_none()
            if not patient or not patient.email:
                appt.reminder_sent = True
                continue

            doctor_result = await db.execute(select(Doctor).where(Doctor.id == appt.doctor_id))
            doctor = doctor_result.scalar_one_or_none()

            slot_str = appt.scheduled_at.strftime("%A %B %d at %I:%M %p") if appt.scheduled_at else "soon"
            await send_reminder_email(
                to_email=patient.email,
                patient_name=patient.name or "Patient",
                appointment_time=slot_str,
                doctor_name=doctor.name if doctor else settings.CLINIC_NAME,
                clinic_name=settings.CLINIC_NAME,
            )
            appt.reminder_sent = True

        await db.commit()
