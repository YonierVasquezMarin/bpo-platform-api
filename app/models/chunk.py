from datetime import datetime
from decimal import Decimal
from enum import Enum

from sqlalchemy import DateTime, ForeignKey, Identity, Integer, Numeric, Unicode, UniqueConstraint, func, text
from sqlalchemy.dialects.mssql import NVARCHAR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ChunkStatus(str, Enum):
    CREATED = "CREATED"
    INTERPRETED = "INTERPRETED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    INDEXED = "INDEXED"
    FAILED = "FAILED"


class Chunk(Base):
    __tablename__ = "chunks"
    __table_args__ = (
        UniqueConstraint(
            "document_version_id",
            "chunk_number",
            name="uq_chunks_document_version_id_chunk_number",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(start=1, increment=1), primary_key=True)
    document_version_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("document_versions.id"),
        nullable=False,
    )
    chunk_number: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(NVARCHAR(None), nullable=False)
    section_title: Mapped[str | None] = mapped_column(Unicode(500), nullable=True)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    content_type: Mapped[str] = mapped_column(Unicode(50), nullable=False)
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    current_interpretation_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey(
            "chunk_interpretations.id",
            use_alter=True,
            name="fk_chunks_current_interpretation_id_chunk_interpretations",
        ),
        nullable=True,
    )
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    status: Mapped[ChunkStatus] = mapped_column(
        Unicode(50),
        nullable=False,
        server_default=text("'CREATED'"),
    )
    ai_search_document_id: Mapped[str | None] = mapped_column(Unicode(255), nullable=True)
    indexed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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

    document_version: Mapped["DocumentVersion"] = relationship(back_populates="chunks")
    current_interpretation: Mapped["ChunkInterpretation | None"] = relationship(
        foreign_keys=[current_interpretation_id],
        post_update=True,
    )
    interpretations: Mapped[list["ChunkInterpretation"]] = relationship(
        back_populates="chunk",
        foreign_keys="ChunkInterpretation.chunk_id",
    )
    human_feedbacks: Mapped[list["HumanFeedback"]] = relationship(back_populates="chunk")
    query_citations: Mapped[list["QueryCitation"]] = relationship(back_populates="chunk")
