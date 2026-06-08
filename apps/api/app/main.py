from datetime import UTC, datetime
from urllib.request import Request as UrlRequest
from urllib.request import urlopen

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from redis import Redis

from app.core.config import get_settings
from app.core.logging import configure_logging, logger
from app.routes.admin import router as admin_router
from app.routes.beta import router as beta_router
from app.routes.exports import router as exports_router
from app.routes.profile import router as profile_router
from app.routes.public import router as public_router
from app.routes.study import alias_router as study_alias_router
from app.routes.study import router as study_router
from app.routes.talk_builder import router as talk_builder_router
from app.services.db import get_conn
from app.services.privacy import sanitize_value
from app.services.rate_limit import RateLimiter

configure_logging()
log = logger(__name__)
settings = get_settings()
privacy_limiter = RateLimiter()

app = FastAPI(title="Gospel Library IA API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)
app.include_router(public_router)
app.include_router(admin_router)
app.include_router(beta_router)
app.include_router(study_router)
app.include_router(study_alias_router)
app.include_router(talk_builder_router)
app.include_router(exports_router)
app.include_router(profile_router)


SENSITIVE_API_PREFIXES = (
    "/api/admin",
    "/api/chat",
    "/api/exports",
    "/api/profile",
    "/api/study",
    "/api/study-workspaces",
    "/api/talk-builder",
)


@app.middleware("http")
async def privacy_and_security_middleware(request: Request, call_next):
    if request.url.path.startswith(SENSITIVE_API_PREFIXES):
        await privacy_limiter.check(request, settings.rate_limit_per_minute, scope="sensitive-api")
    response = await call_next(request)
    _set_default_header(response, "X-Content-Type-Options", "nosniff")
    _set_default_header(response, "X-Frame-Options", "DENY")
    _set_default_header(response, "Referrer-Policy", "no-referrer")
    _set_default_header(response, "Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    if request.url.path.startswith(SENSITIVE_API_PREFIXES):
        _set_default_header(response, "Cache-Control", "no-store")
    return response


def _set_default_header(response, key: str, value: str) -> None:
    if key not in response.headers:
        response.headers[key] = value


@app.exception_handler(Exception)
async def handle_error(request: Request, exc: Exception):
    log.error("api_error", path=str(request.url), error=sanitize_value(str(exc)))
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


def _check_postgres() -> str:
    try:
        with get_conn() as conn:
            conn.execute("select 1")
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


def _status_payload() -> dict:
    dependencies = {
        "postgres": _check_postgres(),
        "redis": _check_redis(),
        "qdrant": _check_qdrant(),
    }
    return {
        "status": "healthy",
        "service": "gospel-library-api",
        "timestamp": datetime.now(UTC).isoformat(),
        "dependencies": dependencies,
    }


@app.get("/")
def root():
    return {
        "service": "gospel-library-api",
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
        return JSONResponse(status_code=503, content=payload)
    return payload
