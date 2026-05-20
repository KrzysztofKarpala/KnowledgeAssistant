import pytest

from app.services.answer_service import ConversationTurn
from app.services.llm_service import LLMServiceError
from app.services.query_rewrite_service import QueryRewriteService


async def test_query_rewrite_service_rewrites_follow_up_with_history():
    llm_client = LLMClientMock(
        response='{"query":"Is product CX-300 approved or suitable for use on line SMT-04?"}'
    )
    service = QueryRewriteService(llm_client=llm_client)

    query = await service.rewrite(
        question="What about product CX-300?",
        conversation_history=[
            ConversationTurn(role="user", content="What product should be used in line SMT-04?"),
            ConversationTurn(role="assistant", content="Product AX-100 should be used in line SMT-04."),
        ],
    )

    assert query == "Is product CX-300 approved or suitable for use on line SMT-04?"
    assert "Conversation history:" in llm_client.user_prompt
    assert "Latest user message:" in llm_client.user_prompt


async def test_query_rewrite_service_skips_llm_without_history():
    llm_client = LLMClientMock(response='{"query":"Should not be used"}')
    service = QueryRewriteService(llm_client=llm_client)

    query = await service.rewrite(
        question="What product should be used in line SMT-04?",
        conversation_history=[],
    )

    assert query == "What product should be used in line SMT-04?"
    assert llm_client.user_prompt is None


async def test_query_rewrite_service_rejects_invalid_llm_response():
    service = QueryRewriteService(llm_client=LLMClientMock(response="not json"))

    with pytest.raises(LLMServiceError, match="invalid rewritten query"):
        await service.rewrite(
            question="What about product CX-300?",
            conversation_history=[ConversationTurn(role="user", content="SMT-04 question")],
        )


class LLMClientMock:
    def __init__(self, *, response: str) -> None:
        self.response = response
        self.system_prompt = None
        self.user_prompt = None

    async def generate(self, *, system_prompt: str, user_prompt: str) -> str:
        self.system_prompt = system_prompt
        self.user_prompt = user_prompt
        return self.response
