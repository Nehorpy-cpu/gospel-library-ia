import os
from datetime import UTC, datetime
from urllib.request import Request as UrlRequest
from urllib.request import urlopen

from fastapi import FastAPI
from redis import Redis
from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.logging.structured import configure_logging
from app.scheduler.sources import seed_sources
from app.storage.r2 import R2Storage
from app.workers.tasks import discover_enabled_sources_task, discover_source_task

configure_logging()
settings = get_settings()

app = FastAPI(title="Gospel Library IA Scraper", version="0.1.0")


def _check_postgres() -> str:
    try:
        with SessionLocal() as db:
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
        qdrant_url = os.getenv("QDRANT_URL", "http://qdrant:6333")
        request = UrlRequest(f"{qdrant_url.rstrip('/')}/healthz")
        with urlopen(request, timeout=2) as response:
            return "ok" if response.status < 500 else "error"
    except Exception:
        return "error"


def _status_payload() -> dict:
    dependencies = {
        "postgres": _check_postgres(),
        "redis": _check_redis(),
        "qdrant": _check_qdrant(),
    }
    return {
        "status": "healthy",
        "service": "gospel-library-scraper",
        "timestamp": datetime.now(UTC).isoformat(),
        "dependencies": dependencies,
    }


@app.get("/")
def root():
    return {
        "service": "gospel-library-scraper",
        "status": "ok",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health")
def health():
    return _status_payload()


@app.get("/ready")
def ready():
    payload = _status_payload()
    if any(status != "ok" for status in payload["dependencies"].values()):
        from fastapi.responses import JSONResponse

        return JSONResponse(status_code=503, content=payload)
    return payload


@app.post("/admin/bootstrap")
def bootstrap():
    seed_sources()
    R2Storage().ensure_bucket()
    return {"status": "bootstrapped"}


@app.post("/admin/discover")
def discover_all():
    task = discover_enabled_sources_task.delay()
    return {"task_id": task.id}


@app.post("/admin/discover/{source_id}")
def discover_one(source_id: str):
    task = discover_source_task.delay(source_id)
    return {"task_id": task.id}
