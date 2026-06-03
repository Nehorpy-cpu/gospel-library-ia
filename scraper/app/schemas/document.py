from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ExtractedAsset(BaseModel):
    url: str
    asset_type: str
    mime_type: str | None = None


class ExtractedDocument(BaseModel):
    source_key: str
    url: str
    title: str
    author: str | None = None
    published_at: datetime | None = None
    language: str | None = None
    category: str | None = None
    tags: list[str] = Field(default_factory=list)
    scripture_refs: list[str] = Field(default_factory=list)
    text: str
    html: str | None = None
    assets: list[ExtractedAsset] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
