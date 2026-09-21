from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Identity, Integer, Numeric, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class QueryCitation(Base):
    __tablename__ = "query_citations"
    __table_args__ = (
        UniqueConstraint(
            "query_message_id",
            "citation_order",
            name="uq_query_citations_query_message_id_citation_order",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(start=1, increment=1), primary_key=True)
    query_message_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("query_messages.id"),
        nullable=False,
    )
    chunk_id: Mapped[int] = mapped_column(Integer, ForeignKey("chunks.id"), nullable=False)
    relevance_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    citation_order: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.sysutcdatetime(),
    )

    query_message: Mapped["QueryMessage"] = relationship(back_populates="citations")
    chunk: Mapped["Chunk"] = relationship(back_populates="query_citations")
