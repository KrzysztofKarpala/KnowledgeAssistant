from datetime import date
from uuid import uuid4

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
