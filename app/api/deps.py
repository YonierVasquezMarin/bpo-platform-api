from fastapi import Depends
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.core.crypto import PasswordCipher, build_password_cipher_from_settings
from app.core.database import engine, get_db
from app.core.security import TokenService, build_token_service_from_settings
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService
from app.services.connection_status_service import ConnectionStatusService
from app.services.database_connection_checker import DatabaseConnectionChecker
from app.services.external_service_checker import ExternalServiceChecker


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


def get_database_engine() -> Engine:
    return engine


def get_database_connection_checker(
    database_engine: Engine = Depends(get_database_engine),
) -> DatabaseConnectionChecker:
    return DatabaseConnectionChecker(database_engine)


def get_external_service_checkers(
    database_checker: DatabaseConnectionChecker = Depends(get_database_connection_checker),
) -> list[ExternalServiceChecker]:
    return [database_checker]


def get_connection_status_service(
    checkers: list[ExternalServiceChecker] = Depends(get_external_service_checkers),
) -> ConnectionStatusService:
    return ConnectionStatusService(checkers)
