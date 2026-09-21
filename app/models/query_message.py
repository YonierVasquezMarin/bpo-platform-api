from datetime import datetime
from decimal import Decimal
from enum import Enum

from sqlalchemy import Boolean, DateTime, ForeignKey, Identity, Integer, Numeric, Unicode, func
from sqlalchemy.dialects.mssql import NVARCHAR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class QueryMessageRole(str, Enum):
    USER = "USER"
    AI_AGENT = "AI_AGENT"
    HUMAN_AGENT = "HUMAN_AGENT"


class AnswerStatus(str, Enum):
    ANSWERED = "ANSWERED"
    INSUFFICIENT_INFORMATION = "INSUFFICIENT_INFORMATION"
    ERROR = "ERROR"


class QueryMessage(Base):
    __tablename__ = "query_messages"

    id: Mapped[int] = mapped_column(Integer, Identity(start=1, increment=1), primary_key=True)
    session_id: Mapped[int] = mapped_column(Integer, ForeignKey("query_sessions.id"), nullable=False)
    role: Mapped[QueryMessageRole] = mapped_column(Unicode(50), nullable=False)
    content: Mapped[str] = mapped_column(NVARCHAR(None), nullable=False)
    sender_user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    search_query: Mapped[str | None] = mapped_column(NVARCHAR(None), nullable=True)
    retrieval_attempt: Mapped[int | None] = mapped_column(Integer, nullable=True)
    context_sufficient: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    answer_status: Mapped[AnswerStatus | None] = mapped_column(Unicode(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.sysutcdatetime(),
    )

    session: Mapped["QuerySession"] = relationship(back_populates="messages")
    sender_user: Mapped["User | None"] = relationship(
        back_populates="sent_query_messages",
        foreign_keys=[sender_user_id],
    )
    citations: Mapped[list["QueryCitation"]] = relationship(back_populates="query_message")
