from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Identity, Integer, Unicode, func, text
from sqlalchemy.dialects.mssql import NVARCHAR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, Identity(start=1, increment=1), primary_key=True)
    name: Mapped[str] = mapped_column(Unicode(255), nullable=False)
    document_type: Mapped[str] = mapped_column(Unicode(50), nullable=False)
    description: Mapped[str | None] = mapped_column(NVARCHAR(None), nullable=True)
    category: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    source_system: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    current_version_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey(
            "document_versions.id",
            use_alter=True,
            name="fk_documents_current_version_id_document_versions",
        ),
        nullable=True,
    )
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

    versions: Mapped[list["DocumentVersion"]] = relationship(
        back_populates="document",
        foreign_keys="DocumentVersion.document_id",
    )
    current_version: Mapped["DocumentVersion | None"] = relationship(
        foreign_keys=[current_version_id],
        post_update=True,
    )
