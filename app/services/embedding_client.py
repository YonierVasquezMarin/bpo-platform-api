import logging

from openai import APIConnectionError, APIStatusError, AuthenticationError, AzureOpenAI

from app.core.config import settings
from app.core.exceptions import DocumentIntelligenceNotConfiguredError, DocumentModelCallError, EmbeddingDimensionError

logger = logging.getLogger(__name__)


class AzureEmbeddingClient:
    def __init__(self, endpoint: str, api_key: str, api_version: str, deployment: str, dimensions: int) -> None:
        self._endpoint = endpoint
        self._api_key = api_key
        self._api_version = api_version
        self._deployment = deployment
        self._dimensions = dimensions

    def create_embedding(self, content: str) -> list[float]:
        self._ensure_configured()
        self._log_embedding_requested()
        vector = self._request_embedding(content)
        self._ensure_dimensions(vector)
        self._log_embedding_completed(len(vector))
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
            self._log_embedding_call_failed(ex)
            raise DocumentModelCallError("No se pudo generar el embedding") from ex
        return list(response.data[0].embedding)

    def _ensure_dimensions(self, vector: list[float]) -> None:
        if len(vector) == self._dimensions:
            return
        self._log_embedding_dimension_mismatch(len(vector))
        raise EmbeddingDimensionError()

    def _log_embedding_requested(self) -> None:
        logger.info("Generando embedding con el modelo %s", self._deployment)

    def _log_embedding_completed(self, dimensions: int) -> None:
        logger.info("Embedding generado con el modelo %s (%s dimensiones)", self._deployment, dimensions)

    def _log_embedding_call_failed(self, error: Exception) -> None:
        logger.exception("Falló la generación del embedding con el modelo %s: %s", self._deployment, error)

    def _log_embedding_dimension_mismatch(self, actual_dimensions: int) -> None:
        logger.error(
            "El embedding del modelo %s tiene %s dimensiones y se esperaban %s",
            self._deployment,
            actual_dimensions,
            self._dimensions,
        )

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
