from app.services.retrieval_service import RetrievalService


def test_distance_to_similarity_clamps_to_zero_one_range():
    assert RetrievalService._distance_to_similarity(-0.25) == 1.0
    assert RetrievalService._distance_to_similarity(0.25) == 0.75
    assert RetrievalService._distance_to_similarity(1.25) == 0.0
