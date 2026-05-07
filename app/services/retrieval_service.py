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
    parent_id: UUID | None
    document_title: str
    document_version: str | None
    effective_from: date | None
    chunk_id: UUID
    chunk_index: int
    content: str
    similarity: float
    source_role: str = "semantic_match"


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

        chunk_repository = ChunkRepository(self.session)
        rows = await chunk_repository.search_similar(
            embedding=query_embedding,
            limit=limit,
            active_only=active_only,
        )

        retrieved_chunks = [
            RetrievedChunk(
                document_id=document.id,
                parent_id=document.parent_id,
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
            for chunk in await self._include_parent_chunks(
                chunk_repository=chunk_repository,
                chunks=retrieved_chunks,
                query_embedding=query_embedding,
                active_only=active_only,
            )
            if chunk.similarity >= settings.retrieval_min_similarity
        ]

    async def _include_parent_chunks(
        self,
        *,
        chunk_repository: ChunkRepository,
        chunks: list[RetrievedChunk],
        query_embedding: list[float],
        active_only: bool,
    ) -> list[RetrievedChunk]:
        expanded_chunks = list(chunks)
        seen_document_ids = {chunk.document_id for chunk in expanded_chunks}
        index = 0

        while index < len(expanded_chunks):
            chunk = expanded_chunks[index]
            index += 1
            if chunk.parent_id is None or chunk.parent_id in seen_document_ids:
                continue

            parent_row = await chunk_repository.search_similar_for_document(
                document_id=chunk.parent_id,
                embedding=query_embedding,
                active_only=active_only,
            )
            if parent_row is None:
                continue

            parent_chunk, parent_document, parent_distance = parent_row
            expanded_chunks.append(
                RetrievedChunk(
                    document_id=parent_document.id,
                    parent_id=parent_document.parent_id,
                    document_title=parent_document.title,
                    document_version=parent_document.version,
                    effective_from=parent_document.effective_from,
                    chunk_id=parent_chunk.id,
                    chunk_index=parent_chunk.chunk_index,
                    content=parent_chunk.content,
                    similarity=max(0.0, min(1.0, 1.0 - parent_distance)),
                    source_role="hierarchy_parent",
                )
            )
            seen_document_ids.add(parent_document.id)

        return expanded_chunks
