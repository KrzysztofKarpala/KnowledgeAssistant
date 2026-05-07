from pathlib import Path
import re
from typing import Any

import httpx

from app.core.config import settings


class LLMServiceError(RuntimeError):
    pass


class LLMClient:
    def __init__(
        self,
        *,
        base_url: str = settings.llm_base_url,
        model: str = settings.llm_model,
        timeout_seconds: float = 120.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds

    async def generate(self, *, system_prompt: str, user_prompt: str) -> str:
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        "temperature": 0.1,
                        "stream": False,
                    },
                )
                response.raise_for_status()
                return self._parse_response(response.json())
        except httpx.HTTPError as exc:
            raise LLMServiceError(f"LLM service request failed: {exc}") from exc

    def _parse_response(self, payload: dict[str, Any]) -> str:
        choices = payload.get("choices")
        if not isinstance(choices, list) or not choices:
            raise LLMServiceError("LLM service returned an invalid response.")

        message = choices[0].get("message")
        if not isinstance(message, dict):
            raise LLMServiceError("LLM service returned an invalid message.")

        content = message.get("content")
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
