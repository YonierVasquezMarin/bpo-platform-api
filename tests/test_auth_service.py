from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from app.core.crypto import PasswordCipher
from app.core.exceptions import InactiveUserError, InvalidCredentialsError
from app.core.security import TokenService
from app.dtos.auth import LoginRequestDto
from app.models.user import User, UserRole
from app.services.auth_service import AuthService

_TEST_EMAIL = "admin@example.com"
_TEST_PASSWORD = "admin1234"


def test_login_returns_token_and_user() -> None:
    user, auth_service, user_repository = _build_auth_context()
    login_request = LoginRequestDto(email=_TEST_EMAIL, password=_TEST_PASSWORD)

    response = auth_service.login(login_request)

    assert response.token_type == "bearer"
    assert response.expires_in == 3600
    assert response.access_token
    assert response.user.email == _TEST_EMAIL
    assert response.user.role == UserRole.ADMIN
    user_repository.mark_last_login.assert_called_once_with(user)


def test_login_fails_when_user_does_not_exist() -> None:
    _, auth_service, _ = _build_auth_context(user=None)
    login_request = LoginRequestDto(email=_TEST_EMAIL, password=_TEST_PASSWORD)

    with pytest.raises(InvalidCredentialsError):
        auth_service.login(login_request)


def test_login_fails_when_password_is_invalid() -> None:
    _, auth_service, user_repository = _build_auth_context()
    login_request = LoginRequestDto(email=_TEST_EMAIL, password="clave-incorrecta")

    with pytest.raises(InvalidCredentialsError):
        auth_service.login(login_request)
    user_repository.mark_last_login.assert_not_called()


def test_login_fails_when_user_is_inactive() -> None:
    _, auth_service, user_repository = _build_auth_context(is_active=False)
    login_request = LoginRequestDto(email=_TEST_EMAIL, password=_TEST_PASSWORD)

    with pytest.raises(InactiveUserError):
        auth_service.login(login_request)
    user_repository.mark_last_login.assert_not_called()


def _build_auth_context(
    user: User | None | object = ...,
    is_active: bool = True,
) -> tuple[User | None, AuthService, MagicMock]:
    cipher = PasswordCipher(encryption_key="clave-de-prueba", encryption_salt="sal-de-prueba")
    resolved_user = user if user is not ... else _build_user(cipher, is_active=is_active)
    user_repository = MagicMock()
    user_repository.find_by_email.return_value = resolved_user
    user_repository.mark_last_login.side_effect = lambda stored_user: stored_user
    token_service = TokenService(
        secret_key="clave-jwt-de-prueba-con-longitud-segura-32b",
        algorithm="HS256",
        expire_minutes=60,
    )
    auth_service = AuthService(
        user_repository=user_repository,
        password_cipher=cipher,
        token_service=token_service,
    )
    return resolved_user, auth_service, user_repository


def _build_user(cipher: PasswordCipher, is_active: bool) -> MagicMock:
    user = MagicMock(spec=User)
    user.id = 1
    user.email = _TEST_EMAIL
    user.password = cipher.encrypt_password(_TEST_PASSWORD)
    user.first_name = "Ada"
    user.last_name = "Lovelace"
    user.role = UserRole.ADMIN
    user.is_active = is_active
    user.created_at = datetime.now(timezone.utc)
    user.updated_at = datetime.now(timezone.utc)
    user.last_login_at = None
    user.external_id = None
    return user
