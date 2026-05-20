import json
from dataclasses import dataclass

from pydantic import BaseModel, ValidationError

from app.services.answer_service import ConversationTurn
from app.services.llm_service import LLMClient


FOLLOW_UP_SYSTEM_PROMPT = """
You classify whether a user's latest message depends on the prior conversation.

Return only valid JSON with this exact shape:
{"is_follow_up":false}

Set is_follow_up to true only when the latest message cannot be fully understood
without prior conversation context, corrects or challenges a previous answer, asks
for elaboration, or refers to earlier entities with pronouns or phrases like this,
that, it, those, previous, above, or your answer.
Set is_follow_up to false when the latest message is a standalone documentation
question, even if similar words also appeared earlier.
""".strip()


class FollowUpClassification(BaseModel):
    is_follow_up: bool


@dataclass(frozen=True)
class FollowUpClassifier:
    llm_client: LLMClient

    def __init__(self, *, llm_client: LLMClient | None = None) -> None:
        object.__setattr__(self, "llm_client", llm_client or LLMClient())

    async def is_follow_up(
        self,
        *,
        question: str,
        conversation_history: list[ConversationTurn],
    ) -> bool:
        if not conversation_history:
            return False

        raw_answer = await self.llm_client.generate(
            system_prompt=FOLLOW_UP_SYSTEM_PROMPT,
            user_prompt=self._build_prompt(
                question=question,
                conversation_history=conversation_history,
            ),
        )
        return self._parse_response(raw_answer)

    @staticmethod
    def _build_prompt(*, question: str, conversation_history: list[ConversationTurn]) -> str:
        history_text = "\n".join(
            f"{turn.role}: {turn.content}" for turn in conversation_history[-10:]
        )
        return (
            "Conversation history:\n"
            f"{history_text}\n\n"
            "Latest user message:\n"
            f"{question}\n\n"
            "Classify whether the latest user message depends on the conversation history. "
            "Return JSON only."
        )

    @staticmethod
    def _parse_response(raw_answer: str) -> bool:
        try:
            payload = json.loads(raw_answer)
            classification = FollowUpClassification.model_validate(payload)
        except (json.JSONDecodeError, ValidationError):
            return False

        return classification.is_follow_up
