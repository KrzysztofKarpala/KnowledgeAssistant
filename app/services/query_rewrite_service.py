import json
from dataclasses import dataclass

from pydantic import BaseModel, Field, ValidationError, field_validator

from app.services.answer_service import ConversationTurn
from app.services.llm_service import LLMClient, LLMServiceError


QUERY_REWRITE_SYSTEM_PROMPT = """
You rewrite conversational user messages into standalone retrieval questions for a documentation search system.

Return only valid JSON with this exact shape:
{"query":"..."}

Rules:
- Preserve the user's actual intent.
- Resolve pronouns, comparisons, and fragments using conversation history.
- Include important entities from prior turns when the latest message depends on them.
- Do not answer the question.
- Do not add facts that are not present in the latest message or conversation history.
- Keep the query concise and specific.
""".strip()


class RewrittenQuery(BaseModel):
    query: str = Field(min_length=1, max_length=500)

    @field_validator("query")
    @classmethod
    def validate_query(cls, value: str) -> str:
        query = " ".join(value.strip().split())
        if not query:
            raise ValueError("Query must not be blank.")
        return query


@dataclass(frozen=True)
class QueryRewriteService:
    llm_client: LLMClient

    def __init__(self, *, llm_client: LLMClient | None = None) -> None:
        object.__setattr__(self, "llm_client", llm_client or LLMClient())

    async def rewrite(
        self,
        *,
        question: str,
        conversation_history: list[ConversationTurn],
    ) -> str:
        if not conversation_history:
            return question

        raw_answer = await self.llm_client.generate(
            system_prompt=QUERY_REWRITE_SYSTEM_PROMPT,
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
            "Rewrite the latest user message into a standalone retrieval question. "
            "Return JSON only."
        )

    @staticmethod
    def _parse_response(raw_answer: str) -> str:
        try:
            payload = json.loads(raw_answer)
            rewritten = RewrittenQuery.model_validate(payload)
        except (json.JSONDecodeError, ValidationError) as exc:
            raise LLMServiceError("LLM service returned an invalid rewritten query.") from exc

        return rewritten.query
