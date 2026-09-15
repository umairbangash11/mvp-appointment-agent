import uuid
import enum
from datetime import datetime
from sqlalchemy import DateTime, Enum, String, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from models.base import Base


class SessionChannel(str, enum.Enum):
    whatsapp = "whatsapp"


class ConversationSession(Base):
    __tablename__ = "conversation_sessions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    phone_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    channel: Mapped[SessionChannel] = mapped_column(Enum(SessionChannel), nullable=False)
    current_step: Mapped[str] = mapped_column(String(50), nullable=False, default="greeting")
    collected_data: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
