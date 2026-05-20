import pytest

from app.models.conversation import CONVERSATION_TITLE_MAX_LENGTH
from app.services.conversation_title_service import ConversationTitleService
from app.services.llm_service import LLMServiceError


async def test_conversation_title_service_generates_title_with_llm():
    llm_client = LLMClientMock(response='{"title":"Reset Admin Password"}')
    service = ConversationTitleService(llm_client=llm_client)

    title = await service.generate_title(
        first_user_message="How do I reset a user password from the admin console?"
    )

    assert title == "Reset Admin Password"
    assert "Generate a conversation title" in llm_client.user_prompt


async def test_conversation_title_service_rejects_invalid_llm_title():
    service = ConversationTitleService(
        llm_client=LLMClientMock(
            response=f'{{"title":"{"A" * (CONVERSATION_TITLE_MAX_LENGTH + 1)}"}}'
        )
    )

    with pytest.raises(LLMServiceError, match="invalid conversation title"):
        await service.generate_title(first_user_message="Question")


class LLMClientMock:
    def __init__(self, *, response: str) -> None:
        self.response = response
        self.system_prompt = None
        self.user_prompt = None

    async def generate(self, *, system_prompt: str, user_prompt: str) -> str:
        self.system_prompt = system_prompt
        self.user_prompt = user_prompt
        return self.response
