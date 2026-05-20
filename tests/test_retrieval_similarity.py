from datetime import date
from uuid import uuid4

import pytest

from app.services.reranker_service import RerankResult
from app.services.retrieval_service import RetrievalRow, RetrievalService


def test_distance_to_similarity_clamps_to_zero_one_range():
    assert RetrievalService._distance_to_similarity(-0.25) == 1.0
    assert RetrievalService._distance_to_similarity(0.25) == 0.75
    assert RetrievalService._distance_to_similarity(1.25) == 0.0


def test_merge_retrieval_rows_combines_dense_and_keyword_scores():
    semantic_only_id = uuid4()
    hybrid_id = uuid4()
    semantic_only = RetrievalRow(
        chunk_id=semantic_only_id,
        document_id=uuid4(),
        parent_id=None,
        document_title="Semantic only",
        document_version="1.0",
        effective_from=date(2026, 1, 1),
        chunk_index=0,
        content="Semantically close content.",
        dense_score=0.7,
    )
    hybrid_semantic = RetrievalRow(
        chunk_id=hybrid_id,
        document_id=uuid4(),
        parent_id=None,
        document_title="Hybrid",
        document_version="1.0",
        effective_from=date(2026, 1, 1),
        chunk_index=0,
        content="Semantically close and keyword exact content.",
        dense_score=0.6,
    )
    hybrid_keyword = RetrievalRow(
        chunk_id=hybrid_id,
        document_id=hybrid_semantic.document_id,
        parent_id=None,
        document_title="Hybrid",
        document_version="1.0",
        effective_from=date(2026, 1, 1),
        chunk_index=0,
        content="Semantically close and keyword exact content.",
        keyword_score=10.0,
    )

    results = RetrievalService._merge_retrieval_rows(
        semantic_rows=[semantic_only, hybrid_semantic],
        keyword_rows=[hybrid_keyword],
        limit=2,
    )

    assert results[0].chunk_id == hybrid_id
    assert results[0].source_role == "hybrid_match"
    assert results[1].chunk_id == semantic_only_id
    assert results[1].source_role == "semantic_match"


def test_candidate_limit_uses_wider_pool_when_reranker_is_enabled(monkeypatch):
    monkeypatch.setattr("app.services.retrieval_service.settings.reranker_enabled", True)
    monkeypatch.setattr("app.services.retrieval_service.settings.reranker_candidate_limit", 50)

    assert RetrievalService._candidate_limit(5) == 50


async def test_rerank_chunks_maps_result_indexes_to_original_candidates(monkeypatch):
    monkeypatch.setattr("app.services.retrieval_service.settings.reranker_enabled", True)
    service = RetrievalService(
        session=None,
        embedding_client=None,
        reranker_client=RerankerClientMock(
            [
                RerankResult(index=1, relevance_score=0.92),
                RerankResult(index=0, relevance_score=0.41),
            ]
        ),
    )
    first_chunk = _retrieved_chunk(content="Refund policy.")
    second_chunk = _retrieved_chunk(content="Password reset instructions.")

    results = await service._rerank_chunks(
        question="How do I reset my password?",
        chunks=[first_chunk, second_chunk],
        limit=1,
    )

    assert results[0].chunk_id == second_chunk.chunk_id
    assert results[0].content == "Password reset instructions."
    assert results[0].similarity == pytest.approx(0.92)


def _retrieved_chunk(*, content: str):
    return RetrievalService._to_retrieved_chunk(
        RetrievalRow(
            chunk_id=uuid4(),
            document_id=uuid4(),
            parent_id=None,
            document_title="Document",
            document_version="1.0",
            effective_from=date(2026, 1, 1),
            chunk_index=0,
            content=content,
            dense_score=0.5,
        )
    )


class RerankerClientMock:
    def __init__(self, results: list[RerankResult]) -> None:
        self.results = results
        self.query = None
        self.documents = None

    async def rerank(self, *, query: str, documents: list[str]) -> list[RerankResult]:
        self.query = query
        self.documents = documents
        return self.results
