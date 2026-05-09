from pathlib import Path
import re

from openai import APIError, APITimeoutError, AsyncOpenAI, OpenAIError

from app.core.config import settings


class LLMServiceError(RuntimeError):
    pass


class LLMClient:
    def __init__(
        self,
        *,
        base_url: str = settings.openai_base_url,
        api_key: str = settings.openai_api_key,
        model: str = settings.llm_model,
        timeout_seconds: float = 120.0,
        client: AsyncOpenAI | None = None,
    ) -> None:
        self.model = model
        self.client = client or AsyncOpenAI(
            base_url=base_url.rstrip("/"),
            api_key=api_key,
            timeout=timeout_seconds,
        )

    async def generate(self, *, system_prompt: str, user_prompt: str) -> str:
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.1,
                stream=False,
            )
            content = response.choices[0].message.content
        except (APIError, APITimeoutError, OpenAIError, IndexError) as exc:
            raise LLMServiceError(f"LLM service request failed: {exc}") from exc

        if not isinstance(content, str) or not content.strip():
            raise LLMServiceError("LLM service returned an empty answer.")

        return sanitize_llm_answer(content)


def load_answer_system_prompt() -> str:
    prompt_path = Path(__file__).resolve().parents[1] / "prompts" / "answer_system_prompt.txt"
    return prompt_path.read_text(encoding="utf-8")


def sanitize_llm_answer(content: str) -> str:
    cleaned = content.strip()
    if "<channel|>" in cleaned:
        cleaned = cleaned.rsplit("<channel|>", 1)[-1]

    cleaned = re.sub(r"<\|channel\>.*?(?=<channel\|>|$)", "", cleaned, flags=re.DOTALL)
    cleaned = cleaned.replace("<channel|>", "")
    cleaned = cleaned.replace("<|channel>", "")
    return cleaned.strip()
