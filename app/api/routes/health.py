from fastapi import APIRouter, Depends, Response, status

from app.api.deps import get_connection_status_service
from app.core.config import settings
from app.dtos.connection_status import ConnectionStatusResponseDto, OverallConnectionStatus
from app.services.connection_status_service import ConnectionStatusService

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
    }


@router.get(
    "/health/connections",
    response_model=ConnectionStatusResponseDto,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "description": "Uno o más servicios externos no están disponibles",
        },
    },
)
def get_connections_status(
    response: Response,
    connection_status_service: ConnectionStatusService = Depends(get_connection_status_service),
) -> ConnectionStatusResponseDto:
    payload = connection_status_service.get_status()
    if _connections_are_not_healthy(payload):
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return payload


def _connections_are_not_healthy(payload: ConnectionStatusResponseDto) -> bool:
    connections_are_healthy = payload.status == OverallConnectionStatus.OK
    connections_are_not_healthy = not connections_are_healthy
    return connections_are_not_healthy
