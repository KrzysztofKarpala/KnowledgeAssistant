from collections.abc import Sequence
from typing import Any
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation, ConversationMessage, ConversationMessageRole


class ConversationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, *, title: str | None = None) -> Conversation:
        conversation = Conversation(title=title)
        self.session.add(conversation)
        await self.session.commit()
        await self.session.refresh(conversation)
        return conversation

    async def get(self, conversation_id: UUID) -> Conversation | None:
        return await self.session.get(Conversation, conversation_id)

    async def update_title(self, *, conversation: Conversation, title: str) -> Conversation:
        conversation.title = title
        await self.session.commit()
        await self.session.refresh(conversation)
        return conversation

    async def list(self, *, limit: int = 100, offset: int = 0) -> Sequence[Conversation]:
        result = await self.session.scalars(
            select(Conversation)
            .order_by(Conversation.updated_at.desc(), Conversation.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return result.all()

    async def delete(self, conversation_id: UUID) -> bool:
        result = await self.session.execute(
            delete(Conversation).where(Conversation.id == conversation_id)
        )
        await self.session.commit()
        return result.rowcount > 0


class ConversationMessageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        conversation_id: UUID,
        role: ConversationMessageRole,
        content: str,
        cited_chunk_ids: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ConversationMessage:
        message = ConversationMessage(
            conversation_id=conversation_id,
            role=role,
            content=content,
            cited_chunk_ids=cited_chunk_ids or [],
            metadata_=metadata or {},
        )
        self.session.add(message)
        await self.session.commit()
        await self.session.refresh(message)
        return message

    async def list_for_conversation(
        self,
        *,
        conversation_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[ConversationMessage]:
        result = await self.session.scalars(
            select(ConversationMessage)
            .where(ConversationMessage.conversation_id == conversation_id)
            .order_by(ConversationMessage.created_at.asc())
            .limit(limit)
            .offset(offset)
        )
        return result.all()

    async def list_recent_for_conversation(
        self,
        *,
        conversation_id: UUID,
        limit: int,
    ) -> Sequence[ConversationMessage]:
        result = await self.session.scalars(
            select(ConversationMessage)
            .where(ConversationMessage.conversation_id == conversation_id)
            .order_by(ConversationMessage.created_at.desc())
            .limit(limit)
        )
        return list(reversed(result.all()))
