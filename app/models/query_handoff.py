from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Identity, Integer, Unicode, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.query_session import ConversationControllerType


class QueryHandoff(Base):
    __tablename__ = "query_handoffs"

    id: Mapped[int] = mapped_column(Integer, Identity(start=1, increment=1), primary_key=True)
    session_id: Mapped[int] = mapped_column(Integer, ForeignKey("query_sessions.id"), nullable=False)
    from_controller_type: Mapped[ConversationControllerType] = mapped_column(Unicode(50), nullable=False)
    to_controller_type: Mapped[ConversationControllerType] = mapped_column(Unicode(50), nullable=False)
    from_user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    to_user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    initiated_by_user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    reason: Mapped[str | None] = mapped_column(Unicode(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.sysutcdatetime(),
    )

    session: Mapped["QuerySession"] = relationship(back_populates="handoffs")
    from_user: Mapped["User | None"] = relationship(
        back_populates="handoffs_from",
        foreign_keys=[from_user_id],
    )
    to_user: Mapped["User | None"] = relationship(
        back_populates="handoffs_to",
        foreign_keys=[to_user_id],
    )
    initiated_by_user: Mapped["User | None"] = relationship(
        back_populates="initiated_handoffs",
        foreign_keys=[initiated_by_user_id],
    )
