from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.search import Citation, MetadataFilter


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    session_id: UUID | None = None
    user_id: UUID | None = None
    mode: str = "doctrinal_assistant"
    language: str | None = None
    filters: MetadataFilter = Field(default_factory=MetadataFilter)
    stream: bool = True


class ChatResponse(BaseModel):
    session_id: UUID
    message: str
    citations: list[Citation]
    grounded: bool
    warnings: list[str] = Field(default_factory=list)
