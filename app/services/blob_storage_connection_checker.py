import logging
import time

from app.dtos.connection_status import ConnectionStatus, ServiceConnectionStatusDto
from app.services.blob_storage_client import AzureBlobStorageClient

logger = logging.getLogger(__name__)


class BlobStorageConnectionChecker:
    SERVICE_NAME = "blob_storage"

    def __init__(self, blob_storage: AzureBlobStorageClient) -> None:
        self._blob_storage = blob_storage
        self._started_at: float = 0.0

    def check_connection(self) -> ServiceConnectionStatusDto:
        self._mark_probe_started()
        try:
            return self._probe_blob_storage_connection()
        except Exception as ex:
            return self._build_error_status(ex)

    def _probe_blob_storage_connection(self) -> ServiceConnectionStatusDto:
        self._ensure_container_is_available()
        self._log_blob_storage_connection_succeeded()
        return self._build_ok_status()

    def _mark_probe_started(self) -> None:
        self._started_at = time.perf_counter()

    def _ensure_container_is_available(self) -> None:
        self._blob_storage.ensure_container()

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
        self._log_blob_storage_connection_failed(error)
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

    def _log_blob_storage_connection_succeeded(self) -> None:
        logger.info("Conexión a Blob Storage verificada")

    def _log_blob_storage_connection_failed(self, error: Exception) -> None:
        logger.error("Fallo al verificar la conexión a Blob Storage: %s", error)
