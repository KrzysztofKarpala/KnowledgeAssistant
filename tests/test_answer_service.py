from datetime import date
from uuid import uuid4

from app.services.answer_service import (
    INSUFFICIENT_INFORMATION_ANSWER,
    AnswerService,
    ConversationTurn,
)
from app.services.retrieval_service import RetrievedChunk


class LLMClientMock:
    def __init__(self, response: str) -> None:
        self.response = response
        self.user_prompt: str | None = None

    async def generate(self, *, system_prompt: str, user_prompt: str) -> str:
        self.user_prompt = user_prompt
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
        llm_client=LLMClientMock(
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
    service = AnswerService(llm_client=LLMClientMock(response="Use the blue hammer."))

    answer = await service.answer(question="Which hammer?", sources=[make_source()])

    assert "could not be validated" in answer.answer
    assert answer.cited_chunk_ids == []


async def test_answer_withholds_uncited_response():
    service = AnswerService(
        llm_client=LLMClientMock(
            response='{"answer":"Use the blue hammer.","cited_chunk_ids":[],"insufficient_evidence":false}'
        )
    )

    answer = await service.answer(question="Which hammer?", sources=[make_source()])

    assert "did not cite any retrieved source" in answer.answer
    assert answer.cited_chunk_ids == []


async def test_answer_normalizes_insufficient_evidence():
    source = make_source()
    service = AnswerService(
        llm_client=LLMClientMock(
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


async def test_answer_includes_conversation_history_as_dialogue_context():
    source = make_source()
    llm_client = LLMClientMock(
        response=(
            '{"answer":"Use the blue hammer.",'
            f'"cited_chunk_ids":["{source.chunk_id}"],'
            '"insufficient_evidence":false}'
        )
    )
    service = AnswerService(llm_client=llm_client)

    await service.answer(
        question="Which one?",
        sources=[source],
        conversation_history=[
            ConversationTurn(role="user", content="We are talking about small screws."),
            ConversationTurn(role="assistant", content="Understood."),
        ],
    )

    assert llm_client.user_prompt is not None
    assert "Conversation history" in llm_client.user_prompt
    assert "user: We are talking about small screws." in llm_client.user_prompt
