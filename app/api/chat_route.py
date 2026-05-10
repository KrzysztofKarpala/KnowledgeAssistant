from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import (
    get_answer_service,
    get_query_log_repository,
    get_retrieval_service,
)
from app.repositories.query_log_repository import QueryLogRepository
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    RetrievalRequest,
    RetrievalResponse,
    RetrievedChunkResponse,
    SourceReference,
)
from app.services.answer_service import AnswerService
from app.services.embedding_service import EmbeddingServiceError
from app.services.llm_service import LLMServiceError
from app.services.retrieval_service import RetrievedChunk, RetrievalService

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/retrieve", response_model=RetrievalResponse)
async def retrieve(
    payload: RetrievalRequest,
    retrieval_service: RetrievalService = Depends(get_retrieval_service),
) -> RetrievalResponse:
    try:
        results = await retrieval_service.retrieve(
            question=payload.question,
            limit=payload.limit,
            active_only=payload.active_only,
        )
    except EmbeddingServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    return RetrievalResponse(
        question=payload.question,
        results=[
            RetrievedChunkResponse(
                document_id=result.document_id,
                parent_id=result.parent_id,
                document_title=result.document_title,
                document_version=result.document_version,
                effective_from=result.effective_from,
                chunk_id=result.chunk_id,
                chunk_index=result.chunk_index,
                similarity=result.similarity,
                source_role=result.source_role,
                content=result.content,
            )
            for result in results
        ],
    )


@router.post("", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    retrieval_service: RetrievalService = Depends(get_retrieval_service),
    answer_service: AnswerService = Depends(get_answer_service),
    query_log_repository: QueryLogRepository = Depends(get_query_log_repository),
) -> ChatResponse:
    try:
        retrieved_chunks = await retrieval_service.retrieve(
            question=payload.question,
        )
        answer = await answer_service.answer(
            question=payload.question,
            sources=retrieved_chunks,
        )
    except EmbeddingServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except LLMServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    sources = build_source_references(retrieved_chunks)

    response = ChatResponse(
        answer=answer.answer,
        sources=sources,
        cited_chunk_ids=answer.cited_chunk_ids,
        confidence=calculate_confidence([source.similarity for source in sources]),
    )

    await query_log_repository.create(
        question=payload.question,
        answer=response.answer,
        used_sources=[source.model_dump(mode="json") for source in response.sources],
    )

    return response


def build_source_references(retrieved_chunks: list[RetrievedChunk]) -> list[SourceReference]:
    return [
        SourceReference(
            document_id=result.document_id,
            parent_id=result.parent_id,
            document_title=result.document_title,
            document_version=result.document_version,
            effective_from=result.effective_from,
            chunk_id=result.chunk_id,
            chunk_index=result.chunk_index,
            similarity=result.similarity,
            source_role=result.source_role,
        )
        for result in retrieved_chunks
    ]


def calculate_confidence(similarities: list[float]) -> str:
    if not similarities:
        return "low"

    best_similarity = max(similarities)
    if best_similarity >= 0.75:
        return "high"
    if best_similarity >= 0.45:
        return "medium"
    return "low"
