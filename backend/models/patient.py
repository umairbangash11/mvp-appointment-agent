import uuid
import hashlib
from sqlalchemy import String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column
from models.base import Base, TimestampMixin


def hash_phone(phone: str) -> str:
    return hashlib.sha256(phone.encode()).hexdigest()


class Patient(Base, TimestampMixin):
    __tablename__ = "patients"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    phone_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    date_of_birth: Mapped[str | None] = mapped_column(Text, nullable=True)
    email: Mapped[str | None] = mapped_column(Text, nullable=True)
    insurance_carrier: Mapped[str | None] = mapped_column(Text, nullable=True)
    insurance_member_id: Mapped[str | None] = mapped_column(Text, nullable=True)
