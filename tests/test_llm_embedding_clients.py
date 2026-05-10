from types import SimpleNamespace

import pytest

from app.services.embedding_service import EmbeddingClient, EmbeddingServiceError
from app.services.llm_service import LLMClient, LLMServiceError


class ChatCompletionsMock:
    def __init__(self, content: str | None) -> None:
        self.content = content
        self.kwargs = None

    async def create(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content=self.content),
                )
            ]
        )


class EmbeddingsMock:
    def __init__(self, data) -> None:
        self.data = data

    async def create(self, **kwargs):
        return SimpleNamespace(data=self.data)


def llm_client_mock(content: str | None):
    completions = ChatCompletionsMock(content)
    return SimpleNamespace(chat=SimpleNamespace(completions=completions))


def embedding_client_mock(data):
    return SimpleNamespace(embeddings=EmbeddingsMock(data))


async def test_llm_client_generates_sanitized_answer():
    openai_client = llm_client_mock("  answer <|channel>analysis  ")
    client = LLMClient(client=openai_client)

    answer = await client.generate(system_prompt="system", user_prompt="user")

    assert answer == "answer"
    assert openai_client.chat.completions.kwargs["response_format"] == {"type": "json_object"}


async def test_llm_client_rejects_empty_answer():
    client = LLMClient(client=llm_client_mock(" "))

    with pytest.raises(LLMServiceError, match="empty answer"):
        await client.generate(system_prompt="system", user_prompt="user")


async def test_embedding_client_returns_embeddings_in_response_order():
    client = EmbeddingClient(
        client=embedding_client_mock(
            [
                SimpleNamespace(index=1, embedding=[3, 4]),
                SimpleNamespace(index=0, embedding=[1, 2]),
            ]
        )
    )

    embeddings = await client.embed_many(["first", "second"])

    assert embeddings == [[1, 2], [3, 4]]


async def test_embedding_client_rejects_empty_embedding_response():
    client = EmbeddingClient(client=embedding_client_mock([]))

    with pytest.raises(EmbeddingServiceError, match="invalid response"):
        await client.embed_many(["question"])
