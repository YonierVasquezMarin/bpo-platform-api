import hmac
import logging

from cryptography.exceptions import InvalidTag

from app.core.crypto import PasswordCipher
from app.core.exceptions import InactiveUserError, InvalidCredentialsError
from app.core.security import TokenService
from app.dtos.auth import AuthenticatedUserDto, LoginRequestDto, LoginResponseDto
from app.models.user import User
from app.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)


class AuthService:
    def __init__(
        self,
        user_repository: UserRepository,
        password_cipher: PasswordCipher,
        token_service: TokenService,
    ) -> None:
        self._user_repository = user_repository
        self._password_cipher = password_cipher
        self._token_service = token_service
        self._login_request: LoginRequestDto | None = None
        self._user: User | None = None
        self._access_token: str | None = None

    def login(self, login_request: LoginRequestDto) -> LoginResponseDto:
        self._login_request = login_request
        self._log_login_started()
        self._authenticate_user()
        self._issue_access_token()
        self._register_successful_login()
        self._log_login_succeeded()
        return self._build_login_response()

    def _authenticate_user(self) -> None:
        self._user = self._user_repository.find_by_email(self._login_request.email)
        self._ensure_user_was_found()
        self._ensure_password_matches()
        self._ensure_user_is_active()

    def _ensure_user_was_found(self) -> None:
        if self._user_was_not_found():
            raise InvalidCredentialsError()

    def _user_was_not_found(self) -> bool:
        user_was_found = self._user is not None
        user_was_not_found = not user_was_found
        return user_was_not_found

    def _ensure_password_matches(self) -> None:
        if self._password_does_not_match():
            raise InvalidCredentialsError()

    def _password_does_not_match(self) -> bool:
        password_matches = self._stored_password_matches_request()
        password_does_not_match = not password_matches
        return password_does_not_match

    def _stored_password_matches_request(self) -> bool:
        try:
            decrypted_password = self._password_cipher.decrypt_password(self._user.password)
        except (InvalidTag, ValueError, UnicodeDecodeError):
            return False
        return hmac.compare_digest(decrypted_password, self._login_request.password)

    def _ensure_user_is_active(self) -> None:
        if self._user_is_inactive():
            raise InactiveUserError()

    def _user_is_inactive(self) -> bool:
        user_is_active = self._user.is_active
        user_is_inactive = not user_is_active
        return user_is_inactive

    def _issue_access_token(self) -> None:
        self._access_token = self._token_service.create_access_token(self._user)

    def _register_successful_login(self) -> None:
        self._user = self._user_repository.mark_last_login(self._user)

    def _build_login_response(self) -> LoginResponseDto:
        expires_in = self._token_service.get_expires_in_seconds()
        authenticated_user = self._build_authenticated_user_dto()
        return LoginResponseDto(
            access_token=self._access_token,
            token_type="bearer",
            expires_in=expires_in,
            user=authenticated_user,
        )

    def _build_authenticated_user_dto(self) -> AuthenticatedUserDto:
        return AuthenticatedUserDto(
            first_name=self._user.first_name,
            last_name=self._user.last_name,
            email=self._user.email,
            role=self._user.role,
            id=self._user.id,
        )

    def _log_login_started(self) -> None:
        logger.info("Iniciando autenticación para %s", self._login_request.email)

    def _log_login_succeeded(self) -> None:
        logger.info("Autenticación exitosa para el usuario %s", self._user.id)
