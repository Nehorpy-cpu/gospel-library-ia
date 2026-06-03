from abc import ABC, abstractmethod

from bs4 import BeautifulSoup

from app.extractors.assets import extract_assets
from app.extractors.content_cleaner import clean_html, html_to_text
from app.extractors.metadata import (
    detect_language,
    extract_author,
    extract_category,
    extract_published_at,
    extract_scripture_refs,
    extract_tags,
    extract_title,
)
from app.schemas.document import ExtractedDocument
from app.utils.source_types import source_type_for_url


class BaseParser(ABC):
    source_key: str

    @abstractmethod
    def can_parse(self, url: str) -> bool:
        raise NotImplementedError

    def parse(self, url: str, html: str) -> ExtractedDocument:
        cleaned_html = clean_html(html)
        soup = BeautifulSoup(cleaned_html, "lxml")
        text = html_to_text(cleaned_html)
        return ExtractedDocument(
            source_key=self.source_key,
            url=url,
            title=extract_title(soup, url, text),
            author=extract_author(soup),
            published_at=extract_published_at(soup, text, url),
            language=detect_language(text, url),
            category=extract_category(soup),
            tags=extract_tags(soup),
            scripture_refs=extract_scripture_refs(text),
            text=text,
            html=cleaned_html,
            assets=extract_assets(html, url),
            metadata={
                "source_url": url,
                "source_type": source_type_for_url(self.source_key, url),
            },
        )
