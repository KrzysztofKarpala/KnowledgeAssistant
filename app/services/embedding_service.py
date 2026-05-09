from typing import Any

import httpx

from app.core.config import settings


class EmbeddingServiceError(RuntimeError):
    pass


class EmbeddingClient:
    def __init__(
        self,
        *,
        base_url: str = settings.embedding_base_url,
        model: str = settings.embedding_model,
        timeout_seconds: float = settings.embedding_timeout_seconds,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds

    async def embed_many(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                if self.base_url.endswith("/v1"):
                    return await self._embed_many_openai_compatible(client, texts)

                response = await client.post(
                    f"{self.base_url}/api/embed",
                    json={"model": self.model, "input": texts},
                )
                if response.status_code == 404:
                    return await self._embed_many_legacy_ollama(client, texts)

                response.raise_for_status()
                return self._parse_embed_response(response.json())
        except httpx.HTTPError as exc:
            raise EmbeddingServiceError(f"Embedding service request failed: {exc}") from exc

    async def _embed_many_openai_compatible(
        self,
        client: httpx.AsyncClient,
        texts: list[str],
    ) -> list[list[float]]:
        response = await client.post(
            f"{self.base_url}/embeddings",
            json={"model": self.model, "input": texts},
        )
        response.raise_for_status()
        payload = response.json()
        data = payload.get("data")
        if not isinstance(data, list):
            raise EmbeddingServiceError("Embedding service returned an invalid response.")

        embeddings_by_index: list[tuple[int, list[float]]] = []
        for item in data:
            if not isinstance(item, dict):
                raise EmbeddingServiceError("Embedding service returned an invalid embedding item.")

            embedding = item.get("embedding")
            index = item.get("index", len(embeddings_by_index))
            if not isinstance(embedding, list):
                raise EmbeddingServiceError("Embedding service returned an invalid embedding vector.")

            embeddings_by_index.append((int(index), [float(value) for value in embedding]))

        return [embedding for _, embedding in sorted(embeddings_by_index, key=lambda item: item[0])]

    async def _embed_many_legacy_ollama(
        self,
        client: httpx.AsyncClient,
        texts: list[str],
    ) -> list[list[float]]:
        embeddings: list[list[float]] = []
        for text in texts:
            response = await client.post(
                f"{self.base_url}/api/embeddings",
                json={"model": self.model, "prompt": text},
            )
            response.raise_for_status()
            payload = response.json()
            embedding = payload.get("embedding")
            if not isinstance(embedding, list):
                raise EmbeddingServiceError("Embedding service returned an invalid response.")
            embeddings.append([float(value) for value in embedding])

        return embeddings

    @staticmethod
    def _parse_embed_response(payload: dict[str, Any]) -> list[list[float]]:
        embeddings = payload.get("embeddings")
        if not isinstance(embeddings, list):
            raise EmbeddingServiceError("Embedding service returned an invalid response.")

        return [[float(value) for value in embedding] for embedding in embeddings]
