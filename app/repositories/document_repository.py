from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from app.models.audit_event import AuditEvent
from app.models.chunk import Chunk
from app.models.chunk_interpretation import ChunkInterpretation
from app.models.document import Document
from app.models.document_version import DocumentVersion, DocumentVersionStatus
from app.models.human_feedback import HumanFeedback
from app.models.processing_execution import ProcessingExecution
from app.models.query_citation import QueryCitation


class DocumentRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def add_document(self, document: Document) -> Document:
        self._db.add(document)
        self._db.flush()
        return document

    def add_version(self, version: DocumentVersion) -> DocumentVersion:
        self._db.add(version)
        self._db.flush()
        return version

    def add_chunk(self, chunk: Chunk) -> Chunk:
        self._db.add(chunk)
        self._db.flush()
        return chunk

    def add_interpretation(self, interpretation: ChunkInterpretation) -> ChunkInterpretation:
        self._db.add(interpretation)
        self._db.flush()
        return interpretation

    def add_execution(self, execution: ProcessingExecution) -> ProcessingExecution:
        self._db.add(execution)
        self._db.flush()
        return execution

    def add_feedback(self, feedback: HumanFeedback) -> HumanFeedback:
        self._db.add(feedback)
        self._db.flush()
        return feedback

    def add_audit_event(self, event: AuditEvent) -> AuditEvent:
        self._db.add(event)
        self._db.flush()
        return event

    def find_document(self, document_id: int) -> Document | None:
        return self._db.get(Document, document_id)

    def find_version(self, document_id: int, version_id: int) -> DocumentVersion | None:
        statement = select(DocumentVersion).where(
            DocumentVersion.id == version_id,
            DocumentVersion.document_id == document_id,
        )
        return self._db.scalar(statement)

    def find_version_by_id(self, version_id: int) -> DocumentVersion | None:
        return self._db.get(DocumentVersion, version_id)

    def find_chunk(self, version_id: int, chunk_id: int) -> Chunk | None:
        statement = select(Chunk).where(
            Chunk.id == chunk_id,
            Chunk.document_version_id == version_id,
        )
        return self._db.scalar(statement)

    def find_interpretation(self, interpretation_id: int) -> ChunkInterpretation | None:
        return self._db.get(ChunkInterpretation, interpretation_id)

    def list_chunks(self, version_id: int) -> list[Chunk]:
        statement = (
            select(Chunk)
            .where(Chunk.document_version_id == version_id)
            .order_by(Chunk.chunk_number)
        )
        return list(self._db.scalars(statement))

    def latest_execution(self, version_id: int) -> ProcessingExecution | None:
        statement = (
            select(ProcessingExecution)
            .where(ProcessingExecution.document_version_id == version_id)
            .order_by(ProcessingExecution.id.desc())
        )
        return self._db.scalars(statement).first()

    def next_interpretation_version(self, chunk_id: int) -> int:
        statement = select(ChunkInterpretation.interpretation_version).where(
            ChunkInterpretation.chunk_id == chunk_id
        )
        versions = list(self._db.scalars(statement))
        if not versions:
            return 1
        return max(versions) + 1

    def delete_chunks_for_version(self, version_id: int) -> None:
        chunk_ids = list(
            self._db.scalars(select(Chunk.id).where(Chunk.document_version_id == version_id))
        )
        if not chunk_ids:
            return
        self._delete_chunk_dependents(chunk_ids)
        self._db.execute(delete(Chunk).where(Chunk.id.in_(chunk_ids)))
        self._db.flush()

    def claim_version_for_processing(self, version_id: int) -> bool:
        statement = (
            update(DocumentVersion)
            .where(
                DocumentVersion.id == version_id,
                DocumentVersion.status.in_(
                    [DocumentVersionStatus.UPLOADED.value, DocumentVersionStatus.FAILED.value]
                ),
            )
            .values(status=DocumentVersionStatus.PROCESSING.value)
        )
        result = self._db.execute(statement)
        claimed = result.rowcount == 1
        self._db.commit()
        self._db.expire_all()
        return claimed

    def commit(self) -> None:
        self._db.commit()

    def rollback(self) -> None:
        self._db.rollback()

    def _delete_chunk_dependents(self, chunk_ids: list[int]) -> None:
        interpretation_ids = list(
            self._db.scalars(
                select(ChunkInterpretation.id).where(ChunkInterpretation.chunk_id.in_(chunk_ids))
            )
        )
        self._db.execute(delete(QueryCitation).where(QueryCitation.chunk_id.in_(chunk_ids)))
        self._db.execute(
            update(Chunk).where(Chunk.id.in_(chunk_ids)).values(current_interpretation_id=None)
        )
        self._delete_feedbacks(chunk_ids, interpretation_ids)
        if interpretation_ids:
            self._db.execute(
                delete(ChunkInterpretation).where(ChunkInterpretation.id.in_(interpretation_ids))
            )

    def _delete_feedbacks(self, chunk_ids: list[int], interpretation_ids: list[int]) -> None:
        statement = delete(HumanFeedback).where(HumanFeedback.chunk_id.in_(chunk_ids))
        if interpretation_ids:
            statement = delete(HumanFeedback).where(
                HumanFeedback.chunk_id.in_(chunk_ids)
                | HumanFeedback.previous_interpretation_id.in_(interpretation_ids)
            )
        self._db.execute(statement)
