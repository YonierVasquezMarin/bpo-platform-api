from enum import Enum

from pydantic import BaseModel


class ConnectionStatus(str, Enum):
    OK = "ok"
    ERROR = "error"


class OverallConnectionStatus(str, Enum):
    OK = "ok"
    DEGRADED = "degraded"
    ERROR = "error"


class ServiceConnectionStatusDto(BaseModel):
    name: str
    status: ConnectionStatus
    latency_ms: float | None = None
    message: str | None = None


class ConnectionStatusResponseDto(BaseModel):
    status: OverallConnectionStatus
    services: list[ServiceConnectionStatusDto]
