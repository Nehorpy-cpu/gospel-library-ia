from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.retrieval.scripture_refs import extract_scripture_refs
from app.schemas.search import Citation, MetadataFilter


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    session_id: UUID | None = None
    user_id: UUID | None = None
    mode: str = "doctrinal_assistant"
    language: str | None = None
    filters: MetadataFilter = Field(default_factory=MetadataFilter)
    stream: bool = True

    @model_validator(mode="after")
    def include_message_scripture_refs(self):
        refs = set(self.filters.scripture_refs or [])
        refs.update(extract_scripture_refs(self.message))
        self.filters.scripture_refs = sorted(refs) or None
        return self


class ChatResponse(BaseModel):
    session_id: UUID
    message: str
    citations: list[Citation]
    grounded: bool
    warnings: list[str] = Field(default_factory=list)
