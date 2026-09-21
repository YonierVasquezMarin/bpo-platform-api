from datetime import datetime, timedelta, timezone

import jwt

from app.core.config import settings
from app.models.user import User


class TokenService:
    def __init__(self, secret_key: str, algorithm: str, expire_minutes: int) -> None:
        self._secret_key = secret_key
        self._algorithm = algorithm
        self._expire_minutes = expire_minutes
        self._user: User | None = None
        self._validate_secret_key()

    def create_access_token(self, user: User) -> str:
        self._user = user
        payload = self._build_payload()
        return jwt.encode(payload, self._secret_key, algorithm=self._algorithm)

    def get_expires_in_seconds(self) -> int:
        return self._expire_minutes * 60

    def _validate_secret_key(self) -> None:
        if self._secret_key_is_missing():
            raise ValueError("JWT_SECRET_KEY debe estar definida en .env")

    def _secret_key_is_missing(self) -> bool:
        return not self._secret_key.strip()

    def _build_payload(self) -> dict[str, str | datetime]:
        issued_at = self._get_current_utc_time()
        return {
            "sub": str(self._user.id),
            "email": self._user.email,
            "role": self._get_role_value(),
            "iat": issued_at,
            "exp": self._get_expiration_time(issued_at),
        }

    def _get_current_utc_time(self) -> datetime:
        return datetime.now(timezone.utc)

    def _get_expiration_time(self, issued_at: datetime) -> datetime:
        return issued_at + timedelta(minutes=self._expire_minutes)

    def _get_role_value(self) -> str:
        role = self._user.role
        role_has_enum_value = hasattr(role, "value")
        if role_has_enum_value:
            return str(role.value)
        return str(role)


def build_token_service_from_settings() -> TokenService:
    return TokenService(
        secret_key=settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
        expire_minutes=settings.jwt_expire_minutes,
    )
