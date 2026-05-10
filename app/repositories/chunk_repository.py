from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import delete, desc, func, nulls_last, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentStatus
from app.models.document_chunk import DocumentChunk

class ChunkRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def replace_for_document(
        self,
        *,
        document_id: UUID,
        chunks: Sequence[str],
        embeddings: Sequence[list[float]],
    ) -> int:
        await self.session.execute(
            delete(DocumentChunk).where(DocumentChunk.document_id == document_id)
        )

        for index, (content, embedding) in enumerate(zip(chunks, embeddings, strict=True)):
            self.session.add(
                DocumentChunk(
                    document_id=document_id,
                    chunk_index=index,
                    content=content,
                    embedding=embedding,
                    metadata_={},
                )
            )

        await self.session.commit()
        return len(chunks)

    async def count_for_document(self, document_id: UUID) -> int:
        result = await self.session.scalars(
            select(DocumentChunk.id).where(DocumentChunk.document_id == document_id)
        )
        return len(result.all())

    async def search_similar_for_document(
        self,
        *,
        document_id: UUID,
        embedding: list[float],
        active_only: bool = True,
    ) -> tuple[DocumentChunk, Document, float] | None:
        distance = DocumentChunk.embedding.cosine_distance(embedding).label("distance")
        statement = (
            select(DocumentChunk, Document, distance)
            .join(Document, Document.id == DocumentChunk.document_id)
            .where(DocumentChunk.document_id == document_id)
            .order_by(distance.asc(), DocumentChunk.chunk_index.asc())
            .limit(1)
        )

        if active_only:
            statement = statement.where(Document.status == DocumentStatus.ACTIVE)

        result = await self.session.execute(statement)
        row = result.first()
        if row is None:
            return None

        chunk, document, raw_distance = row
        return chunk, document, float(raw_distance)

    async def search_similar(
        self,
        *,
        embedding: list[float],
        limit: int,
        active_only: bool = True,
    ) -> Sequence[tuple[DocumentChunk, Document, float]]:
        distance = DocumentChunk.embedding.cosine_distance(embedding).label("distance")
        statement = (
            select(DocumentChunk, Document, distance)
            .join(Document, Document.id == DocumentChunk.document_id)
            .order_by(
                distance.asc(),
                nulls_last(desc(Document.effective_from)),
                Document.created_at.desc(),
            )
            .limit(limit)
        )

        if active_only:
            statement = statement.where(Document.status == DocumentStatus.ACTIVE)

        result = await self.session.execute(statement)
        return [(chunk, document, float(raw_distance)) for chunk, document, raw_distance in result.all()]

    async def search_keyword(
        self,
        *,
        query: str,
        limit: int,
        active_only: bool = True,
        search_config: str = "english",
    ) -> Sequence[tuple[DocumentChunk, Document, float]]:
        search_query = func.websearch_to_tsquery(search_config, query)
        search_vector = func.to_tsvector(search_config, DocumentChunk.content)
        rank = func.ts_rank_cd(search_vector, search_query).label("rank")
        statement = (
            select(DocumentChunk, Document, rank)
            .join(Document, Document.id == DocumentChunk.document_id)
            .where(search_vector.op("@@")(search_query))
            .order_by(
                rank.desc(),
                nulls_last(desc(Document.effective_from)),
                Document.created_at.desc(),
                DocumentChunk.chunk_index.asc(),
            )
            .limit(limit)
        )

        if active_only:
            statement = statement.where(Document.status == DocumentStatus.ACTIVE)

        result = await self.session.execute(statement)
        return [(chunk, document, float(raw_rank)) for chunk, document, raw_rank in result.all()]
