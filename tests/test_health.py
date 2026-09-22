from collections.abc import Iterator
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_connection_status_service
from app.dtos.connection_status import (
    ConnectionStatus,
    ConnectionStatusResponseDto,
    OverallConnectionStatus,
    ServiceConnectionStatusDto,
)
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_dependency_overrides() -> Iterator[None]:
    yield
    app.dependency_overrides.clear()


def test_health_returns_ok() -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["service"] == "bpo-platform-api"
    assert payload["version"] == "0.1.0"


def test_health_connections_returns_ok_when_services_are_up() -> None:
    connection_status_service = MagicMock()
    connection_status_service.get_status.return_value = ConnectionStatusResponseDto(
        status=OverallConnectionStatus.OK,
        services=[
            ServiceConnectionStatusDto(
                name="database",
                status=ConnectionStatus.OK,
                latency_ms=4.2,
                message="Conexión establecida",
            )
        ],
    )
    app.dependency_overrides[get_connection_status_service] = lambda: connection_status_service

    response = client.get("/api/health/connections")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["services"][0]["name"] == "database"
    assert payload["services"][0]["status"] == "ok"
    assert payload["services"][0]["message"] == "Conexión establecida"


def test_health_connections_returns_503_when_services_are_down() -> None:
    connection_status_service = MagicMock()
    connection_status_service.get_status.return_value = ConnectionStatusResponseDto(
        status=OverallConnectionStatus.ERROR,
        services=[
            ServiceConnectionStatusDto(
                name="database",
                status=ConnectionStatus.ERROR,
                latency_ms=12.0,
                message="No se pudo establecer la conexión",
            )
        ],
    )
    app.dependency_overrides[get_connection_status_service] = lambda: connection_status_service

    response = client.get("/api/health/connections")

    assert response.status_code == 503
    payload = response.json()
    assert payload["status"] == "error"
    assert payload["services"][0]["status"] == "error"
