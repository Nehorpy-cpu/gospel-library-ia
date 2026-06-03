import json
from datetime import UTC, datetime
from urllib.request import Request as UrlRequest
from urllib.request import urlopen
from uuid import uuid4

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from redis import Redis
from sqlalchemy import text
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from app.core.config import get_settings
from app.db.session import get_db
from app.rag.orchestrator import RAGOrchestrator
from app.rag.citations import CitationBuilder
from app.retrieval.bm25 import BM25Retriever
from app.retrieval.hybrid import HybridSearchService
from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.search import IndexRequest, SearchRequest, SearchResponse, SearchResult
from app.services.qdrant_service import QdrantService
from app.workers.tasks import index_documents_task, index_pending_task

router = APIRouter()
settings = get_settings()
SEMANTIC_UNAVAILABLE_WARNING = "Busqueda semantica no disponible todavia."
MISSING_OPENAI_API_KEY_RESPONSE = {
    "error": "OPENAI_API_KEY is required for semantic search and chat",
    "status": "missing_api_key",
}


def _check_postgres(db: Session) -> str:
    try:
        db.execute(text("select 1"))
        return "ok"
    except Exception:
        return "error"


def _check_redis() -> str:
    try:
        Redis.from_url(settings.redis_url, socket_connect_timeout=2, socket_timeout=2).ping()
        return "ok"
    except Exception:
        return "error"


def _check_qdrant() -> str:
    try:
        request = UrlRequest(f"{settings.qdrant_url.rstrip('/')}/healthz")
        with urlopen(request, timeout=2) as response:
            return "ok" if response.status < 500 else "error"
    except Exception:
        return "error"


def _check_openai_api_key() -> str:
    return "ok" if settings.openai_api_key.strip() else "error"


def _status_payload(db: Session) -> dict:
    dependencies = {
        "postgres": _check_postgres(db),
        "redis": _check_redis(),
        "qdrant": _check_qdrant(),
        "openai": _check_openai_api_key(),
    }
    openai_missing = dependencies["openai"] == "error"
    return {
        "status": "degraded" if openai_missing else "healthy",
        "service": "gospel-library-rag",
        "timestamp": datetime.now(UTC).isoformat(),
        "dependencies": dependencies,
        "configuration": {
            "openai_api_key": "missing" if openai_missing else "configured",
        },
        "error": MISSING_OPENAI_API_KEY_RESPONSE["error"] if openai_missing else None,
    }


def _missing_openai_api_key() -> bool:
    return not settings.openai_api_key.strip()


def _missing_openai_response() -> JSONResponse:
    return JSONResponse(status_code=503, content=MISSING_OPENAI_API_KEY_RESPONSE)


def _qdrant_points_count() -> int:
    return QdrantService().points_count()


def _is_openai_quota_error(exc: Exception) -> bool:
    value = str(exc).lower()
    return "insufficient_quota" in value or "quota" in value or "rate limit" in value or "429" in value


def _search_response(
    request: SearchRequest,
    rewritten: str | None,
    chunks,
    *,
    warnings: list[str] | None = None,
    mode: str = "hybrid",
) -> SearchResponse:
    return SearchResponse(
        query=request.query,
        rewritten_query=rewritten,
        mode=mode,
        warnings=warnings or [],
        results=[
            SearchResult(
                chunk_id=chunk.chunk_id,
                document_id=chunk.document_id,
                title=chunk.title,
                author=chunk.author,
                source_key=chunk.source_key,
                canonical_url=chunk.canonical_url,
                language=chunk.language,
                section_title=chunk.section_title,
                snippet=chunk.citation_quote(520),
                score=chunk.final_score,
                semantic_score=chunk.semantic_score,
                bm25_score=chunk.bm25_score,
                rerank_score=chunk.rerank_score,
                metadata=chunk.metadata,
            )
            for chunk in chunks
        ],
    )


def _textual_search_response(request: SearchRequest, db: Session, warnings: list[str] | None = None) -> SearchResponse:
    chunks = BM25Retriever().search(db, request.query, request.filters, limit=request.limit)
    return _search_response(
        request,
        rewritten=None,
        chunks=chunks[: request.limit],
        warnings=warnings or [SEMANTIC_UNAVAILABLE_WARNING],
        mode="textual_fallback",
    )


