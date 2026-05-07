from datetime import date
from uuid import uuid4

from app.services.answer_service import INSUFFICIENT_INFORMATION_ANSWER, AnswerService
from app.services.retrieval_service import RetrievedChunk


class FakeLLMClient:
    def __init__(self, response: str) -> None:
        self.response = response

    async def generate(self, *, system_prompt: str, user_prompt: str) -> str:
        return self.response


def make_source() -> RetrievedChunk:
    return RetrievedChunk(
        document_id=uuid4(),
        parent_id=None,
        document_title="Test Document",
        document_version="1.0",
        effective_from=date(2026, 1, 1),
        chunk_id=uuid4(),
        chunk_index=0,
        content="The blue hammer is used for the small screw.",
        similarity=0.9,
    )


async def test_answer_accepts_valid_structured_response_with_citation():
    source = make_source()
    service = AnswerService(
        llm_client=FakeLLMClient(
            response=(
                '{"answer":"Use the blue hammer.",'
                f'"cited_chunk_ids":["{source.chunk_id}"],'
                '"insufficient_evidence":false}'
            )
        )
    )

    answer = await service.answer(question="Which hammer?", sources=[source])

    assert answer.answer == "Use the blue hammer."
    assert answer.cited_chunk_ids == [source.chunk_id]


async def test_answer_withholds_invalid_json_response():
    service = AnswerService(llm_client=FakeLLMClient(response="Use the blue hammer."))

    answer = await service.answer(question="Which hammer?", sources=[make_source()])

    assert "could not be validated" in answer.answer
    assert answer.cited_chunk_ids == []


async def test_answer_withholds_uncited_response():
    service = AnswerService(
        llm_client=FakeLLMClient(
            response='{"answer":"Use the blue hammer.","cited_chunk_ids":[],"insufficient_evidence":false}'
        )
    )

    answer = await service.answer(question="Which hammer?", sources=[make_source()])

    assert "did not cite any retrieved source" in answer.answer
    assert answer.cited_chunk_ids == []


async def test_answer_normalizes_insufficient_evidence():
    source = make_source()
    service = AnswerService(
        llm_client=FakeLLMClient(
            response=(
                '{"answer":"I do not know.",'
                f'"cited_chunk_ids":["{source.chunk_id}"],'
                '"insufficient_evidence":true}'
            )
        )
    )

    answer = await service.answer(question="Which hammer?", sources=[source])

    assert answer.answer == INSUFFICIENT_INFORMATION_ANSWER
    assert answer.cited_chunk_ids == [source.chunk_id]
