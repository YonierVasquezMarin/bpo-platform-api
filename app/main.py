import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import api_router
from app.core.config import settings
from app.core.database import engine


def configure_logging() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("%(levelname)s %(asctime)s [%(name)s] %(message)s")
    )
    app_logger = logging.getLogger("app")
    app_logger.setLevel(logging.INFO)
    app_logger.addHandler(handler)


@asynccontextmanager
async def lifespan(_application: FastAPI) -> AsyncIterator[None]:
    yield
    engine.dispose()


def create_app() -> FastAPI:
    configure_logging()
    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="API orquestadora de la solución agéntica BPO",
        lifespan=lifespan,
    )
    application.include_router(api_router)
    return application


app = create_app()
