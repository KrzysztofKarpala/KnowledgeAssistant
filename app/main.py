from fastapi import FastAPI

from app.api import chat_route, conversations_route, documents_route, health_route, queries_route
from app.core.config import settings


def create_app() -> FastAPI:
    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Backend API for a local RAG knowledge assistant.",
    )

    application.include_router(health_route.router)
    application.include_router(documents_route.router)
    application.include_router(chat_route.router)
    application.include_router(conversations_route.router)
    application.include_router(queries_route.router)

    return application


app = create_app()
