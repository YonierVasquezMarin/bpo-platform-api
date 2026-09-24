from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.core.exceptions import DocumentModelCallError, DocumentVersionNotProcessableError
from app.models.chunk import ChunkStatus
from app.models.document import Document
from app.models.document_version import DocumentVersion, DocumentVersionStatus
from app.models.processing_execution import ProcessingExecutionStatus
from app.services.chunk_splitter import ChunkSplitter, TokenCounter
from app.services.document_chunking_service import DocumentChunkingService
from app.services.document_indexing_service import DocumentIndexingService
from app.services.document_ingestion_orchestrator import DocumentIngestionOrchestrator
from app.services.document_interpretation_service import DocumentInterpretationService
from app.services.document_text_extractor import DocumentTextExtractor
from app.services.document_version_query_service import DocumentVersionQueryService
from app.services.chunk_interpretation_client import ChunkInterpretationResult
from tests.document_fakes import FixedEmbeddingClient, InMemoryBlobStorage, RecordingSearchClient
from tests.in_memory_document_repository import InMemoryDocumentRepository

_DOCUMENT_TEXT = """# Politica de pagos

El pago se realiza en cinco dias habiles.

# Excepcion ambigua

Este caso queda ambiguo para el operador.
"""


class ScriptedInterpreter:
    def __init__(self, confidence_by_marker: dict[str, Decimal]) -> None:
        self._confidence_by_marker = confidence_by_marker

    def interpret_chunk(self, content: str, section_title: str | None) -> ChunkInterpretationResult:
        confidence = Decimal("0.95")
        for marker, marker_confidence in self._confidence_by_marker.items():
            if marker in content:
                confidence = marker_confidence
        return ChunkInterpretationResult(
            interpretation=f"Interpretación de {section_title or 'fragmento'}",
            structured_content={"summary": content[:40], "topics": ["pagos"]},
            confidence=confidence,
            model_name="gpt-conocimiento",
            prompt_version="v1",
        )


def test_high_confidence_document_is_indexed() -> None:
    repository, version, orchestrator, search = _pipeline({"dias": Decimal("0.95")})

    processed = orchestrator.process_uploaded_version(version.id)

    assert processed.status == DocumentVersionStatus.INDEXED
    chunks = repository.list_chunks(version.id)
    assert len(chunks) == 2
    assert all(chunk.status == ChunkStatus.INDEXED for chunk in chunks)
    assert chunks[0].ai_search_document_id == f"chunk-{chunks[0].id}"
    assert search.documents[0].section_title == "Politica de pagos"
    detail = DocumentVersionQueryService(repository).get_version(version.document_id, version.id)
    assert detail.status == "INDEXED"
    assert detail.overall_confidence == 0.95
    assert detail.chunks[0].interpretation.startswith("Interpretación")
    assert detail.latest_execution.status == ProcessingExecutionStatus.COMPLETED.value


def test_low_confidence_waits_for_human_review_and_does_not_index() -> None:
    repository, version, orchestrator, search = _pipeline({"ambiguo": Decimal("0.42"), "dias": Decimal("0.91")})

    processed = orchestrator.process_uploaded_version(version.id)

    assert processed.status == DocumentVersionStatus.WAITING_HUMAN_REVIEW
    chunks = repository.list_chunks(version.id)
    assert [chunk.status for chunk in chunks] == [ChunkStatus.INTERPRETED, ChunkStatus.NEEDS_REVIEW]
    assert search.documents == []
    execution = repository.latest_execution(version.id)
    assert execution.chunks_requiring_review == 1
    assert execution.chunks_approved == 0


def test_model_failure_marks_the_version_as_failed() -> None:
    repository, version, orchestrator, _search = _pipeline({})
    orchestrator._interpretation_service._interpretation_client.interpret_chunk = _raise_model_error

    processed = orchestrator.process_uploaded_version(version.id)

    assert processed.status == DocumentVersionStatus.FAILED
    execution = repository.latest_execution(version.id)
    assert execution.status == ProcessingExecutionStatus.FAILED
    assert "DocumentModelCallError" in execution.error_message


def test_indexing_failure_keeps_the_version_approved() -> None:
    repository, version, orchestrator, search = _pipeline({"dias": Decimal("0.95")})
    search.upsert_document = _raise_search_error

    processed = orchestrator.process_uploaded_version(version.id)

    assert processed.status == DocumentVersionStatus.APPROVED
    execution = repository.latest_execution(version.id)
    assert execution.execution_type.value == "INDEXING" or str(execution.execution_type) == "INDEXING"
    assert execution.status == ProcessingExecutionStatus.FAILED


def test_approved_version_can_be_indexed_again() -> None:
    repository, version, orchestrator, _search = _pipeline({"dias": Decimal("0.95")})
    orchestrator.process_uploaded_version(version.id)
    version.status = DocumentVersionStatus.APPROVED
    for chunk in repository.list_chunks(version.id):
        chunk.status = ChunkStatus.APPROVED

    indexed = orchestrator.index_approved_version(version.id)

    assert indexed.status == DocumentVersionStatus.INDEXED


def test_waiting_version_cannot_be_processed_again() -> None:
    _repository, version, orchestrator, _search = _pipeline({"ambiguo": Decimal("0.20")})
    orchestrator.process_uploaded_version(version.id)

    with pytest.raises(DocumentVersionNotProcessableError):
        orchestrator.process_uploaded_version(version.id)


def _pipeline(confidence_by_marker: dict[str, Decimal]):
    repository = InMemoryDocumentRepository()
    blob_storage = InMemoryBlobStorage()
    version = _seed_version(repository, blob_storage)
    search = RecordingSearchClient()
    orchestrator = DocumentIngestionOrchestrator(
        document_repository=repository,
        chunking_service=DocumentChunkingService(
            document_repository=repository,
            blob_storage=blob_storage,
            text_extractor=DocumentTextExtractor(),
            chunk_splitter=ChunkSplitter(TokenCounter(), max_tokens=800, overlap_tokens=80),
        ),
        interpretation_service=DocumentInterpretationService(
            document_repository=repository,
            interpretation_client=ScriptedInterpreter(confidence_by_marker),
            confidence_threshold=Decimal("0.80"),
            prompt_version="v1",
        ),
        indexing_service=DocumentIndexingService(
            embedding_client=FixedEmbeddingClient(),
            search_client=search,
        ),
    )
    return repository, version, orchestrator, search


def _seed_version(repository: InMemoryDocumentRepository, blob_storage: InMemoryBlobStorage) -> DocumentVersion:
    document = Document(name="Politica", document_type="TXT", is_active=True)
    repository.add_document(document)
    content = _DOCUMENT_TEXT.encode("utf-8")
    version = DocumentVersion(
        document_id=document.id,
        version_number=1,
        file_name="politica.txt",
        file_type="txt",
        file_size_bytes=len(content),
        blob_container="documents",
        blob_path="docs/politica.txt",
        checksum="abc",
        status=DocumentVersionStatus.UPLOADED,
        uploaded_at=datetime.now(timezone.utc),
    )
    repository.add_version(version)
    document.current_version_id = version.id
    blob_storage.upload_bytes(version.blob_path, content, "text/plain")
    return version


def _raise_model_error(content: str, section_title: str | None) -> ChunkInterpretationResult:
    raise DocumentModelCallError("No se pudo consultar el modelo de interpretación")


def _raise_search_error(document: object) -> str:
    raise RuntimeError("search no disponible")
