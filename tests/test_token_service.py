from datetime import datetime, timezone
from unittest.mock import MagicMock

import jwt
import pytest

from app.core.security import TokenService
from app.models.user import User, UserRole


def test_create_access_token_contains_user_claims() -> None:
    token_service = TokenService(
        secret_key="clave-jwt-de-prueba-con-longitud-segura-32b",
        algorithm="HS256",
        expire_minutes=30,
    )
    user = _build_user()

    access_token = token_service.create_access_token(user)
    payload = jwt.decode(
        access_token,
        "clave-jwt-de-prueba-con-longitud-segura-32b",
        algorithms=["HS256"],
    )

    assert payload["sub"] == "7"
    assert payload["email"] == "support@example.com"
    assert payload["role"] == UserRole.SUPPORT.value
    assert token_service.get_expires_in_seconds() == 1800


def test_missing_secret_key_raises_value_error() -> None:
    with pytest.raises(ValueError, match="JWT_SECRET_KEY"):
        TokenService(secret_key="   ", algorithm="HS256", expire_minutes=60)


def _build_user() -> MagicMock:
    user = MagicMock(spec=User)
    user.id = 7
    user.email = "support@example.com"
    user.role = UserRole.SUPPORT
    user.created_at = datetime.now(timezone.utc)
    return user
