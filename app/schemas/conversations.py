from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.models.conversation import (
    CONVERSATION_TITLE_MAX_LENGTH,
    ConversationMessageRole,
    ConversationStatus,
)
from app.schemas.chat import ChatResponse


class ConversationCreate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=CONVERSATION_TITLE_MAX_LENGTH)


class ConversationUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=CONVERSATION_TITLE_MAX_LENGTH)

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        title = value.strip()
        if not title:
            raise ValueError("Title must not be blank.")
        return title


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
