from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


StudyBlockType = Literal[
    "personal_note",
    "ai_doctrinal_analysis",
    "ai_quote",
    "ai_reference",
    "scripture_connection",
    "reflection_question",
    "powerful_phrase",
    "name_meaning",
    "calling_application",
    "manual_reference",
    "book_reference",
]

StudySourceType = Literal[
    "scripture",
    "church_manual",
    "book",
    "byu_speech",
    "discourse",
    "user_private_note",
    "library_document",
]

AiSuggestionMode = Literal["rapido", "profundo", "citas", "manuales", "nombres", "llamamiento"]


class StudyProjectPayload(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    scriptureReference: str | None = Field(default=None, max_length=240)
    scriptureText: str | None = None
    personalThought: str | None = None
    topic: str | None = Field(default=None, max_length=160)
    callingContext: str | None = Field(default=None, max_length=240)


class StudyProjectUpdatePayload(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=240)
    scriptureReference: str | None = Field(default=None, max_length=240)
    scriptureText: str | None = None
    personalThought: str | None = None
    topic: str | None = Field(default=None, max_length=160)
    callingContext: str | None = Field(default=None, max_length=240)
    archived: bool | None = None


class StudyBlockPayload(BaseModel):
    type: StudyBlockType = "personal_note"
    title: str = Field(min_length=1, max_length=240)
    content: str = Field(default="")
    sourceTitle: str | None = Field(default=None, max_length=300)
    sourceAuthor: str | None = Field(default=None, max_length=240)
    sourceUrl: str | None = None
    sourceReference: str | None = Field(default=None, max_length=300)
    quoteText: str | None = None
    isAiGenerated: bool = False
    isSaved: bool = True
    isDeleted: bool = False
    sortOrder: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class StudyBlockUpdatePayload(BaseModel):
    type: StudyBlockType | None = None
    title: str | None = Field(default=None, min_length=1, max_length=240)
    content: str | None = None
    sourceTitle: str | None = Field(default=None, max_length=300)
    sourceAuthor: str | None = Field(default=None, max_length=240)
    sourceUrl: str | None = None
    sourceReference: str | None = Field(default=None, max_length=300)
    quoteText: str | None = None
    isSaved: bool | None = None
    isDeleted: bool | None = None
    sortOrder: int | None = None
    metadata: dict[str, Any] | None = None


class StudySourcePayload(BaseModel):
    sourceType: StudySourceType
    title: str = Field(min_length=1, max_length=300)
    author: str | None = Field(default=None, max_length=240)
    url: str | None = None
    reference: str | None = Field(default=None, max_length=300)
    notes: str | None = None


class UserPrivateSourcePayload(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    author: str | None = Field(default=None, max_length=240)
    sourceType: StudySourceType = "user_private_note"
    citationText: str | None = Field(default=None, max_length=1200)
    personalNote: str | None = None
    tags: list[str] = Field(default_factory=list)

    @field_validator("tags")
    @classmethod
    def limit_tags(cls, value: list[str]) -> list[str]:
        return [tag.strip() for tag in value if tag.strip()][:20]


class AiSuggestPayload(BaseModel):
    prompt: str | None = Field(default=None, max_length=1200)
    blockTypes: list[StudyBlockType] = Field(default_factory=list)
    preferredSources: list[StudySourceType | str] = Field(default_factory=list)
    mode: AiSuggestionMode = "rapido"
    maxSuggestions: int = Field(default=6, ge=1, le=10)


class AiSuggestedBlock(BaseModel):
    type: StudyBlockType
    title: str
    content: str = ""
    quoteText: str | None = None
    sourceTitle: str | None = None
    sourceAuthor: str | None = None
    sourceUrl: str | None = None
    sourceReference: str | None = None
    sourceStatus: Literal["local", "referencia_sugerida", "idea_relacionada", "usuario"] = "idea_relacionada"
    sources: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AiSuggestResponse(BaseModel):
    suggestions: list[AiSuggestedBlock]
    cached: bool = False
    mode: AiSuggestionMode
    warnings: list[str] = Field(default_factory=list)
    localContext: list[dict[str, Any]] = Field(default_factory=list)
