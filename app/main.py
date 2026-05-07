from fastapi import FastAPI

from app.api import chat, documents, health, queries
from app.core.config import settings


def create_app() -> FastAPI:
    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Backend API for a local RAG knowledge assistant.",
    )

    application.include_router(health.router)
    application.include_router(documents.router)
    application.include_router(chat.router)
    application.include_router(queries.router)

    return application


app = create_app()
