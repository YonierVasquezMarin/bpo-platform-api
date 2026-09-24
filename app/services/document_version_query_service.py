from decimal import Decimal

from app.core.enum_values import enum_value
from app.core.exceptions import DocumentVersionNotFoundError
from app.dtos.document import DocumentChunkDto, DocumentVersionDetailDto, ProcessingExecutionDto
from app.models.chunk import Chunk
from app.models.processing_execution import ProcessingExecution
from app.repositories.document_repository import DocumentRepository


class DocumentVersionQueryService:
    def __init__(self, document_repository: DocumentRepository) -> None:
        self._document_repository = document_repository

    def get_version(self, document_id: int, version_id: int) -> DocumentVersionDetailDto:
        version = self._document_repository.find_version(document_id, version_id)
        if version is None:
            raise DocumentVersionNotFoundError()
        document = self._document_repository.find_document(document_id)
        if document is None:
            raise DocumentVersionNotFoundError()
        chunks = self._document_repository.list_chunks(version_id)
        execution = self._document_repository.latest_execution(version_id)
        return DocumentVersionDetailDto(
            document_id=document.id,
            document_name=document.name,
            document_type=document.document_type,
            version_id=version.id,
            version_number=version.version_number,
            file_name=version.file_name,
            file_type=version.file_type,
            status=enum_value(version.status),
            overall_confidence=self._to_float(version.overall_confidence),
            processed_at=version.processed_at,
            approved_at=version.approved_at,
            indexed_at=version.indexed_at,
            chunks=[self._build_chunk_dto(chunk) for chunk in chunks],
            latest_execution=self._build_execution_dto(execution),
        )

    def _build_chunk_dto(self, chunk: Chunk) -> DocumentChunkDto:
        interpretation = None
        if chunk.current_interpretation_id is not None:
            stored = self._document_repository.find_interpretation(chunk.current_interpretation_id)
            if stored is not None:
                interpretation = stored.interpretation
        return DocumentChunkDto(
            id=chunk.id,
            chunk_number=chunk.chunk_number,
            section_title=chunk.section_title,
            page_number=chunk.page_number,
            content_type=chunk.content_type,
            content=chunk.content,
            token_count=chunk.token_count,
            confidence=self._to_float(chunk.confidence),
            status=enum_value(chunk.status),
            interpretation=interpretation,
        )

    def _build_execution_dto(self, execution: ProcessingExecution | None) -> ProcessingExecutionDto | None:
        if execution is None:
            return None
        return ProcessingExecutionDto(
            id=execution.id,
            execution_type=enum_value(execution.execution_type),
            status=enum_value(execution.status),
            chunks_processed=execution.chunks_processed,
            chunks_requiring_review=execution.chunks_requiring_review,
            chunks_approved=execution.chunks_approved,
            error_message=execution.error_message,
        )

    def _to_float(self, value: Decimal | None) -> float | None:
        if value is None:
            return None
        return float(value)
