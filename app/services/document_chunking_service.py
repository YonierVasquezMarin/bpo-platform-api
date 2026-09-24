from app.core.exceptions import DocumentTextExtractionError, EmptyDocumentError
from app.models.chunk import Chunk, ChunkStatus
from app.models.document_version import DocumentVersion
from app.repositories.document_repository import DocumentRepository
from app.services.blob_storage_client import AzureBlobStorageClient
from app.services.chunk_splitter import ChunkSplitter
from app.services.document_text import TextChunkDraft
from app.services.document_text_extractor import DocumentTextExtractor


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
        self._document_repository.delete_chunks_for_version(version.id)
        drafts = self._build_drafts()
        self._ensure_drafts_exist(drafts)
        return [self._store_chunk(draft) for draft in drafts]

    def _build_drafts(self) -> list[TextChunkDraft]:
        content = self._blob_storage.download_bytes(self._version.blob_path)
        sections = self._text_extractor.extract(self._version.file_name, content)
        if not sections:
            raise DocumentTextExtractionError("El documento no tiene secciones con texto")
        return self._chunk_splitter.split(sections)

    def _ensure_drafts_exist(self, drafts: list[TextChunkDraft]) -> None:
        if not drafts:
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
