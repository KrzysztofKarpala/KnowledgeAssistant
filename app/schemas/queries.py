from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class QueryLogResponse(BaseModel):
    id: UUID
    question: str
    answer: str
    used_sources: list[dict[str, Any]]
    created_at: datetime
