from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.conversation import ConversationMessageRole, ConversationStatus
from app.schemas.chat import ChatResponse


class ConversationCreate(BaseModel):
    title: str | None = Field(default=None, min_length=1)


class ConversationResponse(BaseModel):
    id: UUID
    title: str | None = None
    status: ConversationStatus
    created_at: datetime
    updated_at: datetime


class ConversationMessageCreate(BaseModel):
    content: str = Field(min_length=1)


class ConversationMessageResponse(BaseModel):
    id: UUID
    conversation_id: UUID
    role: ConversationMessageRole
    content: str
    cited_chunk_ids: list[UUID] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class ConversationChatResponse(ChatResponse):
    conversation_id: UUID
    user_message_id: UUID
    assistant_message_id: UUID
