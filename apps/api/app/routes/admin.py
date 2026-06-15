import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.schemas.api import ReindexRequest
from app.services.auth import require_admin
from app.services.db import get_conn
from app.services.qdrant_admin import QdrantAdmin
from app.services.source_filters import canonical_source_options, normalize_source_type

router = APIRouter(prefix="/api")


class SourceUpdateRequest(BaseModel):
    enabled: bool | None = None
    maxPagesPerRun: int | None = Field(default=None, ge=1, le=200)


class SourceCrawlRequest(BaseModel):
    maxPagesPerRun: int | None = Field(default=None, ge=1, le=200)


def _passthrough_rag_response(response: httpx.Response) -> JSONResponse | None:
    if response.status_code < 400:
        return None
    try:
        return JSONResponse(status_code=response.status_code, content=response.json())
    except ValueError:
        return JSONResponse(status_code=response.status_code, content={"detail": response.text})


@router.get("/ingestion/status")
def ingestion_status():
    with get_conn() as conn:
        jobs = conn.execute(
            "SELECT status, count(*) FROM ingestion_jobs GROUP BY status ORDER BY status"
        ).fetchall()
        docs = conn.execute("SELECT status, count(*) FROM documents GROUP BY status ORDER BY status").fetchall()
        recent_jobs = conn.execute(
            """
            SELECT
              id::text,
              job_type,
              status,
              attempts,
              error,
              created_at,
              started_at,
              finished_at,
              source,
              coalesce(documents_found, 0)::int,
              coalesce(documents_created, 0)::int,
              coalesce(documents_updated, 0)::int,
              coalesce(documents_skipped, 0)::int,
              coalesce(documents_failed, 0)::int,
              errors
            FROM ingestion_jobs
            ORDER BY created_at DESC
            LIMIT 20
            """
        ).fetchall()
    recent = [
        {
            "id": row[0],
            "type": row[1],
            "status": row[2],
            "attempts": row[3],
            "error": row[4],
            "createdAt": row[5].isoformat() if row[5] else None,
            "startedAt": row[6].isoformat() if row[6] else None,
            "finishedAt": row[7].isoformat() if row[7] else None,
            "source": row[8],
            "documentsFound": row[9],
            "documentsCreated": row[10],
            "documentsUpdated": row[11],
            "documentsSkipped": row[12],
            "documentsFailed": row[13],
            "errors": row[14] or ([] if row[4] is None else [row[4]]),
        }
        for row in recent_jobs
    ]
    return {
        "jobs": [{"status": row[0], "count": row[1]} for row in jobs],
        "documents": [{"status": row[0], "count": row[1]} for row in docs],
        "recentJobs": recent,
        "latestScrapingTasks": [
            job
            for job in recent
            if any(token in job["type"].lower() for token in ["scrape", "crawl", "discover", "asset", "ocr"])
        ][:8],
        "latestIndexingTasks": [
            job
            for job in recent
            if any(token in job["type"].lower() for token in ["index", "embed", "rag"])
        ][:8],
    }


@router.get("/admin/errors", dependencies=[Depends(require_admin)])
def admin_errors(limit: int = Query(default=20, ge=1, le=100)):
    with get_conn() as conn:
        failed_jobs = conn.execute(
            """
            SELECT
              id::text,
              job_type,
              status,
              attempts,
              error,
              errors,
              payload,
              source,
              created_at,
              started_at,
              finished_at
            FROM ingestion_jobs
            WHERE lower(status) IN ('failed', 'error')
               OR error IS NOT NULL
               OR errors <> '[]'::jsonb
            ORDER BY coalesce(finished_at, started_at, created_at) DESC
            LIMIT %(limit)s
            """,
            {"limit": limit},
        ).fetchall()
        failed_documents = conn.execute(
            """
            SELECT
              d.id::text,
              d.title,
              d.status,
              d.canonical_url,
              d.updated_at,
              s.name,
              COALESCE(d.raw_metadata->>'source_type', s.key) AS source_type,
              d.raw_metadata->>'error' AS error
            FROM documents d
            JOIN sources s ON s.id = d.source_id
            WHERE upper(coalesce(d.status, '')) = 'FAILED'
               OR d.raw_metadata ? 'error'
            ORDER BY d.updated_at DESC
            LIMIT %(limit)s
            """,
            {"limit": limit},
        ).fetchall()
    return {
        "jobs": [
            {
                "id": row[0],
                "type": row[1],
                "status": row[2],
                "attempts": row[3],
                "error": row[4],
                "errors": row[5] or ([] if row[4] is None else [row[4]]),
                "payload": row[6] or {},
                "source": row[7],
                "createdAt": row[8].isoformat() if row[8] else None,
                "startedAt": row[9].isoformat() if row[9] else None,
                "finishedAt": row[10].isoformat() if row[10] else None,
            }
            for row in failed_jobs
        ],
        "documents": [
            {
                "id": row[0],
                "title": row[1],
                "status": row[2],
                "url": row[3],
                "updatedAt": row[4].isoformat() if row[4] else None,
                "source": row[5],
                "sourceType": normalize_source_type(row[6]) or row[6],
                "error": row[7],
            }
            for row in failed_documents
        ],
    }


