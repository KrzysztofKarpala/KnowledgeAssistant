from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(min_length=1)


class RetrievalRequest(BaseModel):
    question: str = Field(min_length=1)
    limit: int = Field(default=5, ge=1, le=50)
    active_only: bool = True


class SourceReference(BaseModel):
    document_id: UUID
    parent_id: UUID | None = None
    document_title: str
    document_version: str | None = None
    effective_from: date | None = None
    chunk_id: UUID
    chunk_index: int
    similarity: float
    source_role: str = "semantic_match"


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceReference]
    cited_chunk_ids: list[UUID]
    confidence: str


class RetrievedChunkResponse(SourceReference):
    content: str


class RetrievalResponse(BaseModel):
    question: str
    results: list[RetrievedChunkResponse]
