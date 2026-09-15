import logging
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status

logger = logging.getLogger(__name__)
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import settings
from db.session import get_db
from middleware.auth_middleware import get_current_doctor
from models.doctor import Doctor
from services import auth_service, sendgrid_service

router = APIRouter()


# ── Schemas ────────────────────────────────────────────────────────────────────

class SignupRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    clinic_name: str
    phone: str
    state: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class ProfileUpdateRequest(BaseModel):
    name: str | None = None
    clinic_name: str | None = None
    phone: str | None = None
    state: str | None = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class MessageResponse(BaseModel):
    message: str


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.post("/signup", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def signup(body: SignupRequest, db: AsyncSession = Depends(get_db)):
    logger.info("Signup attempt: %s", body.email)
    existing = await db.execute(select(Doctor).where(Doctor.email == body.email))
    if existing.scalar_one_or_none():
        logger.info("Signup failed (duplicate): %s", body.email)
        raise HTTPException(status_code=400, detail="Email already registered")

    verification_token = auth_service.generate_secure_token()
    is_dev = settings.ENVIRONMENT == "development"
    doctor = Doctor(
        id=uuid.uuid4(),
        name=body.name,
        email=body.email,
        hashed_password=auth_service.hash_password(body.password),
        clinic_name=body.clinic_name,
        phone=body.phone,
        state=body.state,
        is_verified=is_dev,
        email_verification_token=verification_token,
        email_verification_expires=datetime.now(timezone.utc) + timedelta(hours=24),
    )
    db.add(doctor)
    await db.commit()
    if is_dev:
        logger.info("[DEV] Auto-verified signup (ENVIRONMENT=development): %s", body.email)
        return {"message": "Account created and auto-verified (development mode). You can log in now."}

    sendgrid_service.send_verification_email(body.email, verification_token, body.name)
    logger.info("Signup successful: %s (verify token logged below)", body.email)
    logger.info("[DEV] Verify token for %s: %s", body.email, verification_token)
    return {"message": "Account created. Please check your email to verify your account."}


@router.post("/verify-email", response_model=MessageResponse)
async def verify_email(token: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Doctor).where(Doctor.email_verification_token == token))
    doctor = result.scalar_one_or_none()
    if not doctor:
        raise HTTPException(status_code=400, detail="Invalid verification token")
    if doctor.email_verification_expires and doctor.email_verification_expires < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Verification token has expired")

    doctor.is_verified = True
    doctor.email_verification_token = None
    doctor.email_verification_expires = None
    await db.commit()
    return {"message": "Email verified successfully. You can now log in."}


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    logger.info("Login attempt: %s", body.email)
    result = await db.execute(select(Doctor).where(Doctor.email == body.email))
    doctor = result.scalar_one_or_none()
    if not doctor or not auth_service.verify_password(body.password, doctor.hashed_password):
        logger.info("Login failed: %s", body.email)
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not doctor.is_verified:
        logger.info("Login failed (unverified): %s", body.email)
        raise HTTPException(status_code=403, detail="Please verify your email before logging in")

    logger.info("Login successful: %s", body.email)
    token_data = {"sub": str(doctor.id)}
    return TokenResponse(
        access_token=auth_service.create_access_token(token_data),
        refresh_token=auth_service.create_refresh_token(token_data),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    try:
        payload = auth_service.decode_token(body.refresh_token)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")

    token_data = {"sub": payload["sub"]}
    return TokenResponse(
        access_token=auth_service.create_access_token(token_data),
        refresh_token=auth_service.create_refresh_token(token_data),
    )


@router.post("/logout", response_model=MessageResponse)
async def logout(doctor: Doctor = Depends(get_current_doctor)):
    logger.info("Logout: %s", doctor.email)
    return {"message": "Logged out successfully"}


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(body: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Doctor).where(Doctor.email == body.email))
    doctor = result.scalar_one_or_none()
    if doctor:
        reset_token = auth_service.generate_secure_token()
        doctor.reset_password_token = reset_token
        doctor.reset_password_expires = datetime.now(timezone.utc) + timedelta(hours=1)
        await db.commit()
        sendgrid_service.send_password_reset_email(body.email, reset_token, doctor.name)
    return {"message": "If that email is registered, a reset link has been sent."}


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(body: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Doctor).where(Doctor.reset_password_token == body.token))
    doctor = result.scalar_one_or_none()
    if not doctor:
        raise HTTPException(status_code=400, detail="Invalid reset token")
    if doctor.reset_password_expires and doctor.reset_password_expires < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Reset token has expired")

    doctor.hashed_password = auth_service.hash_password(body.new_password)
    doctor.reset_password_token = None
    doctor.reset_password_expires = None
    await db.commit()
    return {"message": "Password updated successfully"}


@router.get("/profile")
async def get_profile(doctor: Doctor = Depends(get_current_doctor)):
    return {
        "id": str(doctor.id),
        "name": doctor.name,
        "email": doctor.email,
        "clinic_name": doctor.clinic_name,
        "phone": doctor.phone,
        "state": doctor.state,
        "is_verified": doctor.is_verified,
    }


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    body: ChangePasswordRequest,
    doctor: Doctor = Depends(get_current_doctor),
    db: AsyncSession = Depends(get_db),
):
    if not auth_service.verify_password(body.current_password, doctor.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    doctor.hashed_password = auth_service.hash_password(body.new_password)
    await db.commit()
    return {"message": "Password changed successfully"}


@router.put("/profile/update", response_model=MessageResponse)
async def update_profile(
    body: ProfileUpdateRequest,
    doctor: Doctor = Depends(get_current_doctor),
    db: AsyncSession = Depends(get_db),
):
    if body.name is not None:
        doctor.name = body.name
    if body.clinic_name is not None:
        doctor.clinic_name = body.clinic_name
    if body.phone is not None:
        doctor.phone = body.phone
    if body.state is not None:
        doctor.state = body.state
    await db.commit()
    return {"message": "Profile updated successfully"}
