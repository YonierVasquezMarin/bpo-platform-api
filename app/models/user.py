from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, DateTime, Identity, Index, Integer, Unicode, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class UserRole(str, Enum):
    ADMIN = "ADMIN"
    KNOWLEDGE_MANAGER = "KNOWLEDGE_MANAGER"
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
