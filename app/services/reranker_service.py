from dataclasses import dataclass

import httpx

from app.core.config import settings


class RerankerServiceError(RuntimeError):
    pass


@dataclass(frozen=True)
class RerankResult:
    index: int
    relevance_score: float


class RerankerClient:
    def __init__(
        self,
        *,
        base_url: str = settings.reranker_base_url,
        model: str = settings.reranker_model,
        timeout_seconds: float = settings.reranker_timeout_seconds,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self._owns_client = client is None
        self.client = client or httpx.AsyncClient(timeout=timeout_seconds)

    async def rerank(self, *, query: str, documents: list[str]) -> list[RerankResult]:
        if not documents:
            return []

        try:
            response = await self.client.post(
                f"{self.base_url}/rerank",
                json={
                    "model": self.model,
                    "query": query,
                    "documents": documents,
                },
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise RerankerServiceError(f"Reranker service request failed: {exc}") from exc

        payload = response.json()
        results = payload.get("results")
        if not isinstance(results, list):
            raise RerankerServiceError("Reranker service returned an invalid response.")

        reranked_results: list[RerankResult] = []
        for item in results:
            if not isinstance(item, dict):
                raise RerankerServiceError("Reranker service returned an invalid result item.")

            index = item.get("index")
            relevance_score = item.get("relevance_score")
            if not isinstance(index, int) or not isinstance(relevance_score, int | float):
                raise RerankerServiceError("Reranker service returned an invalid result item.")
            if index < 0 or index >= len(documents):
                raise RerankerServiceError("Reranker service returned an out-of-range document index.")

            reranked_results.append(
                RerankResult(index=index, relevance_score=float(relevance_score))
            )

        return reranked_results

    async def aclose(self) -> None:
        if self._owns_client:
            await self.client.aclose()
