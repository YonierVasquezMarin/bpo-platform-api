from collections.abc import Iterator
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_auth_service
from app.core.exceptions import InactiveUserError, InvalidCredentialsError
from app.dtos.auth import AuthenticatedUserDto, LoginResponseDto
from app.main import app
from app.models.user import UserRole

client = TestClient(app)

_LOGIN_PAYLOAD = {
    "email": "admin@example.com",
    "password": "admin1234",
}


@pytest.fixture(autouse=True)
def clear_dependency_overrides() -> Iterator[None]:
    yield
    app.dependency_overrides.clear()


def test_login_returns_token_payload() -> None:
    auth_service = MagicMock()
    auth_service.login.return_value = LoginResponseDto(
        access_token="token-de-prueba",
        token_type="bearer",
        expires_in=3600,
        user=AuthenticatedUserDto(
            id=1,
            email="admin@example.com",
            first_name="Ada",
            last_name="Lovelace",
            role=UserRole.ADMIN,
        ),
    )
    app.dependency_overrides[get_auth_service] = lambda: auth_service

    response = client.post("/api/auth/login", json=_LOGIN_PAYLOAD)

    assert response.status_code == 200
    payload = response.json()
    assert payload["access_token"] == "token-de-prueba"
    assert payload["token_type"] == "bearer"
    assert payload["expires_in"] == 3600
    assert payload["user"]["email"] == "admin@example.com"
    assert payload["user"]["role"] == UserRole.ADMIN.value


def test_login_returns_401_when_credentials_are_invalid() -> None:
    auth_service = MagicMock()
    auth_service.login.side_effect = InvalidCredentialsError()
    app.dependency_overrides[get_auth_service] = lambda: auth_service

    response = client.post("/api/auth/login", json=_LOGIN_PAYLOAD)

    assert response.status_code == 401
    assert response.json()["detail"] == "Credenciales inválidas"


def test_login_returns_403_when_user_is_inactive() -> None:
    auth_service = MagicMock()
    auth_service.login.side_effect = InactiveUserError()
    app.dependency_overrides[get_auth_service] = lambda: auth_service

    response = client.post("/api/auth/login", json=_LOGIN_PAYLOAD)

    assert response.status_code == 403
    assert response.json()["detail"] == "El usuario está inactivo"


def test_login_returns_422_when_payload_is_invalid() -> None:
    response = client.post("/api/auth/login", json={"email": "no-es-un-email", "password": ""})

    assert response.status_code == 422