def _no_vectors_chat_response(request: ChatRequest, db: Session) -> ChatResponse:
    chunks = BM25Retriever().search(db, request.message, request.filters, limit=5)
    citations = CitationBuilder().build(chunks)
    warnings = [SEMANTIC_UNAVAILABLE_WARNING]
    if _missing_openai_api_key():
        warnings.insert(0, MISSING_OPENAI_API_KEY_RESPONSE["error"])
    if citations:
        titles = ", ".join(f"[{citation.citation_id}] {citation.title}" for citation in citations)
        message = (
            "Busqueda semantica no disponible todavia. "
            "No puedo generar una respuesta IA completa con embeddings, "
            f"pero encontre fuentes textuales relacionadas: {titles}"
        )
    else:
        message = (
            "Busqueda semantica no disponible todavia. "
            "No puedo generar una respuesta IA completa y no encontre fuentes textuales locales relacionadas."
        )
    return ChatResponse(
        session_id=request.session_id or uuid4(),
        message=message,
        citations=citations,
        grounded=bool(citations),
        warnings=warnings,
    )


@router.get("/")
def root():
    return {
        "service": "gospel-library-rag",
        "status": "ok",
        "docs": "/docs",
        "health": "/health",
    }


@router.get("/health")
def health(db: Session = Depends(get_db)):
    return _status_payload(db)


@router.get("/ready")
def ready(db: Session = Depends(get_db)):
    payload = _status_payload(db)
    if any(status != "ok" for status in payload["dependencies"].values()):
        return JSONResponse(status_code=503, content=payload)
    return payload


@router.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest, db: Session = Depends(get_db)):
    if _missing_openai_api_key():
        return _textual_search_response(
            request,
            db,
            [SEMANTIC_UNAVAILABLE_WARNING, MISSING_OPENAI_API_KEY_RESPONSE["error"]],
        )
    if _qdrant_points_count() <= 0:
        return _textual_search_response(request, db)
    try:
        rewritten, chunks = await HybridSearchService().search(
            db,
            request.query,
            request.filters,
            language=request.language,
            limit=request.limit,
            use_reranker=request.use_reranker,
        )
        return _search_response(request, rewritten, chunks)
    except Exception as exc:
        warnings = [SEMANTIC_UNAVAILABLE_WARNING]
        if _is_openai_quota_error(exc):
            warnings.append("OpenAI quota is unavailable; using PostgreSQL text search.")
        return _textual_search_response(request, db, warnings)


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, db: Session = Depends(get_db)):
    if _qdrant_points_count() <= 0:
        return _no_vectors_chat_response(request, db)
    if _missing_openai_api_key():
        return _missing_openai_response()
    return await RAGOrchestrator().answer(db, request)


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest, db: Session = Depends(get_db)):
    if _qdrant_points_count() <= 0:
        fallback = _no_vectors_chat_response(request, db)

        async def fallback_events():
            yield {"event": "session", "data": json.dumps({"type": "session", "session_id": str(fallback.session_id)})}
            yield {
                "event": "citations",
                "data": json.dumps(
                    {"type": "citations", "citations": [item.model_dump(mode="json") for item in fallback.citations]},
                    default=str,
                ),
            }
            yield {"event": "delta", "data": json.dumps({"type": "delta", "content": fallback.message})}
            yield {
                "event": "grounding",
                "data": json.dumps(
                    {"type": "grounding", "grounded": fallback.grounded, "warnings": fallback.warnings}
                ),
            }
            yield {"event": "done", "data": json.dumps({"type": "done"})}

        return EventSourceResponse(fallback_events())
    if _missing_openai_api_key():
        return _missing_openai_response()

    async def events():
        async for event in RAGOrchestrator().stream_answer(db, request):
            yield {"event": event["type"], "data": json.dumps(event, default=str)}

    return EventSourceResponse(events())


@router.post("/admin/index")
def index(request: IndexRequest):
    if _missing_openai_api_key():
        return _missing_openai_response()
    if request.document_ids:
        task = index_documents_task.delay([str(item) for item in request.document_ids], request.force)
    else:
        task = index_pending_task.delay(request.limit, request.force)
    return {"task_id": task.id}
