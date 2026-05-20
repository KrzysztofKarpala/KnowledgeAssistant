from app.services.answer_service import ConversationTurn
from app.services.follow_up_service import FollowUpClassifier


async def test_follow_up_classifier_asks_llm_with_history():
    llm_client = LLMClientMock(response='{"is_follow_up":true}')
    classifier = FollowUpClassifier(llm_client=llm_client)

    result = await classifier.is_follow_up(
        question="Why?",
        conversation_history=[
            ConversationTurn(role="user", content="Which production line approves AX-100?"),
            ConversationTurn(role="assistant", content="Line SMT-04 approves AX-100."),
        ],
    )

    assert result is True
    assert "Conversation history:" in llm_client.user_prompt
    assert "Latest user message:" in llm_client.user_prompt
    assert "Why?" in llm_client.user_prompt


async def test_follow_up_classifier_returns_false_without_history():
    llm_client = LLMClientMock(response='{"is_follow_up":true}')
    classifier = FollowUpClassifier(llm_client=llm_client)

    result = await classifier.is_follow_up(
        question="Why?",
        conversation_history=[],
    )

    assert result is False
    assert llm_client.user_prompt is None


async def test_follow_up_classifier_treats_invalid_response_as_standalone():
    classifier = FollowUpClassifier(llm_client=LLMClientMock(response="not json"))

    result = await classifier.is_follow_up(
        question="Why?",
        conversation_history=[ConversationTurn(role="user", content="Previous question")],
    )

    assert result is False


class LLMClientMock:
    def __init__(self, *, response: str) -> None:
        self.response = response
        self.system_prompt = None
        self.user_prompt = None

    async def generate(self, *, system_prompt: str, user_prompt: str) -> str:
        self.system_prompt = system_prompt
        self.user_prompt = user_prompt
        return self.response
