import logging

from app.dtos.connection_status import (
    ConnectionStatus,
    ConnectionStatusResponseDto,
    OverallConnectionStatus,
    ServiceConnectionStatusDto,
)
from app.services.external_service_checker import ExternalServiceChecker

logger = logging.getLogger(__name__)


class ConnectionStatusService:
    def __init__(self, checkers: list[ExternalServiceChecker]) -> None:
        self._checkers = checkers
        self._service_statuses: list[ServiceConnectionStatusDto] = []

    def get_status(self) -> ConnectionStatusResponseDto:
        self._collect_service_statuses()
        self._log_connection_status_checked()
        return self._build_response()

    def _collect_service_statuses(self) -> None:
        self._service_statuses = []
        for checker in self._checkers:
            self._append_service_status(checker)

    def _append_service_status(self, checker: ExternalServiceChecker) -> None:
        service_status = checker.check_connection()
        self._service_statuses.append(service_status)

    def _build_response(self) -> ConnectionStatusResponseDto:
        overall_status = self._resolve_overall_status()
        return ConnectionStatusResponseDto(
            services=self._service_statuses,
            status=overall_status,
        )

    def _resolve_overall_status(self) -> OverallConnectionStatus:
        if self._all_services_are_ok():
            return OverallConnectionStatus.OK
        if self._any_service_is_ok():
            return OverallConnectionStatus.DEGRADED
        return OverallConnectionStatus.ERROR

    def _all_services_are_ok(self) -> bool:
        return all(self._service_is_ok(status) for status in self._service_statuses)

    def _any_service_is_ok(self) -> bool:
        return any(self._service_is_ok(status) for status in self._service_statuses)

    def _service_is_ok(self, service_status: ServiceConnectionStatusDto) -> bool:
        return service_status.status == ConnectionStatus.OK

    def _log_connection_status_checked(self) -> None:
        overall_status = self._resolve_overall_status()
        logger.info("Estado de conexión de servicios externos: %s", overall_status.value)
