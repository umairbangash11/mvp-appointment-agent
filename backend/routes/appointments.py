from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from datetime import datetime, timezone

from db.session import get_db
from middleware.auth_middleware import get_current_doctor
from models.doctor import Doctor
from models.appointment import Appointment, AppointmentStatus

router = APIRouter()


@router.get("")
async def list_appointments(
    db: AsyncSession = Depends(get_db),
    current_doctor: Doctor = Depends(get_current_doctor),  # auth only
):
    result = await db.execute(
        select(Appointment)
        .options(selectinload(Appointment.patient))
        .order_by(Appointment.scheduled_at.desc())
    )
    return [_serialize(a) for a in result.scalars().all()]


@router.get("/stats")
async def dashboard_stats(
    db: AsyncSession = Depends(get_db),
    current_doctor: Doctor = Depends(get_current_doctor),  # auth only
):
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end   = today_start.replace(hour=23, minute=59, second=59)

    today_count = await db.scalar(
        select(func.count(Appointment.id)).where(
            Appointment.scheduled_at >= today_start,
            Appointment.scheduled_at <= today_end,
            Appointment.status == AppointmentStatus.scheduled,
        )
    )
    total_count = await db.scalar(select(func.count(Appointment.id)))
    patient_count = await db.scalar(
        select(func.count(func.distinct(Appointment.patient_id)))
    )
    upcoming_count = await db.scalar(
        select(func.count(Appointment.id)).where(
            Appointment.scheduled_at > now,
            Appointment.status == AppointmentStatus.scheduled,
        )
    )

    recent_result = await db.execute(
        select(Appointment)
        .options(selectinload(Appointment.patient))
        .order_by(Appointment.scheduled_at.desc())
        .limit(5)
    )

    return {
        "today_appointments":    today_count    or 0,
        "total_appointments":    total_count    or 0,
        "total_patients":        patient_count  or 0,
        "upcoming_appointments": upcoming_count or 0,
        "recent_appointments":   [_serialize(a) for a in recent_result.scalars().all()],
    }


@router.get("/{appointment_id}")
async def get_appointment(
    appointment_id: str,
    db: AsyncSession = Depends(get_db),
    current_doctor: Doctor = Depends(get_current_doctor),  # auth only
):
    result = await db.execute(
        select(Appointment)
        .options(selectinload(Appointment.patient))
        .where(Appointment.id == appointment_id)
    )
    appointment = result.scalar_one_or_none()
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return _serialize(appointment)


@router.put("/{appointment_id}/cancel")
async def cancel_appointment(
    appointment_id: str,
    db: AsyncSession = Depends(get_db),
    current_doctor: Doctor = Depends(get_current_doctor),  # auth only
):
    result = await db.execute(
        select(Appointment)
        .options(selectinload(Appointment.patient))
        .where(Appointment.id == appointment_id)
    )
    appointment = result.scalar_one_or_none()
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    if appointment.status == AppointmentStatus.cancelled:
        raise HTTPException(status_code=400, detail="Appointment already cancelled")
    appointment.status = AppointmentStatus.cancelled
    await db.commit()
    return {"message": "Appointment cancelled", "id": str(appointment.id)}


def _serialize(a: Appointment) -> dict:
    branch = ""
    if a.insurance_snapshot and isinstance(a.insurance_snapshot, dict):
        branch = a.insurance_snapshot.get("location", "")
    return {
        "id":               str(a.id),
        "doctor_id":        str(a.doctor_id),
        "patient_id":       str(a.patient_id),
        "patient_name":     a.patient.name if a.patient else "",
        "scheduled_at":     a.scheduled_at.isoformat() if a.scheduled_at else None,
        "duration_minutes": a.duration_minutes,
        "reason_for_visit": a.reason_for_visit or "",
        "branch":           branch,
        "status":           a.status.value if a.status else None,
        "booking_channel":  a.booking_channel.value if a.booking_channel else None,
        "reminder_sent":    a.reminder_sent,
        "created_at":       a.created_at.isoformat() if a.created_at else None,
    }
