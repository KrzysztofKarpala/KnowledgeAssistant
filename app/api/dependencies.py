from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.repositories.chunk_repository import ChunkRepository
from app.repositories.conversation_repository import (
    ConversationMessageRepository,
    ConversationRepository,
)
from app.repositories.document_repository import DocumentRepository
from app.repositories.query_log_repository import QueryLogRepository
from app.services.answer_service import AnswerService
from app.services.conversation_title_service import ConversationTitleService
from app.services.follow_up_service import FollowUpClassifier
from app.services.query_rewrite_service import QueryRewriteService
from app.services.retrieval_service import RetrievalService


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


async def get_conversation_repository(
    session: AsyncSession = Depends(get_async_session),
) -> ConversationRepository:
    return ConversationRepository(session)


async def get_conversation_message_repository(
    session: AsyncSession = Depends(get_async_session),
) -> ConversationMessageRepository:
    return ConversationMessageRepository(session)


async def get_retrieval_service(
    session: AsyncSession = Depends(get_async_session),
) -> RetrievalService:
    return RetrievalService(session=session)


async def get_answer_service() -> AnswerService:
    return AnswerService()


async def get_follow_up_classifier() -> FollowUpClassifier:
    return FollowUpClassifier()


async def get_conversation_title_service() -> ConversationTitleService:
    return ConversationTitleService()


async def get_query_rewrite_service() -> QueryRewriteService:
    return QueryRewriteService()
