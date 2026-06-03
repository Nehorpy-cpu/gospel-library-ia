from dataclasses import dataclass

import fitz

from app.core.config import get_settings


@dataclass(frozen=True)
class OcrResult:
    text: str
    pages: int


def run_pdf_ocr(pdf_bytes: bytes) -> OcrResult:
    settings = get_settings()
    try:
        import pytesseract
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError("OCR dependencies are missing. Install project with [ocr].") from exc

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page_texts: list[str] = []
    for page in doc:
        pix = page.get_pixmap(dpi=220, alpha=False)
        image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        page_texts.append(pytesseract.image_to_string(image, lang=settings.ocr_language))
    return OcrResult(text="\n\n".join(page_texts).strip(), pages=len(doc))
