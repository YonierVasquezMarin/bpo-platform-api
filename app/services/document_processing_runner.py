import logging
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.exceptions import DocumentVersionNotFoundError, DocumentVersionNotProcessableError
from app.repositories.document_repository import DocumentRepository
from app.services.blob_storage_client import build_blob_storage_client
from app.services.chunk_interpretation_client import build_chunk_interpretation_client
from app.services.chunk_splitter import ChunkSplitter, TokenCounter
from app.services.document_chunking_service import DocumentChunkingService
from app.services.document_indexing_service import DocumentIndexingService
from app.services.document_ingestion_orchestrator import DocumentIngestionOrchestrator
from app.services.document_interpretation_service import DocumentInterpretationService
from app.services.document_text_extractor import DocumentTextExtractor
from app.services.embedding_client import build_embedding_client
from app.services.knowledge_search_client import build_knowledge_search_client

logger = logging.getLogger(__name__)


def process_document_version(version_id: int) -> None:
    _run_background_task(version_id, "procesamiento", _process)


def index_document_version(version_id: int) -> None:
    _run_background_task(version_id, "indexación", _index)


def build_document_ingestion_orchestrator(db: Session) -> DocumentIngestionOrchestrator:
    repository = DocumentRepository(db)
    return DocumentIngestionOrchestrator(
        document_repository=repository,
        chunking_service=DocumentChunkingService(
            document_repository=repository,
            blob_storage=build_blob_storage_client(),
            text_extractor=DocumentTextExtractor(),
            chunk_splitter=_build_chunk_splitter(),
        ),
        interpretation_service=DocumentInterpretationService(
            document_repository=repository,
            interpretation_client=build_chunk_interpretation_client(),
            confidence_threshold=_confidence_threshold(),
            prompt_version=settings.interpretation_prompt_version,
        ),
        indexing_service=DocumentIndexingService(
            embedding_client=build_embedding_client(),
            search_client=build_knowledge_search_client(),
        ),
    )


def _run_background_task(version_id: int, task_name: str, action) -> None:
    _log_background_task_started(task_name, version_id)
    db = SessionLocal()
    try:
        action(db, version_id)
    except (DocumentVersionNotFoundError, DocumentVersionNotProcessableError):
        _log_background_task_skipped(task_name, version_id)
    except Exception:
        _log_background_task_failed(task_name, version_id)
    finally:
        db.close()


def _log_background_task_started(task_name: str, version_id: int) -> None:
    logger.info("Iniciando tarea de %s para la versión %s", task_name, version_id)


def _log_background_task_skipped(task_name: str, version_id: int) -> None:
    logger.info("La versión %s no admite la tarea de %s", version_id, task_name)


def _log_background_task_failed(task_name: str, version_id: int) -> None:
    logger.exception("Falló la tarea de %s de la versión %s", task_name, version_id)


def _process(db: Session, version_id: int) -> None:
    build_document_ingestion_orchestrator(db).process_uploaded_version(version_id)


def _index(db: Session, version_id: int) -> None:
    build_document_ingestion_orchestrator(db).index_approved_version(version_id)


def _build_chunk_splitter() -> ChunkSplitter:
    return ChunkSplitter(
        token_counter=TokenCounter(),
        max_tokens=settings.chunk_max_tokens,
        overlap_tokens=settings.chunk_overlap_tokens,
    )


def _confidence_threshold() -> Decimal:
    return Decimal(str(settings.confidence_threshold)).quantize(Decimal("0.01"))
