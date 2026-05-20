import json
from dataclasses import dataclass

from pydantic import BaseModel, Field, ValidationError, field_validator

from app.models.conversation import CONVERSATION_TITLE_MAX_LENGTH
from app.services.llm_service import LLMClient, LLMServiceError


CONVERSATION_TITLE_SYSTEM_PROMPT = f"""
You generate concise conversation titles for a documentation assistant.

Return only valid JSON with this exact shape:
{{"title":"..."}}

Rules:
- Use the user's first message as the source.
- Write a short, specific title.
- Do not answer the question.
- Do not include quotation marks, trailing punctuation, markdown, or labels.
- The title must be {CONVERSATION_TITLE_MAX_LENGTH} characters or fewer.
""".strip()


class GeneratedConversationTitle(BaseModel):
    title: str = Field(min_length=1, max_length=CONVERSATION_TITLE_MAX_LENGTH)

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        title = value.strip().strip("\"'`.,;:!?")
        if not title:
            raise ValueError("Title must not be blank.")
        return title


@dataclass(frozen=True)
class ConversationTitleService:
    llm_client: LLMClient

    def __init__(self, *, llm_client: LLMClient | None = None) -> None:
        object.__setattr__(self, "llm_client", llm_client or LLMClient())

    async def generate_title(self, *, first_user_message: str) -> str:
        raw_answer = await self.llm_client.generate(
            system_prompt=CONVERSATION_TITLE_SYSTEM_PROMPT,
            user_prompt=(
                "Generate a conversation title for this first user message:\n"
                f"{first_user_message}"
            ),
        )
        return self._parse_response(raw_answer)

    @staticmethod
    def _parse_response(raw_answer: str) -> str:
        try:
            payload = json.loads(raw_answer)
            generated = GeneratedConversationTitle.model_validate(payload)
        except (json.JSONDecodeError, ValidationError) as exc:
            raise LLMServiceError("LLM service returned an invalid conversation title.") from exc

        return generated.title
