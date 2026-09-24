from dataclasses import dataclass

from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import ResourceNotFoundError
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    HnswAlgorithmConfiguration,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SearchableField,
    SimpleField,
    VectorSearch,
    VectorSearchProfile,
)

from app.core.config import settings
from app.core.exceptions import DocumentSearchNotConfiguredError


@dataclass(frozen=True)
class KnowledgeSearchDocument:
    document_key: str
    content: str
    section_title: str
    document_id: int
    document_version_id: int
    chunk_number: int
    page_number: int | None
    content_vector: list[float]


class AzureKnowledgeSearchClient:
    def __init__(self, endpoint: str, api_key: str, index_name: str, vector_dimensions: int) -> None:
        self._endpoint = endpoint
        self._api_key = api_key
        self._index_name = index_name
        self._vector_dimensions = vector_dimensions
        self._index_is_ready = False

    def upsert_document(self, document: KnowledgeSearchDocument) -> str:
        self._ensure_configured()
        self._ensure_index()
        self._search_client().merge_or_upload_documents(documents=[self._payload(document)])
        return document.document_key

    def _ensure_configured(self) -> None:
        configuration_is_complete = bool(self._endpoint.strip() and self._api_key.strip() and self._index_name.strip())
        if not configuration_is_complete:
            raise DocumentSearchNotConfiguredError()

    def _ensure_index(self) -> None:
        if self._index_is_ready:
            return
        index_client = self._index_client()
        try:
            index_client.get_index(self._index_name)
        except ResourceNotFoundError:
            index_client.create_index(self._build_index())
        self._index_is_ready = True

    def _build_index(self) -> SearchIndex:
        return SearchIndex(
            name=self._index_name,
            fields=self._index_fields(),
            vector_search=VectorSearch(
                algorithms=[HnswAlgorithmConfiguration(name="content-hnsw")],
                profiles=[
                    VectorSearchProfile(
                        name="content-vector-profile",
                        algorithm_configuration_name="content-hnsw",
                    )
                ],
            ),
        )

    def _index_fields(self) -> list:
        return [
            SimpleField(name="id", type=SearchFieldDataType.String, key=True, filterable=True),
            SearchableField(name="content", type=SearchFieldDataType.String),
            SearchableField(name="section_title", type=SearchFieldDataType.String),
            SimpleField(name="document_id", type=SearchFieldDataType.Int32, filterable=True),
            SimpleField(name="document_version_id", type=SearchFieldDataType.Int32, filterable=True),
            SimpleField(name="chunk_number", type=SearchFieldDataType.Int32, filterable=True),
            SimpleField(name="page_number", type=SearchFieldDataType.Int32, filterable=True),
            SearchField(
                name="content_vector",
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True,
                vector_search_dimensions=self._vector_dimensions,
                vector_search_profile_name="content-vector-profile",
            ),
        ]

    def _payload(self, document: KnowledgeSearchDocument) -> dict[str, object]:
        return {
            "id": document.document_key,
            "content": document.content,
            "section_title": document.section_title,
            "document_id": document.document_id,
            "document_version_id": document.document_version_id,
            "chunk_number": document.chunk_number,
            "page_number": document.page_number,
            "content_vector": document.content_vector,
        }

    def _search_client(self) -> SearchClient:
        return SearchClient(
            endpoint=self._endpoint,
            index_name=self._index_name,
            credential=AzureKeyCredential(self._api_key),
        )

    def _index_client(self) -> SearchIndexClient:
        return SearchIndexClient(endpoint=self._endpoint, credential=AzureKeyCredential(self._api_key))


def build_knowledge_search_client() -> AzureKnowledgeSearchClient:
    return AzureKnowledgeSearchClient(
        endpoint=settings.azure_search_endpoint,
        api_key=settings.azure_search_api_key,
        index_name=settings.azure_search_index_name,
        vector_dimensions=settings.azure_openai_embedding_dimensions,
    )
