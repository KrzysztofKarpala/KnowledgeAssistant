from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.core.database import Base
from app.models.enums import enum_values


class ConversationStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class ConversationMessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


CONVERSATION_TITLE_MAX_LENGTH = 80
DEFAULT_CONVERSATION_TITLES = {"new conversation", "untitled conversation"}


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    title: Mapped[str | None] = mapped_column(String(CONVERSATION_TITLE_MAX_LENGTH), nullable=True)
    status: Mapped[ConversationStatus] = mapped_column(
        Enum(ConversationStatus, values_callable=enum_values),
        nullable=False,
        default=ConversationStatus.ACTIVE,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    messages = relationship(
        "ConversationMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    @validates("title")
    def validate_title(self, key: str, title: str | None) -> str | None:
        if title is None:
            return None

        normalized = title.strip()
        if not normalized:
            raise ValueError("Conversation title must not be blank.")
        if len(normalized) > CONVERSATION_TITLE_MAX_LENGTH:
            raise ValueError(
                f"Conversation title must be {CONVERSATION_TITLE_MAX_LENGTH} characters or fewer."
            )
        return normalized


class ConversationMessage(Base):
    __tablename__ = "conversation_messages"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    conversation_id: Mapped[UUID] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[ConversationMessageRole] = mapped_column(
        Enum(ConversationMessageRole, values_callable=enum_values),
        nullable=False,
        index=True,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    cited_chunk_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )

    conversation = relationship("Conversation", back_populates="messages")
