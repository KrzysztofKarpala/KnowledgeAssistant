from collections.abc import Sequence
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.query_log import QueryLog


class QueryLogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        question: str,
        answer: str,
        used_sources: list[dict[str, Any]],
    ) -> QueryLog:
        query_log = QueryLog(
            question=question,
            answer=answer,
            used_sources=used_sources,
        )
        self.session.add(query_log)
        await self.session.commit()
        await self.session.refresh(query_log)
        return query_log

    async def list(self, *, limit: int = 100, offset: int = 0) -> Sequence[QueryLog]:
        result = await self.session.scalars(
            select(QueryLog).order_by(QueryLog.created_at.desc()).limit(limit).offset(offset)
        )
        return result.all()
