from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, ForeignKey, Identity, Integer, Unicode, func
from sqlalchemy.dialects.mssql import NVARCHAR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class HumanFeedbackAction(str, Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    CORRECT = "CORRECT"


class HumanFeedback(Base):
    __tablename__ = "human_feedbacks"

    id: Mapped[int] = mapped_column(Integer, Identity(start=1, increment=1), primary_key=True)
    document_version_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("document_versions.id"),
        nullable=False,
    )
    chunk_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("chunks.id"), nullable=True)
    action: Mapped[HumanFeedbackAction] = mapped_column(Unicode(50), nullable=False)
    feedback_text: Mapped[str | None] = mapped_column(NVARCHAR(None), nullable=True)
    previous_interpretation_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("chunk_interpretations.id"),
        nullable=True,
    )
    created_by_user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.sysutcdatetime(),
    )

    document_version: Mapped["DocumentVersion"] = relationship(back_populates="human_feedbacks")
    chunk: Mapped["Chunk | None"] = relationship(back_populates="human_feedbacks")
    previous_interpretation: Mapped["ChunkInterpretation | None"] = relationship(
        foreign_keys=[previous_interpretation_id],
    )
    created_by_user: Mapped["User"] = relationship(
        back_populates="created_human_feedbacks",
        foreign_keys=[created_by_user_id],
    )
