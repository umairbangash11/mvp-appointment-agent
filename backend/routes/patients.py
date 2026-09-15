from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db
from middleware.auth_middleware import get_current_doctor
from models.doctor import Doctor
from models.patient import Patient

router = APIRouter()


@router.get("")
async def list_patients(
    search: str = Query(default=""),
    db: AsyncSession = Depends(get_db),
    current_doctor: Doctor = Depends(get_current_doctor),  # auth only
):
    query = select(Patient).order_by(Patient.created_at.desc())
    if search.strip():
        query = query.where(Patient.name.ilike(f"%{search.strip()}%"))
    result = await db.execute(query)
    patients = result.scalars().all()
    return [
        {
            "id":         str(p.id),
            "name":       p.name,
            "email":      p.email or "",
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
        for p in patients
    ]
