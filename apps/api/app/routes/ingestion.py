from __future__ import annotations

import hmac

from fastapi import APIRouter, Header, HTTPException, Request, Response, status

from app.core.config import get_settings
from app.schemas.ingestion import (
    N8nDocumentIngestionRequest,
    N8nDocumentIngestionResponse,
    N8nIngestionHealthResponse,
)
from app.services.db import get_conn
from app.services.n8n_ingestion import ingest_document
from app.services.rate_limit import RateLimiter


router = APIRouter(prefix="/api/ingestion", tags=["ingestion"])
limiter = RateLimiter()


def require_ingestion_key(x_ingestion_key: str | None = Header(default=None, alias="X-Ingestion-Key")) -> None:
    expected = get_settings().ingestion_api_key
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Ingestion endpoint is not configured",
        )
    if not x_ingestion_key or not hmac.compare_digest(x_ingestion_key, expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid ingestion credentials")


@router.get("/documents/health", response_model=N8nIngestionHealthResponse)
def ingestion_health():
    return N8nIngestionHealthResponse()


@router.post(
    "/documents",
    response_model=N8nDocumentIngestionResponse,
    responses={201: {"model": N8nDocumentIngestionResponse, "description": "Document created"}},
)
async def create_ingestion_document(
    payload: N8nDocumentIngestionRequest,
    request: Request,
    response: Response,
    x_ingestion_key: str | None = Header(default=None, alias="X-Ingestion-Key"),
):
    require_ingestion_key(x_ingestion_key)
    await limiter.check(request, scope="n8n-ingestion")
    with get_conn() as conn:
        result = ingest_document(conn, payload)
        conn.commit()
    response.status_code = status.HTTP_201_CREATED if result["status"] == "created" else status.HTTP_200_OK
    return result