@router.get("/admin/sources", dependencies=[Depends(require_admin)])
def admin_sources():
    with get_conn() as conn:
        rows = conn.execute(
            """
            WITH document_stats AS (
              SELECT
                source_id,
                count(id)::int AS document_count,
                COALESCE(sum(length(coalesce(text, ''))), 0)::bigint AS text_characters
              FROM documents
              GROUP BY source_id
            ),
            job_stats AS (
              SELECT
                source_id,
                max(created_at) AS latest_job_at,
                count(id) FILTER (WHERE lower(status) IN ('failed', 'error'))::int AS error_count
              FROM ingestion_jobs
              WHERE source_id IS NOT NULL
              GROUP BY source_id
            )
            SELECT
              s.id::text,
              s.key,
              s.name,
              COALESCE(s.source_type, s.config->>'sourceType', s.key) AS source_type,
              s.base_url,
              COALESCE(s.language, s.config->>'language') AS language,
              s.enabled,
              COALESCE(s.crawl_strategy, s.config->>'crawlStrategy', 'html_discovery') AS crawl_strategy,
              COALESCE(s.rate_limit, NULLIF(s.config->>'rateLimit', '')::int, 30) AS rate_limit,
              COALESCE(s.max_pages_per_run, NULLIF(s.config->>'maxPagesPerRun', '')::int, 25) AS max_pages_per_run,
              s.last_crawled_at,
              COALESCE(s.robots_policy_notes, s.config->>'robotsPolicyNotes') AS robots_policy_notes,
              COALESCE(ds.document_count, 0)::int AS document_count,
              COALESCE(ds.text_characters, 0)::bigint AS text_characters,
              js.latest_job_at,
              COALESCE(js.error_count, 0)::int AS error_count
            FROM sources s
            LEFT JOIN document_stats ds ON ds.source_id = s.id
            LEFT JOIN job_stats js ON js.source_id = s.id
            ORDER BY s.name
            """
        ).fetchall()
    return {
        "items": [
            {
                "id": row[0],
                "sourceId": row[1],
                "name": row[2],
                "sourceType": normalize_source_type(row[3]) or row[3],
                "baseUrl": row[4],
                "language": row[5],
                "enabled": row[6],
                "crawlStrategy": row[7],
                "rateLimit": row[8],
                "maxPagesPerRun": row[9],
                "lastCrawledAt": row[10].isoformat() if row[10] else None,
                "robotsPolicyNotes": row[11],
                "documentCount": row[12],
                "textCharacters": int(row[13] or 0),
                "estimatedEmbeddingTokens": max(int((row[13] or 0) / 4), 0),
                "indexingMode": "index_later",
                "latestJobAt": row[14].isoformat() if row[14] else None,
                "errorCount": row[15],
            }
            for row in rows
        ]
    }


@router.patch("/admin/sources/{source_id}", dependencies=[Depends(require_admin)])
def update_admin_source(source_id: str, payload: SourceUpdateRequest):
    updates = []
    params = {"source_id": source_id}
    if payload.enabled is not None:
        updates.append("enabled = %(enabled)s")
        params["enabled"] = payload.enabled
    if payload.maxPagesPerRun is not None:
        updates.append("max_pages_per_run = %(max_pages_per_run)s")
        params["max_pages_per_run"] = payload.maxPagesPerRun
    if not updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No se proporcionaron cambios para la fuente")
    updates.append("updated_at = now()")
    with get_conn() as conn:
        row = conn.execute(
            f"""
            UPDATE sources
            SET {", ".join(updates)}
            WHERE id::text = %(source_id)s OR key = %(source_id)s
            RETURNING id::text, key, enabled, max_pages_per_run
            """,
            params,
        ).fetchone()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fuente no encontrada")
        conn.commit()
    return {"id": row[0], "sourceId": row[1], "enabled": row[2], "maxPagesPerRun": row[3]}


