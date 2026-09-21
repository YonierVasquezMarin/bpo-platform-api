from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.crypto import PasswordCipher, build_password_cipher_from_settings
from app.core.database import get_db
from app.core.security import TokenService, build_token_service_from_settings
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService


def get_user_repository(db: Session = Depends(get_db)) -> UserRepository:
    return UserRepository(db)


def get_password_cipher() -> PasswordCipher:
    return build_password_cipher_from_settings()


def get_token_service() -> TokenService:
    return build_token_service_from_settings()


def get_auth_service(
    user_repository: UserRepository = Depends(get_user_repository),
    password_cipher: PasswordCipher = Depends(get_password_cipher),
    token_service: TokenService = Depends(get_token_service),
) -> AuthService:
    return AuthService(
        user_repository=user_repository,
        password_cipher=password_cipher,
        token_service=token_service,
    )
