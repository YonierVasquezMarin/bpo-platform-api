from app.core.enum_values import enum_value
from app.models.audit_event import AuditEvent
from app.models.chunk import Chunk
from app.models.chunk_interpretation import ChunkInterpretation
from app.models.document import Document
from app.models.document_version import DocumentVersion, DocumentVersionStatus
from app.models.human_feedback import HumanFeedback
from app.models.processing_execution import ProcessingExecution


class InMemoryDocumentRepository:
    def __init__(self) -> None:
        self.documents: list[Document] = []
        self.versions: list[DocumentVersion] = []
        self.chunks: list[Chunk] = []
        self.interpretations: list[ChunkInterpretation] = []
        self.executions: list[ProcessingExecution] = []
        self.feedbacks: list[HumanFeedback] = []
        self.audits: list[AuditEvent] = []
        self._next_identifier = 1

    def add_document(self, document: Document) -> Document:
        self._assign_id(document)
        self.documents.append(document)
        return document

    def add_version(self, version: DocumentVersion) -> DocumentVersion:
        self._assign_id(version)
        self.versions.append(version)
        return version

    def add_chunk(self, chunk: Chunk) -> Chunk:
        self._assign_id(chunk)
        self.chunks.append(chunk)
        return chunk

    def add_interpretation(self, interpretation: ChunkInterpretation) -> ChunkInterpretation:
        self._assign_id(interpretation)
        self.interpretations.append(interpretation)
        return interpretation

    def add_execution(self, execution: ProcessingExecution) -> ProcessingExecution:
        self._assign_id(execution)
        self.executions.append(execution)
        return execution

    def add_feedback(self, feedback: HumanFeedback) -> HumanFeedback:
        self._assign_id(feedback)
        self.feedbacks.append(feedback)
        return feedback

    def add_audit_event(self, event: AuditEvent) -> AuditEvent:
        self._assign_id(event)
        self.audits.append(event)
        return event

    def find_document(self, document_id: int) -> Document | None:
        return self._first(self.documents, document_id)

    def find_version(self, document_id: int, version_id: int) -> DocumentVersion | None:
        version = self.find_version_by_id(version_id)
        if version is None or version.document_id != document_id:
            return None
        return version

    def find_version_by_id(self, version_id: int) -> DocumentVersion | None:
        return self._first(self.versions, version_id)

    def find_chunk(self, version_id: int, chunk_id: int) -> Chunk | None:
        for chunk in self.chunks:
            if chunk.id == chunk_id and chunk.document_version_id == version_id:
                return chunk
        return None

    def find_interpretation(self, interpretation_id: int) -> ChunkInterpretation | None:
        return self._first(self.interpretations, interpretation_id)

    def list_chunks(self, version_id: int) -> list[Chunk]:
        chunks = [chunk for chunk in self.chunks if chunk.document_version_id == version_id]
        return sorted(chunks, key=lambda chunk: chunk.chunk_number)

    def latest_execution(self, version_id: int) -> ProcessingExecution | None:
        executions = [
            execution for execution in self.executions if execution.document_version_id == version_id
        ]
        if not executions:
            return None
        return max(executions, key=lambda execution: execution.id)

    def next_interpretation_version(self, chunk_id: int) -> int:
        versions = [
            interpretation.interpretation_version
            for interpretation in self.interpretations
            if interpretation.chunk_id == chunk_id
        ]
        if not versions:
            return 1
        return max(versions) + 1

    def delete_chunks_for_version(self, version_id: int) -> None:
        chunk_ids = {chunk.id for chunk in self.chunks if chunk.document_version_id == version_id}
        self.chunks = [chunk for chunk in self.chunks if chunk.id not in chunk_ids]
        self.interpretations = [
            interpretation for interpretation in self.interpretations if interpretation.chunk_id not in chunk_ids
        ]
        self.feedbacks = [feedback for feedback in self.feedbacks if feedback.chunk_id not in chunk_ids]

    def claim_version_for_processing(self, version_id: int) -> bool:
        version = self.find_version_by_id(version_id)
        if version is None:
            return False
        status_can_be_claimed = enum_value(version.status) in {
            DocumentVersionStatus.UPLOADED.value,
            DocumentVersionStatus.FAILED.value,
        }
        if not status_can_be_claimed:
            return False
        version.status = DocumentVersionStatus.PROCESSING
        return True

    def commit(self) -> None:
        return None

    def rollback(self) -> None:
        return None

    def _assign_id(self, entity: object) -> None:
        if getattr(entity, "id", None) is None:
            entity.id = self._next_identifier
            self._next_identifier += 1

    def _first(self, entities: list, entity_id: int):
        for entity in entities:
            if entity.id == entity_id:
                return entity
        return None
