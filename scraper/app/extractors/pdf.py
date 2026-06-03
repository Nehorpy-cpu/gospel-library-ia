from dataclasses import dataclass

import fitz

from app.core.config import get_settings
from app.extractors.content_cleaner import compact_text


@dataclass(frozen=True)
class PdfExtractionResult:
    text: str
    pages: int
    needs_ocr: bool


def extract_pdf_text(pdf_bytes: bytes) -> PdfExtractionResult:
    settings = get_settings()
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page_texts: list[str] = []
    low_density_pages = 0
    for page in doc:
        text = page.get_text("text")
        if len(text.strip()) < settings.pdf_text_density_threshold:
            low_density_pages += 1
        page_texts.append(text)
    text = compact_text("\n\n".join(page_texts))
    needs_ocr = settings.ocr_enabled and bool(doc) and low_density_pages / len(doc) > 0.35
    return PdfExtractionResult(text=text, pages=len(doc), needs_ocr=needs_ocr)
