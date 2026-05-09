from openai import APIError, APITimeoutError, AsyncOpenAI, OpenAIError

from app.core.config import settings


class EmbeddingServiceError(RuntimeError):
    pass


class EmbeddingClient:
    def __init__(
        self,
        *,
        base_url: str = settings.openai_base_url,
        api_key: str = settings.openai_api_key,
        model: str = settings.embedding_model,
        timeout_seconds: float = settings.embedding_timeout_seconds,
        client: AsyncOpenAI | None = None,
    ) -> None:
        self.model = model
        self.client = client or AsyncOpenAI(
            base_url=base_url.rstrip("/"),
            api_key=api_key,
            timeout=timeout_seconds,
        )

    async def embed_many(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        try:
            response = await self.client.embeddings.create(
                model=self.model,
                input=texts,
            )
        except (APIError, APITimeoutError, OpenAIError) as exc:
            raise EmbeddingServiceError(f"Embedding service request failed: {exc}") from exc

        if not response.data:
            raise EmbeddingServiceError("Embedding service returned an invalid response.")

        embeddings_by_index: list[tuple[int, list[float]]] = []
        for index, item in enumerate(response.data):
            embedding = item.embedding
            if not embedding:
                raise EmbeddingServiceError("Embedding service returned an invalid embedding vector.")

            embeddings_by_index.append((item.index if item.index is not None else index, list(embedding)))

        return [embedding for _, embedding in sorted(embeddings_by_index, key=lambda item: item[0])]
