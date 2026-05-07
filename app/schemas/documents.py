from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class DocumentCreate(BaseModel):
    title: str = Field(min_length=1)
    content: str = Field(min_length=1)
    status: str = "active"
    version: str | None = None
    effective_from: date | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class DocumentUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1)
    content: str | None = Field(default=None, min_length=1)
    status: str | None = None
    version: str | None = None
    effective_from: date | None = None
    metadata: dict[str, Any] | None = None


class DocumentCreateResponse(BaseModel):
    id: UUID
    title: str
    chunks_created: int


class DocumentResponse(BaseModel):
    id: UUID
    title: str
    content: str
    status: str
    version: str | None = None
    effective_from: date | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
