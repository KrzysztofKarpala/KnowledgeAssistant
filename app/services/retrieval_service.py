from dataclasses import dataclass, replace
from datetime import date
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.repositories.chunk_repository import ChunkRepository
from app.services.embedding_service import EmbeddingClient
from app.services.reranker_service import RerankerClient, RerankerServiceError

HYBRID_DENSE_WEIGHT = 0.65
HYBRID_KEYWORD_WEIGHT = 0.35
HYBRID_CANDIDATE_MULTIPLIER = 3
KEYWORD_SEARCH_CONFIG = "english"


@dataclass(frozen=True)
class RetrievalRow:
    chunk_id: UUID
    document_id: UUID
    parent_id: UUID | None
    document_title: str
    document_version: str | None
    effective_from: date | None
    chunk_index: int
    content: str
    dense_score: float | None = None
    keyword_score: float | None = None


@dataclass(frozen=True)
class RetrievedChunk:
    document_id: UUID
    parent_id: UUID | None
    document_title: str
    document_version: str | None
    effective_from: date | None
    chunk_id: UUID
    chunk_index: int
    content: str
    similarity: float
    source_role: str = "semantic_match"


class RetrievalService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        embedding_client: EmbeddingClient | None = None,
        reranker_client: RerankerClient | None = None,
    ) -> None:
        self.session = session
        self.embedding_client = embedding_client or EmbeddingClient()
        self.reranker_client = reranker_client or RerankerClient()

    async def retrieve(
        self,
        *,
        question: str,
        limit: int = settings.top_k,
        active_only: bool = True,
    ) -> list[RetrievedChunk]:
        embeddings = await self.embedding_client.embed_many([question])
        query_embedding = embeddings[0]

        chunk_repository = ChunkRepository(self.session)
        candidate_limit = self._candidate_limit(limit)
        semantic_rows = await chunk_repository.search_similar(
            embedding=query_embedding,
            limit=candidate_limit,
            active_only=active_only,
        )
        keyword_rows = await chunk_repository.search_keyword(
            query=question,
            limit=candidate_limit,
            active_only=active_only,
            search_config=KEYWORD_SEARCH_CONFIG,
        )

        retrieved_chunks = self._merge_retrieval_rows(
            semantic_rows=[
                RetrievalRow(
                    document_id=document.id,
                    parent_id=document.parent_id,
                    document_title=document.title,
                    document_version=document.version,
                    effective_from=document.effective_from,
                    chunk_id=chunk.id,
                    chunk_index=chunk.chunk_index,
                    content=chunk.content,
                    dense_score=self._distance_to_similarity(distance),
                )
                for chunk, document, distance in semantic_rows
            ],
            keyword_rows=[
                RetrievalRow(
                    document_id=document.id,
                    parent_id=document.parent_id,
                    document_title=document.title,
                    document_version=document.version,
                    effective_from=document.effective_from,
                    chunk_id=chunk.id,
                    chunk_index=chunk.chunk_index,
                    content=chunk.content,
                    keyword_score=rank,
                )
                for chunk, document, rank in keyword_rows
            ],
            limit=candidate_limit,
        )

        reranked_chunks = await self._rerank_chunks(
            question=question,
            chunks=retrieved_chunks,
            limit=limit,
        )

        return [
            chunk
            for chunk in await self._include_parent_chunks(
                chunk_repository=chunk_repository,
                chunks=reranked_chunks,
                query_embedding=query_embedding,
                active_only=active_only,
            )
            if chunk.similarity >= settings.retrieval_min_similarity
        ]

    @staticmethod
    def _candidate_limit(limit: int) -> int:
        if not settings.reranker_enabled:
            return limit * HYBRID_CANDIDATE_MULTIPLIER
        return max(limit, settings.reranker_candidate_limit)

    async def _rerank_chunks(
        self,
        *,
        question: str,
        chunks: list[RetrievedChunk],
        limit: int,
    ) -> list[RetrievedChunk]:
        if not settings.reranker_enabled or not chunks:
            return chunks[:limit]

        try:
            reranked_results = await self.reranker_client.rerank(
                query=question,
                documents=[chunk.content for chunk in chunks],
            )
        except RerankerServiceError:
            return chunks[:limit]

        best_chunks = [
            replace(
                chunks[result.index],
                similarity=self._clip(result.relevance_score, min_value=0.0, max_value=1.0),
            )
            for result in sorted(
                reranked_results,
                key=lambda item: item.relevance_score,
                reverse=True,
            )
        ]
        return best_chunks[:limit]

    @staticmethod
    async def _include_parent_chunks(
        *,
        chunk_repository: ChunkRepository,
        chunks: list[RetrievedChunk],
        query_embedding: list[float],
        active_only: bool,
    ) -> list[RetrievedChunk]:
        expanded_chunks = list(chunks)
        seen_document_ids = {chunk.document_id for chunk in expanded_chunks}
        index = 0

        while index < len(expanded_chunks):
            chunk = expanded_chunks[index]
            index += 1
            if chunk.parent_id is None or chunk.parent_id in seen_document_ids:
                continue

            parent_row = await chunk_repository.search_similar_for_document(
                document_id=chunk.parent_id,
                embedding=query_embedding,
                active_only=active_only,
            )
            if parent_row is None:
                continue

            parent_chunk, parent_document, parent_distance = parent_row
            expanded_chunks.append(
                RetrievedChunk(
                    document_id=parent_document.id,
                    parent_id=parent_document.parent_id,
                    document_title=parent_document.title,
                    document_version=parent_document.version,
                    effective_from=parent_document.effective_from,
                    chunk_id=parent_chunk.id,
                    chunk_index=parent_chunk.chunk_index,
                    content=parent_chunk.content,
                    similarity=RetrievalService._distance_to_similarity(parent_distance),
                    source_role="hierarchy_parent",
                )
            )
            seen_document_ids.add(parent_document.id)

        return expanded_chunks

    @staticmethod
    def _distance_to_similarity(distance: float) -> float:
        return RetrievalService._clip(1.0 - distance, min_value=0.0, max_value=1.0)

    @staticmethod
    def _clip(value: float, *, min_value: float, max_value: float) -> float:
        return max(min_value, min(max_value, value))

    @staticmethod
    def _merge_retrieval_rows(
        *,
        semantic_rows: list[RetrievalRow],
        keyword_rows: list[RetrievalRow],
        limit: int,
    ) -> list[RetrievedChunk]:
        candidates: dict[UUID, RetrievalRow] = {}
        for row in semantic_rows:
            candidates[row.chunk_id] = row

        keyword_scores = [row.keyword_score or 0.0 for row in keyword_rows]
        max_keyword_score = max(keyword_scores, default=0.0)
        for row in keyword_rows:
            keyword_score = RetrievalService._normalize_score(row.keyword_score, max_keyword_score)
            existing = candidates.get(row.chunk_id)
            if existing is None:
                candidates[row.chunk_id] = RetrievalRow(
                    chunk_id=row.chunk_id,
                    document_id=row.document_id,
                    parent_id=row.parent_id,
                    document_title=row.document_title,
                    document_version=row.document_version,
                    effective_from=row.effective_from,
                    chunk_index=row.chunk_index,
                    content=row.content,
                    keyword_score=keyword_score,
                )
                continue

            candidates[row.chunk_id] = RetrievalRow(
                chunk_id=existing.chunk_id,
                document_id=existing.document_id,
                parent_id=existing.parent_id,
                document_title=existing.document_title,
                document_version=existing.document_version,
                effective_from=existing.effective_from,
                chunk_index=existing.chunk_index,
                content=existing.content,
                dense_score=existing.dense_score,
                keyword_score=keyword_score,
            )

        ranked_chunks = [
            RetrievalService._to_retrieved_chunk(row)
            for row in sorted(
                candidates.values(),
                key=RetrievalService._ranking_key,
                reverse=True,
            )
        ]
        return ranked_chunks[:limit]

    @staticmethod
    def _normalize_score(score: float | None, max_score: float) -> float:
        if score is None or max_score <= 0.0:
            return 0.0
        return RetrievalService._clip(score / max_score, min_value=0.0, max_value=1.0)

    @staticmethod
    def _to_retrieved_chunk(row: RetrievalRow) -> RetrievedChunk:
        dense_score = row.dense_score or 0.0
        keyword_score = row.keyword_score or 0.0
        final_score = (
            HYBRID_DENSE_WEIGHT * dense_score
            + HYBRID_KEYWORD_WEIGHT * keyword_score
        )
        return RetrievedChunk(
            document_id=row.document_id,
            parent_id=row.parent_id,
            document_title=row.document_title,
            document_version=row.document_version,
            effective_from=row.effective_from,
            chunk_id=row.chunk_id,
            chunk_index=row.chunk_index,
            content=row.content,
            similarity=RetrievalService._clip(final_score, min_value=0.0, max_value=1.0),
            source_role=RetrievalService._source_role(
                dense_score=dense_score,
                keyword_score=keyword_score,
            ),
        )

    @staticmethod
    def _source_role(*, dense_score: float, keyword_score: float) -> str:
        if dense_score > 0.0 and keyword_score > 0.0:
            return "hybrid_match"
        if keyword_score > 0.0:
            return "keyword_match"
        return "semantic_match"

    @staticmethod
    def _ranking_key(row: RetrievalRow) -> tuple[float, date, str, int]:
        retrieved_chunk = RetrievalService._to_retrieved_chunk(row)
        effective_from = row.effective_from or date.min
        return (
            retrieved_chunk.similarity,
            effective_from,
            row.document_title,
            -row.chunk_index,
        )
