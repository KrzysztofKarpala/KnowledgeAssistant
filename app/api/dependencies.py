from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.repositories.chunks import ChunkRepository
from app.repositories.documents import DocumentRepository
from app.repositories.query_logs import QueryLogRepository
from app.services.answer import AnswerService
from app.services.retrieval import RetrievalService


async def get_document_repository(
    session: AsyncSession = Depends(get_async_session),
) -> DocumentRepository:
    return DocumentRepository(session)


async def get_chunk_repository(
    session: AsyncSession = Depends(get_async_session),
) -> ChunkRepository:
    return ChunkRepository(session)


async def get_query_log_repository(
    session: AsyncSession = Depends(get_async_session),
) -> QueryLogRepository:
    return QueryLogRepository(session)


async def get_retrieval_service(
    session: AsyncSession = Depends(get_async_session),
) -> RetrievalService:
    return RetrievalService(session=session)


async def get_answer_service() -> AnswerService:
    return AnswerService()
