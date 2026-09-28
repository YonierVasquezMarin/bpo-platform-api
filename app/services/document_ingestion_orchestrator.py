import logging
from datetime import datetime, timezone

from app.core.enum_values import enum_value
from app.core.exceptions import DocumentVersionNotFoundError, DocumentVersionNotProcessableError
from app.models.audit_event import AuditEvent
from app.models.document_version import DocumentVersion, DocumentVersionStatus
from app.models.processing_execution import ProcessingExecution, ProcessingExecutionStatus, ProcessingExecutionType
from app.repositories.document_repository import DocumentRepository
from app.services.document_chunking_service import DocumentChunkingService
from app.services.document_indexing_service import DocumentIndexingService
from app.services.document_interpretation_service import DocumentInterpretationService, InterpretationSummary
from app.services.document_text import PROCESSABLE_VERSION_STATUSES

logger = logging.getLogger(__name__)


class DocumentIngestionOrchestrator:
    def __init__(
        self,
        document_repository: DocumentRepository,
        chunking_service: DocumentChunkingService,
        interpretation_service: DocumentInterpretationService,
        indexing_service: DocumentIndexingService,
    ) -> None:
        self._document_repository = document_repository
        self._chunking_service = chunking_service
        self._interpretation_service = interpretation_service
        self._indexing_service = indexing_service
        self._version_id = 0
        self._version: DocumentVersion | None = None

    def process_uploaded_version(self, version_id: int) -> DocumentVersion:
        self._version_id = version_id
        try:
            return self._execute_processing()
        except (DocumentVersionNotFoundError, DocumentVersionNotProcessableError):
            raise
        except Exception as ex:
            return self._mark_processing_failed(ex)

    def index_approved_version(self, version_id: int) -> DocumentVersion:
        self._version_id = version_id
        self._version = self._require_version()
        if not self._version_is_approved():
            raise DocumentVersionNotProcessableError()
        return self._index_current_version()

    def _execute_processing(self) -> DocumentVersion:
        self._load_version_for_processing()
        if self._version_is_approved():
            self._log_processing_skips_to_indexing()
            return self._index_current_version()
        self._run_initial_processing()
        if self._version_is_approved():
            return self._index_current_version()
        return self._version

    def _load_version_for_processing(self) -> None:
        self._version = self._require_version()
        if enum_value(self._version.status) not in PROCESSABLE_VERSION_STATUSES:
            raise DocumentVersionNotProcessableError()

    def _run_initial_processing(self) -> None:
        if not self._document_repository.claim_version_for_processing(self._version_id):
            raise DocumentVersionNotProcessableError()
        self._version = self._require_version()
        self._log_initial_processing_started()
        execution = self._open_execution(ProcessingExecutionType.INITIAL_PROCESSING)
        chunks = self._chunking_service.create_chunks(self._version)
        self._document_repository.commit()
        summary = self._interpretation_service.interpret_version(self._version, chunks)
        self._complete_execution(execution, summary)
        self._document_repository.commit()
        self._log_initial_processing_completed(summary)

    def _index_current_version(self) -> DocumentVersion:
        try:
            self._execute_indexing()
        except Exception as ex:
            self._mark_indexing_failed(ex)
        self._version = self._require_version()
        return self._version

    def _execute_indexing(self) -> None:
        self._log_indexing_started()
        chunks = self._document_repository.list_chunks(self._version.id)
        execution = self._open_execution(ProcessingExecutionType.INDEXING)
        indexed_count = self._indexing_service.index_approved_chunks(self._version, chunks)
        execution.status = ProcessingExecutionStatus.COMPLETED
        execution.completed_at = datetime.now(timezone.utc)
        execution.chunks_processed = indexed_count
        execution.chunks_approved = indexed_count
        self._add_audit_event("DOCUMENT_INDEXED", "SYSTEM", None, {"indexed_chunks": indexed_count})
        self._document_repository.commit()
        self._log_indexing_completed(indexed_count)

    def _open_execution(self, execution_type: ProcessingExecutionType) -> ProcessingExecution:
        execution = ProcessingExecution(
            document_version_id=self._version.id,
            execution_type=execution_type,
            status=ProcessingExecutionStatus.RUNNING,
            started_at=datetime.now(timezone.utc),
            chunks_processed=0,
            chunks_requiring_review=0,
            chunks_approved=0,
        )
        return self._document_repository.add_execution(execution)

    def _complete_execution(self, execution: ProcessingExecution, summary: InterpretationSummary) -> None:
        execution.status = ProcessingExecutionStatus.COMPLETED
        execution.completed_at = datetime.now(timezone.utc)
        execution.chunks_processed = summary.chunks_processed
        execution.chunks_requiring_review = summary.chunks_requiring_review
        execution.chunks_approved = summary.chunks_approved

    def _mark_processing_failed(self, error: Exception) -> DocumentVersion:
        self._log_processing_failed(error)
        self._document_repository.rollback()
        self._version = self._require_version()
        self._version.status = DocumentVersionStatus.FAILED
        self._fail_running_execution(error)
        self._add_audit_event(
            "DOCUMENT_PROCESSING_FAILED",
            "SYSTEM",
            None,
            {"error": self._trim_error(error)},
        )
        self._document_repository.commit()
        return self._version

    def _mark_indexing_failed(self, error: Exception) -> None:
        self._log_indexing_failed(error)
        self._document_repository.rollback()
        self._version = self._require_version()
        self._document_repository.add_execution(
            ProcessingExecution(
                document_version_id=self._version.id,
                execution_type=ProcessingExecutionType.INDEXING,
                status=ProcessingExecutionStatus.FAILED,
                started_at=datetime.now(timezone.utc),
                completed_at=datetime.now(timezone.utc),
                chunks_processed=0,
                chunks_requiring_review=0,
                chunks_approved=0,
                error_message=self._trim_error(error),
            )
        )
        self._document_repository.commit()

    def _fail_running_execution(self, error: Exception) -> None:
        execution = self._document_repository.latest_execution(self._version_id)
        if execution is not None and enum_value(execution.status) == ProcessingExecutionStatus.RUNNING.value:
            execution.status = ProcessingExecutionStatus.FAILED
            execution.completed_at = datetime.now(timezone.utc)
            execution.error_message = self._trim_error(error)
            return
        self._document_repository.add_execution(
            ProcessingExecution(
                document_version_id=self._version_id,
                execution_type=ProcessingExecutionType.INITIAL_PROCESSING,
                status=ProcessingExecutionStatus.FAILED,
                started_at=datetime.now(timezone.utc),
                completed_at=datetime.now(timezone.utc),
                chunks_processed=0,
                chunks_requiring_review=0,
                chunks_approved=0,
                error_message=self._trim_error(error),
            )
        )

    def _add_audit_event(
        self,
        event_type: str,
        actor_type: str,
        actor_user_id: int | None,
        event_data: dict,
    ) -> None:
        self._document_repository.add_audit_event(
            AuditEvent(
                entity_type="document_version",
                entity_id=self._version.id,
                event_type=event_type,
                actor_type=actor_type,
                actor_user_id=actor_user_id,
                event_data=event_data,
            )
        )

    def _require_version(self) -> DocumentVersion:
        version = self._document_repository.find_version_by_id(self._version_id)
        if version is None:
            raise DocumentVersionNotFoundError()
        return version

    def _version_is_approved(self) -> bool:
        return enum_value(self._version.status) == DocumentVersionStatus.APPROVED.value

    def _trim_error(self, error: Exception) -> str:
        return f"{type(error).__name__}: {error}"[:4000]

    def _log_processing_skips_to_indexing(self) -> None:
        logger.info(
            "La versión %s ya está aprobada. Se omite el procesamiento inicial y se indexa",
            self._version.id,
        )

    def _log_initial_processing_started(self) -> None:
        logger.info("Iniciando procesamiento inicial de la versión %s", self._version.id)

    def _log_initial_processing_completed(self, summary: InterpretationSummary) -> None:
        logger.info(
            "Procesamiento inicial de la versión %s finalizado en estado %s. Chunks: %s, en revisión: %s, aprobados: %s",
            self._version.id,
            enum_value(self._version.status),
            summary.chunks_processed,
            summary.chunks_requiring_review,
            summary.chunks_approved,
        )

    def _log_indexing_started(self) -> None:
        logger.info("Iniciando indexación de la versión %s", self._version.id)

    def _log_indexing_completed(self, indexed_count: int) -> None:
        logger.info("Indexación de la versión %s finalizada con %s chunks", self._version.id, indexed_count)

    def _log_processing_failed(self, error: Exception) -> None:
        logger.exception("Falló el procesamiento de la versión %s: %s", self._version_id, error)

    def _log_indexing_failed(self, error: Exception) -> None:
        logger.exception("Falló la indexación de la versión %s: %s", self._version_id, error)
