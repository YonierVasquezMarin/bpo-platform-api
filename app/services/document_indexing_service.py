import logging
from datetime import datetime, timezone

from app.core.enum_values import enum_value
from app.core.exceptions import DocumentVersionNotProcessableError
from app.models.chunk import Chunk, ChunkStatus
from app.models.document_version import DocumentVersion, DocumentVersionStatus
from app.services.embedding_client import AzureEmbeddingClient
from app.services.knowledge_search_client import AzureKnowledgeSearchClient, KnowledgeSearchDocument

logger = logging.getLogger(__name__)


class DocumentIndexingService:
    def __init__(
        self,
        embedding_client: AzureEmbeddingClient,
        search_client: AzureKnowledgeSearchClient,
    ) -> None:
        self._embedding_client = embedding_client
        self._search_client = search_client
        self._version: DocumentVersion | None = None

    def index_approved_chunks(self, version: DocumentVersion, chunks: list[Chunk]) -> int:
        self._version = version
        approved_chunks = self._approved_chunks(chunks)
        self._ensure_there_are_chunks_to_index(approved_chunks)
        for chunk in approved_chunks:
            self._index_chunk(chunk)
        self._mark_version_indexed()
        return len(approved_chunks)

    def _approved_chunks(self, chunks: list[Chunk]) -> list[Chunk]:
        return [chunk for chunk in chunks if enum_value(chunk.status) == ChunkStatus.APPROVED.value]

    def _ensure_there_are_chunks_to_index(self, chunks: list[Chunk]) -> None:
        if chunks:
            return
        self._log_indexing_without_chunks()
        raise DocumentVersionNotProcessableError()

    def _index_chunk(self, chunk: Chunk) -> None:
        self._log_chunk_indexing_started(chunk)
        vector = self._embedding_client.create_embedding(chunk.content)
        document_key = self._search_client.upsert_document(self._build_search_document(chunk, vector))
        chunk.ai_search_document_id = document_key
        chunk.status = ChunkStatus.INDEXED
        chunk.indexed_at = datetime.now(timezone.utc)
        self._log_chunk_indexed(chunk, document_key)

    def _build_search_document(self, chunk: Chunk, vector: list[float]) -> KnowledgeSearchDocument:
        return KnowledgeSearchDocument(
            document_key=f"chunk-{chunk.id}",
            content=chunk.content,
            section_title=chunk.section_title or "",
            document_id=self._version.document_id,
            document_version_id=self._version.id,
            chunk_number=chunk.chunk_number,
            page_number=chunk.page_number,
            content_vector=vector,
        )

    def _mark_version_indexed(self) -> None:
        self._version.status = DocumentVersionStatus.INDEXED
        self._version.indexed_at = datetime.now(timezone.utc)

    def _log_indexing_without_chunks(self) -> None:
        logger.warning("La versión %s no tiene chunks aprobados para indexar", self._version.id)

    def _log_chunk_indexing_started(self, chunk: Chunk) -> None:
        logger.info("Indexando el chunk %s de la versión %s", chunk.id, self._version.id)

    def _log_chunk_indexed(self, chunk: Chunk, document_key: str) -> None:
        logger.info(
            "Chunk %s de la versión %s indexado como %s",
            chunk.id,
            self._version.id,
            document_key,
        )
