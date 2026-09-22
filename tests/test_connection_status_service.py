from unittest.mock import MagicMock

from app.dtos.connection_status import (
    ConnectionStatus,
    OverallConnectionStatus,
    ServiceConnectionStatusDto,
)
from app.services.connection_status_service import ConnectionStatusService


def test_connection_status_is_ok_when_all_services_succeed() -> None:
    database_checker = _build_checker("database", ConnectionStatus.OK)
    service = ConnectionStatusService([database_checker])

    payload = service.get_status()

    assert payload.status == OverallConnectionStatus.OK
    assert len(payload.services) == 1
    assert payload.services[0].name == "database"
    assert payload.services[0].status == ConnectionStatus.OK


def test_connection_status_is_error_when_all_services_fail() -> None:
    database_checker = _build_checker("database", ConnectionStatus.ERROR)
    service = ConnectionStatusService([database_checker])

    payload = service.get_status()

    assert payload.status == OverallConnectionStatus.ERROR
    assert payload.services[0].status == ConnectionStatus.ERROR


def test_connection_status_is_degraded_when_some_services_fail() -> None:
    database_checker = _build_checker("database", ConnectionStatus.OK)
    cache_checker = _build_checker("cache", ConnectionStatus.ERROR)
    service = ConnectionStatusService([database_checker, cache_checker])

    payload = service.get_status()

    assert payload.status == OverallConnectionStatus.DEGRADED
    assert [item.name for item in payload.services] == ["database", "cache"]


def _build_checker(name: str, status: ConnectionStatus) -> MagicMock:
    checker = MagicMock()
    checker.check_connection.return_value = ServiceConnectionStatusDto(
        name=name,
        status=status,
        latency_ms=1.0,
        message="estado de prueba",
    )
    return checker
