from collections.abc import AsyncGenerator, Generator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from testcontainers.postgres import PostgresContainer

from app.core import database
from app.core.database import Base, configure_database
from app.main import app
from app import models  # noqa: F401


@pytest.fixture(scope="session")
def postgres_container() -> Generator[PostgresContainer, None, None]:
    with PostgresContainer(
        image="pgvector/pgvector:pg16",
        username="postgres",
        password="postgres",
        dbname="knowledge_assistant_test",
    ) as container:
        yield container


@pytest.fixture(scope="session")
def test_database_url(postgres_container: PostgresContainer) -> str:
    host = postgres_container.get_container_host_ip()
    port = postgres_container.get_exposed_port(5432)
    return f"postgresql+asyncpg://postgres:postgres@{host}:{port}/knowledge_assistant_test"


@pytest.fixture()
async def api_client(test_database_url: str) -> AsyncGenerator[AsyncClient, None]:
    configure_database(test_database_url)

    async with database.engine.begin() as connection:
        await connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()
    await database.engine.dispose()
