from datetime import datetime
from decimal import Decimal

from sqlalchemy import JSON, DateTime, ForeignKey, Identity, Integer, Numeric, Unicode, UniqueConstraint, func
from sqlalchemy.dialects.mssql import NVARCHAR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ChunkInterpretation(Base):
    __tablename__ = "chunk_interpretations"
    __table_args__ = (
        UniqueConstraint(
            "chunk_id",
            "interpretation_version",
            name="uq_chunk_interpretations_chunk_id_interpretation_version",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(start=1, increment=1), primary_key=True)
    chunk_id: Mapped[int] = mapped_column(Integer, ForeignKey("chunks.id"), nullable=False)
    interpretation_version: Mapped[int] = mapped_column(Integer, nullable=False)
    interpretation: Mapped[str] = mapped_column(NVARCHAR(None), nullable=False)
    structured_content: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    confidence: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    model_name: Mapped[str] = mapped_column(Unicode(100), nullable=False)
    prompt_version: Mapped[str | None] = mapped_column(Unicode(50), nullable=True)
    based_on_interpretation_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("chunk_interpretations.id"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.sysutcdatetime(),
    )

    chunk: Mapped["Chunk"] = relationship(
        back_populates="interpretations",
        foreign_keys=[chunk_id],
    )
    based_on_interpretation: Mapped["ChunkInterpretation | None"] = relationship(
        remote_side="ChunkInterpretation.id",
        foreign_keys=[based_on_interpretation_id],
    )
