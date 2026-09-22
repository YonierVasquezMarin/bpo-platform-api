import logging
import time

from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.dtos.connection_status import ConnectionStatus, ServiceConnectionStatusDto

logger = logging.getLogger(__name__)


class DatabaseConnectionChecker:
    SERVICE_NAME = "database"

    def __init__(self, engine: Engine) -> None:
        self._engine = engine
        self._started_at: float = 0.0

    def check_connection(self) -> ServiceConnectionStatusDto:
        self._mark_probe_started()
        try:
            return self._probe_database_connection()
        except Exception as ex:
            return self._build_error_status(ex)

    def _probe_database_connection(self) -> ServiceConnectionStatusDto:
        self._execute_connectivity_query()
        self._log_database_connection_succeeded()
        return self._build_ok_status()

    def _mark_probe_started(self) -> None:
        self._started_at = time.perf_counter()

    def _execute_connectivity_query(self) -> None:
        with self._engine.connect() as connection:
            connection.execute(text("SELECT 1"))

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
        self._log_database_connection_failed(error)
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

    def _log_database_connection_succeeded(self) -> None:
        logger.info("Conexión a la base de datos verificada")

    def _log_database_connection_failed(self, error: Exception) -> None:
        logger.error("Fallo al verificar la conexión a la base de datos: %s", error)
