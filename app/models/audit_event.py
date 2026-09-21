from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Identity, Index, Integer, Unicode, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class AuditEvent(Base):
    __tablename__ = "audit_events"
    __table_args__ = (
        Index("ix_audit_events_entity_type_entity_id", "entity_type", "entity_id"),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(start=1, increment=1), primary_key=True)
    entity_type: Mapped[str] = mapped_column(Unicode(50), nullable=False)
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(Unicode(50), nullable=False)
    actor_type: Mapped[str] = mapped_column(Unicode(50), nullable=False)
    actor_user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    event_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.sysutcdatetime(),
    )

    actor_user: Mapped["User | None"] = relationship(
        back_populates="audit_events",
        foreign_keys=[actor_user_id],
    )
