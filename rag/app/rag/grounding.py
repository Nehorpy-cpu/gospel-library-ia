import json

from app.rag.prompts import GROUNDING_SYSTEM
from app.schemas.search import Citation
from app.services.openai_client import OpenAIService


class GroundingValidator:
    def __init__(self) -> None:
        self.openai = OpenAIService()

    async def validate(self, answer: str, citations: list[Citation]) -> tuple[bool, list[str]]:
        if not citations:
            return False, ["No se recuperaron fuentes para fundamentar la respuesta."]
        context = "\n\n".join(f"[{c.citation_id}] {c.quote}" for c in citations)
        messages = [
            {"role": "system", "content": GROUNDING_SYSTEM},
            {"role": "user", "content": f"FUENTES:\n{context}\n\nRESPUESTA:\n{answer}"},
        ]
        try:
            raw = await self.openai.complete(messages, temperature=0)
            parsed = json.loads(raw)
            return bool(parsed.get("grounded")), list(parsed.get("warnings") or [])
        except Exception:
            has_citation_markers = any(f"[{c.citation_id}]" in answer for c in citations)
            warnings = [] if has_citation_markers else ["La respuesta no contiene marcadores de cita claros."]
            return has_citation_markers, warnings