@router.post("/admin/sources/{source_id}/crawl", dependencies=[Depends(require_admin)])
async def crawl_admin_source(source_id: str, payload: SourceCrawlRequest | None = None):
    with get_conn() as conn:
        if payload and payload.maxPagesPerRun is not None:
            row = conn.execute(
                """
                UPDATE sources
                SET max_pages_per_run = %(max_pages_per_run)s, updated_at = now()
                WHERE id::text = %(source_id)s OR key = %(source_id)s
                RETURNING id::text, key
                """,
                {"source_id": source_id, "max_pages_per_run": payload.maxPagesPerRun},
            ).fetchone()
            conn.commit()
        else:
            row = conn.execute(
                "SELECT id::text, key FROM sources WHERE id::text = %(source_id)s OR key = %(source_id)s",
                {"source_id": source_id},
            ).fetchone()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fuente no encontrada")
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(f"{get_settings().scraper_api_url}/admin/discover/{row[0]}")
        response.raise_for_status()
        data = response.json()
    return {"task_id": data.get("task_id"), "sourceId": row[1], "maxPagesPerRun": payload.maxPagesPerRun if payload else None}


@router.post("/admin/jobs/{job_id}/retry", dependencies=[Depends(require_admin)])
def retry_ingestion_job(job_id: str):
    with get_conn() as conn:
        row = conn.execute(
            """
            UPDATE ingestion_jobs
            SET status = 'queued',
                error = NULL,
                errors = '[]'::jsonb,
                started_at = NULL,
                finished_at = NULL,
                attempts = 0
            WHERE id::text = %(job_id)s
              AND (lower(status) IN ('failed', 'error') OR error IS NOT NULL OR errors <> '[]'::jsonb)
            RETURNING id::text, job_type, status, payload, source
            """,
            {"job_id": job_id},
        ).fetchone()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No se encontró una tarea de ingesta reintentable")
        conn.commit()
    return {"task_id": row[0], "type": row[1], "status": row[2], "payload": row[3] or {}, "source": row[4]}


@router.post("/admin/scrape", dependencies=[Depends(require_admin)])
async def run_scrape():
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(f"{get_settings().scraper_api_url}/admin/discover")
        response.raise_for_status()
        return response.json()


@router.post("/admin/reindex", dependencies=[Depends(require_admin)])
async def reindex(payload: ReindexRequest):
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(f"{get_settings().rag_api_url}/admin/index", json=payload.model_dump(mode="json"))
        passthrough = _passthrough_rag_response(response)
        if passthrough:
            return passthrough
        response.raise_for_status()
        return response.json()


@router.get("/admin/indexing/estimate", dependencies=[Depends(require_admin)])
async def indexing_estimate(limit: int = Query(default=100, ge=1, le=5000), force: bool = False):
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(
            f"{get_settings().rag_api_url}/admin/indexing/estimate",
            params={"limit": limit, "force": force},
        )
        response.raise_for_status()
        return response.json()


@router.get("/admin/cost", dependencies=[Depends(require_admin)])
async def admin_cost():
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(f"{get_settings().rag_api_url}/admin/cost")
        response.raise_for_status()
        return response.json()


@router.post("/admin/indexing/pause", dependencies=[Depends(require_admin)])
async def pause_indexing():
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(f"{get_settings().rag_api_url}/admin/indexing/pause")
        response.raise_for_status()
        return response.json()


@router.post("/admin/indexing/resume", dependencies=[Depends(require_admin)])
async def resume_indexing():
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(f"{get_settings().rag_api_url}/admin/indexing/resume")
        response.raise_for_status()
        return response.json()


@router.get("/admin/status", dependencies=[Depends(require_admin)])
def admin_status():
    qdrant = QdrantAdmin().ensure_collection()
    with get_conn() as conn:
        pg = conn.execute("SELECT current_database(), now()").fetchone()
        documents = conn.execute("SELECT count(*) FROM documents").fetchone()[0]
        errors = conn.execute("SELECT count(*) FROM ingestion_jobs WHERE status = 'failed' OR status = 'FAILED'").fetchone()[0]
        source_rows = conn.execute(
            """
            SELECT COALESCE(d.raw_metadata->>'source_type', s.key) AS source_type, count(*)::int
            FROM documents d
            JOIN sources s ON s.id = d.source_id
            GROUP BY 1
            """
        ).fetchall()
    source_counts = {option.key: 0 for option in canonical_source_options()}
    for source_type, count in source_rows:
        canonical = normalize_source_type(source_type)
        if canonical in source_counts:
            source_counts[canonical] += count
    return {
        "postgres": {
            "database": pg[0],
            "time": pg[1].isoformat(),
            "documents": documents,
            "errors": errors,
            "sourceCounts": [
                {"key": option.key, "label": option.label, "count": source_counts[option.key]}
                for option in canonical_source_options()
            ],
        },
        "qdrant": qdrant,
    }
