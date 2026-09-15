from fastapi import FastAPI

from app.api.routes.health import router as health_router
from app.core.config import settings


def create_app() -> FastAPI:
    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="API orquestadora de la solución agéntica BPO",
    )
    application.include_router(health_router)
    return application


app = create_app()
