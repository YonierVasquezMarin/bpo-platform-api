from openai import APIConnectionError, APIStatusError, AuthenticationError, AzureOpenAI

from app.core.config import settings
from app.core.exceptions import DocumentIntelligenceNotConfiguredError, DocumentModelCallError, EmbeddingDimensionError


class AzureEmbeddingClient:
    def __init__(self, endpoint: str, api_key: str, api_version: str, deployment: str, dimensions: int) -> None:
        self._endpoint = endpoint
        self._api_key = api_key
        self._api_version = api_version
        self._deployment = deployment
        self._dimensions = dimensions

    def create_embedding(self, content: str) -> list[float]:
        self._ensure_configured()
        vector = self._request_embedding(content)
        self._ensure_dimensions(vector)
        return vector

    def _ensure_configured(self) -> None:
        configuration_is_complete = bool(
            self._endpoint.strip() and self._api_key.strip() and self._deployment.strip()
        )
        if not configuration_is_complete:
            raise DocumentIntelligenceNotConfiguredError("El modelo de embeddings no está configurado")

    def _request_embedding(self, content: str) -> list[float]:
        try:
            response = self._client().embeddings.create(model=self._deployment, input=content)
        except (AuthenticationError, APIConnectionError, APIStatusError) as ex:
            raise DocumentModelCallError("No se pudo generar el embedding") from ex
        return list(response.data[0].embedding)

    def _ensure_dimensions(self, vector: list[float]) -> None:
        if len(vector) != self._dimensions:
            raise EmbeddingDimensionError()

    def _client(self) -> AzureOpenAI:
        return AzureOpenAI(
            api_key=self._api_key,
            api_version=self._api_version,
            azure_endpoint=self._endpoint,
            timeout=60,
        )


def build_embedding_client() -> AzureEmbeddingClient:
    return AzureEmbeddingClient(
        endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key,
        api_version=settings.azure_openai_api_version,
        deployment=settings.azure_openai_embedding_deployment,
        dimensions=settings.azure_openai_embedding_dimensions,
    )
