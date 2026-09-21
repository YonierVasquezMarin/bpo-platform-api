from datetime import datetime
from enum import Enum

from sqlalchemy import JSON, DateTime, ForeignKey, Identity, Integer, Unicode, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class QuerySessionStatus(str, Enum):
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"


class ConversationControllerType(str, Enum):
    AI_AGENT = "AI_AGENT"
    HUMAN_AGENT = "HUMAN_AGENT"


class QuerySession(Base):
    __tablename__ = "query_sessions"

    id: Mapped[int] = mapped_column(Integer, Identity(start=1, increment=1), primary_key=True)
    user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.sysutcdatetime(),
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[QuerySessionStatus] = mapped_column(
        Unicode(50),
        nullable=False,
        server_default=text("'ACTIVE'"),
    )
    controller_type: Mapped[ConversationControllerType] = mapped_column(
        Unicode(50),
        nullable=False,
        server_default=text("'AI_AGENT'"),
    )
    controller_user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    session_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    user: Mapped["User | None"] = relationship(
        back_populates="query_sessions",
        foreign_keys=[user_id],
    )
    controller_user: Mapped["User | None"] = relationship(
        back_populates="controlled_query_sessions",
        foreign_keys=[controller_user_id],
    )
    messages: Mapped[list["QueryMessage"]] = relationship(back_populates="session")
    handoffs: Mapped[list["QueryHandoff"]] = relationship(back_populates="session")
