from typing import Protocol

from app.dtos.connection_status import ServiceConnectionStatusDto


class ExternalServiceChecker(Protocol):
    def check_connection(self) -> ServiceConnectionStatusDto:
        ...
