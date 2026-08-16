from typing import List
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), env_file_encoding="utf-8", extra="ignore")

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/appointment_db"

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def ensure_asyncpg_driver(cls, v: str) -> str:
        if v.startswith("postgresql://") or v.startswith("postgres://"):
            return v.replace("://", "+asyncpg://", 1)
        return v

    # JWT
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # PHI Encryption
    ENCRYPTION_KEY: str = ""

    # Groq
    GROQ_API_KEY: str = ""
    GROQ_WHISPER_MODEL: str = "whisper-large-v3"

    # ElevenLabs
    ELEVENLABS_API_KEY: str = ""
    ELEVENLABS_VOICE_ID: str = "21m00Tcm4TlvDq8ikWAM"

    # Twilio
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_WHATSAPP_NUMBER: str = "whatsapp:+14155238886"

    # Meta WhatsApp Cloud API — active inbound/outbound transport for /whatsapp/webhook
    WHATSAPP_VERIFY_TOKEN: str = ""
    WHATSAPP_TOKEN: str = ""
    WHATSAPP_PHONE_NUMBER_ID: str = ""

    # SendGrid
    SENDGRID_API_KEY: str = ""
    SENDGRID_FROM_EMAIL: str = "noreply@clinic.com"
    SENDGRID_FROM_NAME: str = "Medical Clinic"

    # App
    ENVIRONMENT: str = "production"
    FRONTEND_URL: str = "http://localhost:3000"

    # Clinic FAQ (WhatsApp agent)
    CLINIC_NAME: str = "Your Medical Clinic"
    CLINIC_HOURS: str = "Sunday-Thursday 9:00 AM - 6:00 PM (Asia/Dubai)"
    CLINIC_ADDRESS: str = "Dubai, UAE"
    CLINIC_PHONE: str = "+9715XXXXXXX"
    ACCEPTED_INSURANCE: List[str] = ["Daman", "AXA", "MetLife", "Oman Insurance (Sukoon)", "Nextcare"]

    # The verified doctor who owns this clinic's WhatsApp number.
    # WhatsApp-booked appointments are assigned to this doctor.
    # Set to the email used at signup. Leave blank to fall back to the
    # oldest verified doctor in the database.
    CLINIC_DOCTOR_EMAIL: str = ""


settings = Settings()
