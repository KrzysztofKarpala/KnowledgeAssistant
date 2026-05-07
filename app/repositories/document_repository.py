from collections.abc import Sequence
from typing import Any
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentStatus


class DocumentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        title: str,
        content: str,
        parent_id: UUID | None,
        version: str | None,
        effective_from: Any,
        metadata: dict[str, Any],
    ) -> Document:
        document = Document.create(
            title=title,
            content=content,
            parent_id=parent_id,
            version=version,
            effective_from=effective_from,
            metadata=metadata,
        )
        self.session.add(document)
        await self.session.commit()
        await self.session.refresh(document)
        return document

    async def list(self, *, limit: int = 100, offset: int = 0) -> Sequence[Document]:
        result = await self.session.scalars(
            select(Document).order_by(Document.created_at.desc()).limit(limit).offset(offset)
        )
        return result.all()

    async def get(self, document_id: UUID) -> Document | None:
        return await self.session.get(Document, document_id)

    async def list_active_by_title(self, title: str) -> Sequence[Document]:
        result = await self.session.scalars(
            select(Document).where(
                Document.title == title,
                Document.status == DocumentStatus.ACTIVE,
            )
        )
        return result.all()

    async def archive_active_by_title(self, title: str) -> int:
        documents = await self.list_active_by_title(title)
        for document in documents:
            document.move_to_archived()

        return len(documents)

    async def update(self, document: Document, values: dict[str, Any]) -> Document:
        for field, value in values.items():
            if field == "metadata":
                setattr(document, "metadata_", value)
            else:
                setattr(document, field, value)

        await self.session.commit()
        await self.session.refresh(document)
        return document

    async def delete(self, document_id: UUID) -> bool:
        result = await self.session.execute(delete(Document).where(Document.id == document_id))
        await self.session.commit()
        return result.rowcount > 0
