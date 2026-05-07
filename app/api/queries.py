from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_query_log_repository
from app.models.query_log import QueryLog
from app.repositories.query_logs import QueryLogRepository
from app.schemas.queries import QueryLogResponse

router = APIRouter(prefix="/queries", tags=["queries"])


def serialize_query_log(query_log: QueryLog) -> QueryLogResponse:
    return QueryLogResponse(
        id=query_log.id,
        question=query_log.question,
        answer=query_log.answer,
        used_sources=query_log.used_sources,
        created_at=query_log.created_at,
    )


@router.get("", response_model=list[QueryLogResponse])
async def list_queries(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    query_log_repository: QueryLogRepository = Depends(get_query_log_repository),
) -> list[QueryLogResponse]:
    query_logs = await query_log_repository.list(limit=limit, offset=offset)
    return [serialize_query_log(query_log) for query_log in query_logs]
