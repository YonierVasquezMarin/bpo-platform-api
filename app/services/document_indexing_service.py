from datetime import datetime, timezone

from app.core.enum_values import enum_value
from app.core.exceptions import DocumentVersionNotProcessableError
from app.models.chunk import Chunk, ChunkStatus
from app.models.document_version import DocumentVersion, DocumentVersionStatus
from app.services.embedding_client import AzureEmbeddingClient
from app.services.knowledge_search_client import AzureKnowledgeSearchClient, KnowledgeSearchDocument


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
        if not chunks:
            raise DocumentVersionNotProcessableError()

    def _index_chunk(self, chunk: Chunk) -> None:
        vector = self._embedding_client.create_embedding(chunk.content)
        document_key = self._search_client.upsert_document(self._build_search_document(chunk, vector))
        chunk.ai_search_document_id = document_key
        chunk.status = ChunkStatus.INDEXED
        chunk.indexed_at = datetime.now(timezone.utc)

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
