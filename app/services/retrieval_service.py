from dataclasses import dataclass
from datetime import date
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.repositories.chunk_repository import ChunkRepository
from app.services.embedding_service import EmbeddingClient


@dataclass(frozen=True)
class RetrievedChunk:
    document_id: UUID
    document_title: str
    document_version: str | None
    effective_from: date | None
    chunk_id: UUID
    chunk_index: int
    content: str
    similarity: float


class RetrievalService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        embedding_client: EmbeddingClient | None = None,
    ) -> None:
        self.session = session
        self.embedding_client = embedding_client or EmbeddingClient()

    async def retrieve(
        self,
        *,
        question: str,
        limit: int = settings.top_k,
        active_only: bool = True,
    ) -> list[RetrievedChunk]:
        embeddings = await self.embedding_client.embed_many([question])
        query_embedding = embeddings[0]

        rows = await ChunkRepository(self.session).search_similar(
            embedding=query_embedding,
            limit=limit,
            active_only=active_only,
        )

        retrieved_chunks = [
            RetrievedChunk(
                document_id=document.id,
                document_title=document.title,
                document_version=document.version,
                effective_from=document.effective_from,
                chunk_id=chunk.id,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                similarity=max(0.0, min(1.0, 1.0 - distance)),
            )
            for chunk, document, distance in rows
        ]

        return [
            chunk
            for chunk in retrieved_chunks
            if chunk.similarity >= settings.retrieval_min_similarity
        ]
