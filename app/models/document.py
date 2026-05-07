from datetime import date, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Date, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class DocumentStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active", index=True)
    version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    effective_from: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False, default=dict)
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

    chunks = relationship(
        "DocumentChunk",
        back_populates="document",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __init__(
        self,
        *,
        title: str,
        content: str,
        version: str | None,
        effective_from: date | None,
        metadata: dict[str, Any],
        _allow_direct_creation: bool = False,
    ) -> None:
        if not _allow_direct_creation:
            raise TypeError("Use Document.Create() to create a document.")

        self.title = title
        self.content = content
        self.status = DocumentStatus.ACTIVE
        self.version = version
        self.effective_from = effective_from
        self.metadata_ = metadata

    @staticmethod
    def create(
        *,
        title: str,
        content: str,
        version: str | None,
        effective_from: date | None,
        metadata: dict[str, Any],
    ) -> "Document":
        return Document(
            title=title,
            content=content,
            version=version,
            effective_from=effective_from,
            metadata=metadata,
            _allow_direct_creation=True,
        )

    def move_to_archived(self) -> None:
        self.status = DocumentStatus.ARCHIVED
