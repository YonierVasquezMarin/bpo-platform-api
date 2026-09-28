import logging

from app.core.exceptions import DocumentTextExtractionError, EmptyDocumentError
from app.models.chunk import Chunk, ChunkStatus
from app.models.document_version import DocumentVersion
from app.repositories.document_repository import DocumentRepository
from app.services.blob_storage_client import AzureBlobStorageClient
from app.services.chunk_splitter import ChunkSplitter
from app.services.document_text import ExtractedSection, TextChunkDraft
from app.services.document_text_extractor import DocumentTextExtractor

logger = logging.getLogger(__name__)


class DocumentChunkingService:
    def __init__(
        self,
        document_repository: DocumentRepository,
        blob_storage: AzureBlobStorageClient,
        text_extractor: DocumentTextExtractor,
        chunk_splitter: ChunkSplitter,
    ) -> None:
        self._document_repository = document_repository
        self._blob_storage = blob_storage
        self._text_extractor = text_extractor
        self._chunk_splitter = chunk_splitter
        self._version: DocumentVersion | None = None

    def create_chunks(self, version: DocumentVersion) -> list[Chunk]:
        self._version = version
        self._log_chunking_started()
        self._document_repository.delete_chunks_for_version(version.id)
        drafts = self._build_drafts()
        self._ensure_drafts_exist(drafts)
        chunks = [self._store_chunk(draft) for draft in drafts]
        self._log_chunking_completed(len(chunks))
        return chunks

    def _build_drafts(self) -> list[TextChunkDraft]:
        content = self._download_blob()
        sections = self._extract_sections(content)
        return self._chunk_splitter.split(sections)

    def _download_blob(self) -> bytes:
        self._log_blob_download_started()
        try:
            content = self._blob_storage.download_bytes(self._version.blob_path)
        except Exception as error:
            self._log_blob_download_failed(error)
            raise
        self._log_blob_downloaded(len(content))
        return content

    def _extract_sections(self, content: bytes) -> list[ExtractedSection]:
        sections = self._text_extractor.extract(self._version.file_name, content)
        if not sections:
            self._log_document_without_sections()
            raise DocumentTextExtractionError("El documento no tiene secciones con texto")
        self._log_sections_ready(len(sections))
        return sections

    def _ensure_drafts_exist(self, drafts: list[TextChunkDraft]) -> None:
        if drafts:
            return
        self._log_chunking_produced_no_chunks()
        raise EmptyDocumentError()

    def _store_chunk(self, draft: TextChunkDraft) -> Chunk:
        chunk = Chunk(
            document_version_id=self._version.id,
            chunk_number=draft.chunk_number,
            content=draft.content,
            section_title=draft.section_title,
            page_number=draft.page_number,
            content_type=draft.content_type,
            token_count=draft.token_count,
            status=ChunkStatus.CREATED,
        )
        return self._document_repository.add_chunk(chunk)

    def _log_chunking_started(self) -> None:
        logger.info("Creando chunks de la versión %s", self._version.id)

    def _log_blob_download_started(self) -> None:
        logger.info("Descargando el blob de la versión %s", self._version.id)

    def _log_blob_downloaded(self, size_bytes: int) -> None:
        logger.info("Blob de la versión %s descargado (%s bytes)", self._version.id, size_bytes)

    def _log_blob_download_failed(self, error: Exception) -> None:
        logger.exception("Falló la descarga del blob de la versión %s: %s", self._version.id, error)

    def _log_document_without_sections(self) -> None:
        logger.warning("La versión %s no tiene secciones con texto", self._version.id)

    def _log_sections_ready(self, section_count: int) -> None:
        logger.info("La versión %s tiene %s secciones para dividir", self._version.id, section_count)

    def _log_chunking_produced_no_chunks(self) -> None:
        logger.warning("La versión %s no produjo chunks", self._version.id)

    def _log_chunking_completed(self, chunk_count: int) -> None:
        logger.info("Se crearon %s chunks para la versión %s", chunk_count, self._version.id)
