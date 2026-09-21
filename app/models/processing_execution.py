from datetime import datetime
from enum import Enum

from sqlalchemy import JSON, DateTime, ForeignKey, Identity, Integer, Unicode, func, text
from sqlalchemy.dialects.mssql import NVARCHAR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ProcessingExecutionType(str, Enum):
    INITIAL_PROCESSING = "INITIAL_PROCESSING"
    REPROCESSING = "REPROCESSING"
    INDEXING = "INDEXING"


class ProcessingExecutionStatus(str, Enum):
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ProcessingExecution(Base):
    __tablename__ = "processing_executions"

    id: Mapped[int] = mapped_column(Integer, Identity(start=1, increment=1), primary_key=True)
    document_version_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("document_versions.id"),
        nullable=False,
    )
    execution_type: Mapped[ProcessingExecutionType] = mapped_column(Unicode(50), nullable=False)
    status: Mapped[ProcessingExecutionStatus] = mapped_column(
        Unicode(50),
        nullable=False,
        server_default=text("'RUNNING'"),
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.sysutcdatetime(),
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    chunks_processed: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    chunks_requiring_review: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    chunks_approved: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    error_message: Mapped[str | None] = mapped_column(NVARCHAR(None), nullable=True)
    execution_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    document_version: Mapped["DocumentVersion"] = relationship(back_populates="processing_executions")
