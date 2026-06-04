from collections.abc import AsyncIterator
from sqlalchemy.orm import Session

from app.rag.citations import CitationBuilder
from app.rag.calling_focus import calling_focus_prompt_block
from app.rag.grounding import GroundingValidator
from app.rag.memory import ConversationMemory
from app.rag.prompts import SYSTEM_PROMPT
from app.retrieval.hybrid import HybridSearchService
from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.search import Citation
from app.services.openai_client import OpenAIService


class RAGOrchestrator:
    def __init__(self) -> None:
        self.search = HybridSearchService()
        self.citations = CitationBuilder()
        self.memory = ConversationMemory()
        self.openai = OpenAIService()
        self.grounding = GroundingValidator()

    async def answer(self, db: Session, request: ChatRequest) -> ChatResponse:
        session, messages, citations = await self._prepare(db, request)
        answer = await self.openai.complete(messages, temperature=0.1)
        grounded, warnings = await self.grounding.validate(answer, citations)
        self.memory.save_message(db, session_id=session.id, role="user", content=request.message)
        self.memory.save_message(
            db,
            session_id=session.id,
            role="assistant",
            content=answer,
            citations=[citation.model_dump(mode="json") for citation in citations],
            metadata={"grounded": grounded, "warnings": warnings},
        )
        return ChatResponse(
            session_id=session.id,
            message=answer,
            citations=citations,
            grounded=grounded,
            warnings=warnings,
        )

    async def stream_answer(self, db: Session, request: ChatRequest) -> AsyncIterator[dict]:
        session, messages, citations = await self._prepare(db, request)
        yield {"type": "session", "session_id": str(session.id)}
        yield {"type": "citations", "citations": [citation.model_dump(mode="json") for citation in citations]}
        chunks: list[str] = []
        async for token in self.openai.stream_complete(messages, temperature=0.1):
            chunks.append(token)
            yield {"type": "delta", "content": token}
        answer = "".join(chunks)
        grounded, warnings = await self.grounding.validate(answer, citations)
        self.memory.save_message(db, session_id=session.id, role="user", content=request.message)
        self.memory.save_message(
            db,
            session_id=session.id,
            role="assistant",
            content=answer,
            citations=[citation.model_dump(mode="json") for citation in citations],
            metadata={"grounded": grounded, "warnings": warnings},
        )
        yield {"type": "grounding", "grounded": grounded, "warnings": warnings}
        yield {"type": "done"}

    async def _prepare(self, db: Session, request: ChatRequest):
        session = self.memory.get_or_create_session(
            db,
            session_id=request.session_id,
            user_id=request.user_id,
            language=request.language,
            mode=request.mode,
            first_message=request.message,
        )
        rewritten, chunks = await self.search.search(
            db,
            request.message,
            request.filters,
            language=request.language,
            use_reranker=True,
        )
        citations = self.citations.build(chunks)
        context = self.citations.context_block(chunks)
        history = self.memory.recent_messages(db, session.id)
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for item in history:
            if item.role in {"user", "assistant"}:
                messages.append({"role": item.role, "content": item.content})
        messages.append(
            {
                "role": "user",
                "content": (
                    f"Modo: {request.mode}\n"
                    f"{calling_focus_prompt_block(request.calling_focus)}\n\n"
                    f"Consulta original: {request.message}\n"
                    f"Consulta de recuperacion: {rewritten}\n\n"
                    f"CONTEXTO:\n{context}\n\n"
                    "Responde con citas numeradas como [1], [2]."
                ),
            }
        )
        return session, messages, citations
