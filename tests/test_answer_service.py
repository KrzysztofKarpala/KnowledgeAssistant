from datetime import date
from uuid import uuid4

from app.services.answer_service import (
    INSUFFICIENT_INFORMATION_ANSWER,
    AnswerService,
    ConversationTurn,
)
from app.services.retrieval_service import RetrievedChunk


class LLMClientMock:
    def __init__(self, response: str | list[str]) -> None:
        self.responses = response if isinstance(response, list) else [response]
        self.user_prompt: str | None = None
        self.user_prompts: list[str] = []

    async def generate(self, *, system_prompt: str, user_prompt: str) -> str:
        self.user_prompt = user_prompt
        self.user_prompts.append(user_prompt)
        return self.responses.pop(0)


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
    service = AnswerService(llm_client=LLMClientMock(response=["Use the blue hammer.", "Still invalid."]))

    answer = await service.answer(question="Which hammer?", sources=[make_source()])

    assert "did not match the required answer format" in answer.answer
    assert answer.cited_chunk_ids == []


async def test_answer_repairs_invalid_json_response_once():
    source = make_source()
    llm_client = LLMClientMock(
        response=[
            "Use the blue hammer.",
            (
                '{"answer":"Use the blue hammer.",'
                f'"cited_chunk_ids":["{source.chunk_id}"],'
                '"insufficient_evidence":false,'
                '"uses_conversation_history":false}'
            ),
        ]
    )
    service = AnswerService(llm_client=llm_client)

    answer = await service.answer(question="Which hammer?", sources=[source])

    assert answer.answer == "Use the blue hammer."
    assert answer.cited_chunk_ids == [source.chunk_id]
    assert len(llm_client.user_prompts) == 2
    assert "previous model response was not valid JSON" in llm_client.user_prompts[1]


async def test_answer_repair_still_requires_citations():
    source = make_source()
    service = AnswerService(
        llm_client=LLMClientMock(
            response=[
                "Use the blue hammer.",
                (
                    '{"answer":"Use the blue hammer.",'
                    '"cited_chunk_ids":[],'
                    '"insufficient_evidence":false,'
                    '"uses_conversation_history":false}'
                ),
            ]
        )
    )

    answer = await service.answer(question="Which hammer?", sources=[source])

    assert "did not cite any retrieved source" in answer.answer
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


async def test_answer_can_use_conversation_history_for_conversation_question():
    service = AnswerService(
        llm_client=LLMClientMock(
            response=(
                '{"answer":"The first product mentioned was CX-300.",'
                '"cited_chunk_ids":[],'
                '"insufficient_evidence":false,'
                '"uses_conversation_history":true}'
            )
        )
    )

    answer = await service.answer(
        question="What was the first product we mentioned?",
        sources=[],
        conversation_history=[
            ConversationTurn(
                role="assistant",
                content="If LP-22 is unavailable, operators must handwrite labels for CX-300 or BX-200.",
            ),
        ],
    )

    assert answer.answer == "The first product mentioned was CX-300."
    assert answer.cited_chunk_ids == []


async def test_answer_rejects_uncited_document_answer_even_with_conversation_history():
    service = AnswerService(
        llm_client=LLMClientMock(
            response=(
                '{"answer":"Use the blue hammer.",'
                '"cited_chunk_ids":[],'
                '"insufficient_evidence":false,'
                '"uses_conversation_history":false}'
            )
        )
    )

    answer = await service.answer(
        question="Which hammer should I use?",
        sources=[make_source()],
        conversation_history=[ConversationTurn(role="user", content="We discussed hammers.")],
    )

    assert "did not cite any retrieved source" in answer.answer
    assert answer.cited_chunk_ids == []
