import logging
import time
from urllib.parse import urlsplit

from openai import AzureOpenAI

from app.core.exceptions import DocumentIntelligenceNotConfiguredError, DocumentModelCallError
from app.dtos.connection_status import ConnectionStatus, ServiceConnectionStatusDto

logger = logging.getLogger(__name__)

_PROBE_TIMEOUT_SECONDS = 10


class AzureOpenAiConnectionChecker:
    SERVICE_NAME = "azure_openai"

    def __init__(
        self,
        endpoint: str,
        api_key: str,
        api_version: str,
        chat_deployment: str,
        embedding_deployment: str,
    ) -> None:
        self._endpoint = endpoint
        self._api_key = api_key
        self._api_version = api_version
        self._chat_deployment = chat_deployment
        self._embedding_deployment = embedding_deployment
        self._started_at: float = 0.0

    def check_connection(self) -> ServiceConnectionStatusDto:
        self._mark_probe_started()
        try:
            return self._probe_azure_openai_connection()
        except Exception as ex:
            return self._build_error_status(ex)

    def _probe_azure_openai_connection(self) -> ServiceConnectionStatusDto:
        self._ensure_configured()
        self._ensure_models_are_available()
        self._log_azure_openai_connection_succeeded()
        return self._build_ok_status()

    def _mark_probe_started(self) -> None:
        self._started_at = time.perf_counter()

    def _ensure_configured(self) -> None:
        configuration_is_complete = self._configuration_is_complete()
        if not configuration_is_complete:
            raise DocumentIntelligenceNotConfiguredError("Azure OpenAI no está configurado")

    def _configuration_is_complete(self) -> bool:
        endpoint_is_present = bool(self._endpoint.strip())
        api_key_is_present = bool(self._api_key.strip())
        chat_deployment_is_present = bool(self._chat_deployment.strip())
        embedding_deployment_is_present = bool(self._embedding_deployment.strip())
        configuration_is_complete = (
            endpoint_is_present
            and api_key_is_present
            and chat_deployment_is_present
            and embedding_deployment_is_present
        )
        return configuration_is_complete

    def _ensure_models_are_available(self) -> None:
        model_ids = self._list_model_ids()
        if model_ids:
            return
        raise DocumentModelCallError("Azure OpenAI no devolvió modelos")

    def _list_model_ids(self) -> list[str]:
        models = self._client().models.list()
        return [model.id for model in models if model.id]

    def _client(self) -> AzureOpenAI:
        return AzureOpenAI(
            api_key=self._api_key,
            api_version=self._api_version,
            azure_endpoint=self._azure_resource_endpoint(),
            timeout=_PROBE_TIMEOUT_SECONDS,
            max_retries=0,
        )

    def _azure_resource_endpoint(self) -> str:
        parsed = urlsplit(self._endpoint.strip())
        return f"{parsed.scheme}://{parsed.netloc}"

    def _build_ok_status(self) -> ServiceConnectionStatusDto:
        latency_ms = self._measure_latency_ms()
        message = self._ok_message()
        return ServiceConnectionStatusDto(
            latency_ms=latency_ms,
            message=message,
            status=ConnectionStatus.OK,
            name=self.SERVICE_NAME,
        )

    def _build_error_status(self, error: Exception) -> ServiceConnectionStatusDto:
        self._log_azure_openai_connection_failed(error)
        latency_ms = self._measure_latency_ms()
        message = self._error_message()
        return ServiceConnectionStatusDto(
            latency_ms=latency_ms,
            message=message,
            status=ConnectionStatus.ERROR,
            name=self.SERVICE_NAME,
        )

    def _measure_latency_ms(self) -> float:
        elapsed_seconds = time.perf_counter() - self._started_at
        return round(elapsed_seconds * 1000, 2)

    def _ok_message(self) -> str:
        return "Conexión establecida"

    def _error_message(self) -> str:
        return "No se pudo establecer la conexión"

    def _log_azure_openai_connection_succeeded(self) -> None:
        logger.info("Conexión a Azure OpenAI verificada")

    def _log_azure_openai_connection_failed(self, error: Exception) -> None:
        logger.error("Fallo al verificar la conexión a Azure OpenAI: %s", error)
