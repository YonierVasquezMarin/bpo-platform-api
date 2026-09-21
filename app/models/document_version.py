from datetime import datetime
from decimal import Decimal
from enum import Enum

from sqlalchemy import BigInteger, DateTime, ForeignKey, Identity, Integer, Numeric, Unicode, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class DocumentVersionStatus(str, Enum):
    UPLOADED = "UPLOADED"
    PROCESSING = "PROCESSING"
    WAITING_HUMAN_REVIEW = "WAITING_HUMAN_REVIEW"
    REPROCESSING = "REPROCESSING"
    APPROVED = "APPROVED"
    INDEXED = "INDEXED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"
    SUPERSEDED = "SUPERSEDED"


class DocumentVersion(Base):
    __tablename__ = "document_versions"
    __table_args__ = (
        UniqueConstraint(
            "document_id",
            "version_number",
            name="uq_document_versions_document_id_version_number",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(start=1, increment=1), primary_key=True)
    document_id: Mapped[int] = mapped_column(Integer, ForeignKey("documents.id"), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    file_name: Mapped[str] = mapped_column(Unicode(255), nullable=False)
    file_type: Mapped[str] = mapped_column(Unicode(20), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    blob_container: Mapped[str] = mapped_column(Unicode(255), nullable=False)
    blob_path: Mapped[str] = mapped_column(Unicode(1000), nullable=False)
    blob_url: Mapped[str | None] = mapped_column(Unicode(2000), nullable=True)
    checksum: Mapped[str] = mapped_column(Unicode(128), nullable=False)
    status: Mapped[DocumentVersionStatus] = mapped_column(
        Unicode(50),
        nullable=False,
        server_default=text("'UPLOADED'"),
    )
    effective_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    overall_confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.sysutcdatetime(),
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    indexed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    uploaded_by_user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    approved_by_user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.sysutcdatetime(),
    )

    document: Mapped["Document"] = relationship(
        back_populates="versions",
        foreign_keys=[document_id],
    )
    uploaded_by_user: Mapped["User | None"] = relationship(
        back_populates="uploaded_document_versions",
        foreign_keys=[uploaded_by_user_id],
    )
    approved_by_user: Mapped["User | None"] = relationship(
        back_populates="approved_document_versions",
        foreign_keys=[approved_by_user_id],
    )
    chunks: Mapped[list["Chunk"]] = relationship(back_populates="document_version")
    processing_executions: Mapped[list["ProcessingExecution"]] = relationship(back_populates="document_version")
    human_feedbacks: Mapped[list["HumanFeedback"]] = relationship(back_populates="document_version")
