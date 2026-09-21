from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, DateTime, Identity, Index, Integer, Unicode, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class UserRole(str, Enum):
    ADMIN = "ADMIN"
    KNOWLEDGE_MANAGER = "KNOWLEDGE_MANAGER"
    SUPPORT = "SUPPORT"
    USER = "USER"


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        Index(
            "uq_users_external_id",
            "external_id",
            unique=True,
            mssql_where=text("[external_id] IS NOT NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(start=1, increment=1), primary_key=True)
    external_id: Mapped[str | None] = mapped_column(Unicode(255), nullable=True)
    email: Mapped[str] = mapped_column(Unicode(255), unique=True, nullable=False)
    password: Mapped[str] = mapped_column(Unicode(255), nullable=False)
    first_name: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    last_name: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    role: Mapped[UserRole] = mapped_column(Unicode(50), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("1"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.sysutcdatetime(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.sysutcdatetime(),
        onupdate=func.sysutcdatetime(),
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    uploaded_document_versions: Mapped[list["DocumentVersion"]] = relationship(
        back_populates="uploaded_by_user",
        foreign_keys="DocumentVersion.uploaded_by_user_id",
    )
    approved_document_versions: Mapped[list["DocumentVersion"]] = relationship(
        back_populates="approved_by_user",
        foreign_keys="DocumentVersion.approved_by_user_id",
    )
    created_human_feedbacks: Mapped[list["HumanFeedback"]] = relationship(
        back_populates="created_by_user",
        foreign_keys="HumanFeedback.created_by_user_id",
    )
    query_sessions: Mapped[list["QuerySession"]] = relationship(
        back_populates="user",
        foreign_keys="QuerySession.user_id",
    )
    controlled_query_sessions: Mapped[list["QuerySession"]] = relationship(
        back_populates="controller_user",
        foreign_keys="QuerySession.controller_user_id",
    )
    sent_query_messages: Mapped[list["QueryMessage"]] = relationship(
        back_populates="sender_user",
        foreign_keys="QueryMessage.sender_user_id",
    )
    initiated_handoffs: Mapped[list["QueryHandoff"]] = relationship(
        back_populates="initiated_by_user",
        foreign_keys="QueryHandoff.initiated_by_user_id",
    )
    handoffs_from: Mapped[list["QueryHandoff"]] = relationship(
        back_populates="from_user",
        foreign_keys="QueryHandoff.from_user_id",
    )
    handoffs_to: Mapped[list["QueryHandoff"]] = relationship(
        back_populates="to_user",
        foreign_keys="QueryHandoff.to_user_id",
    )
    audit_events: Mapped[list["AuditEvent"]] = relationship(
        back_populates="actor_user",
        foreign_keys="AuditEvent.actor_user_id",
    )
