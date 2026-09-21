from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_auth_service
from app.core.exceptions import InactiveUserError, InvalidCredentialsError
from app.dtos.auth import LoginRequestDto, LoginResponseDto
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/login",
    response_model=LoginResponseDto,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_401_UNAUTHORIZED: {"description": "Credenciales inválidas"},
        status.HTTP_403_FORBIDDEN: {"description": "El usuario está inactivo"},
    },
)
def login(
    payload: LoginRequestDto,
    auth_service: AuthService = Depends(get_auth_service),
) -> LoginResponseDto:
    try:
        return auth_service.login(payload)
    except InvalidCredentialsError as ex:
        raise _build_invalid_credentials_http_error() from ex
    except InactiveUserError as ex:
        raise _build_inactive_user_http_error() from ex


def _build_invalid_credentials_http_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales inválidas",
        headers={"WWW-Authenticate": "Bearer"},
    )


def _build_inactive_user_http_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="El usuario está inactivo",
    )
