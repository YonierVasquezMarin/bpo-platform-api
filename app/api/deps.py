from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.crypto import PasswordCipher, build_password_cipher_from_settings
from app.core.database import engine, get_db
from app.core.enum_values import enum_value
from app.core.exceptions import InvalidAccessTokenError
from app.core.security import TokenService, build_token_service_from_settings
from app.models.user import User, UserRole
from app.repositories.document_repository import DocumentRepository
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService
from app.services.blob_storage_client import build_blob_storage_client
from app.services.connection_status_service import ConnectionStatusService
from app.services.database_connection_checker import DatabaseConnectionChecker
from app.services.document_processing_runner import index_document_version, process_document_version
from app.services.document_upload_service import DocumentUploadService
from app.services.document_version_query_service import DocumentVersionQueryService
from app.services.document_version_workflow import DocumentVersionWorkflow
from app.services.external_service_checker import ExternalServiceChecker
from app.services.human_feedback_service import HumanFeedbackService

_bearer_scheme = HTTPBearer(auto_error=False)
_DOCUMENT_MANAGER_ROLES = {UserRole.ADMIN.value, UserRole.KNOWLEDGE_MANAGER.value}


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


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    token_service: TokenService = Depends(get_token_service),
    user_repository: UserRepository = Depends(get_user_repository),
) -> User:
    access_token = _require_bearer_token(credentials)
    try:
        user_id = token_service.read_user_id(access_token)
    except InvalidAccessTokenError as ex:
        raise _build_invalid_token_error() from ex
    user = user_repository.find_by_id(user_id)
    if user is None:
        raise _build_invalid_token_error()
    if not user.is_active:
        raise _build_inactive_user_error()
    return user


def get_current_document_manager(current_user: User = Depends(get_current_user)) -> User:
    if not _user_can_manage_documents(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permisos para gestionar documentos",
        )
    return current_user


def get_document_repository(db: Session = Depends(get_db)) -> DocumentRepository:
    return DocumentRepository(db)


def get_document_upload_service(
    document_repository: DocumentRepository = Depends(get_document_repository),
) -> DocumentUploadService:
    return DocumentUploadService(
        document_repository=document_repository,
        blob_storage=build_blob_storage_client(),
        container_name=settings.azure_storage_container,
        max_size_bytes=settings.document_max_size_bytes,
    )


def get_document_version_query_service(
    document_repository: DocumentRepository = Depends(get_document_repository),
) -> DocumentVersionQueryService:
    return DocumentVersionQueryService(document_repository)


def get_document_version_workflow(
    document_repository: DocumentRepository = Depends(get_document_repository),
) -> DocumentVersionWorkflow:
    return DocumentVersionWorkflow(document_repository)


def get_human_feedback_service(
    document_repository: DocumentRepository = Depends(get_document_repository),
) -> HumanFeedbackService:
    return HumanFeedbackService(document_repository)


def get_document_processing_task() -> Callable[[int], None]:
    return process_document_version


def get_document_indexing_task() -> Callable[[int], None]:
    return index_document_version


def _require_bearer_token(credentials: HTTPAuthorizationCredentials | None) -> str:
    if credentials is None or not credentials.credentials.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autenticado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials


def _user_can_manage_documents(user: User) -> bool:
    return enum_value(user.role) in _DOCUMENT_MANAGER_ROLES


def _build_invalid_token_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token de acceso inválido",
        headers={"WWW-Authenticate": "Bearer"},
    )


def _build_inactive_user_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="El usuario está inactivo",
    )
