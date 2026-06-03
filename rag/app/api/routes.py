import json
from datetime import UTC, datetime
from urllib.request import Request as UrlRequest
from urllib.request import urlopen

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from redis import Redis
from sqlalchemy import text
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from app.core.config import get_settings
from app.db.session import get_db
from app.rag.orchestrator import RAGOrchestrator
from app.retrieval.hybrid import HybridSearchService
from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.search import IndexRequest, SearchRequest, SearchResponse, SearchResult
from app.workers.tasks import index_documents_task, index_pending_task

router = APIRouter()
settings = get_settings()
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
        return _missing_openai_response()
    rewritten, chunks = await HybridSearchService().search(
        db,
        request.query,
        request.filters,
        language=request.language,
        limit=request.limit,
        use_reranker=request.use_reranker,
    )
    return SearchResponse(
        query=request.query,
        rewritten_query=rewritten,
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


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, db: Session = Depends(get_db)):
    if _missing_openai_api_key():
        return _missing_openai_response()
    return await RAGOrchestrator().answer(db, request)


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest, db: Session = Depends(get_db)):
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
