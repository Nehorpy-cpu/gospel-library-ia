import httpx
from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.schemas.api import ReindexRequest
from app.services.db import get_conn
from app.services.qdrant_admin import QdrantAdmin
from app.services.source_filters import canonical_source_options, normalize_source_type

router = APIRouter(prefix="/api")


def _is_missing_openai_response(response: httpx.Response) -> bool:
    if response.status_code != 503:
        return False
    try:
        return response.json().get("status") == "missing_api_key"
    except ValueError:
        return False


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
            "errors": row[12] or ([] if row[4] is None else [row[4]]),
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


@router.get("/admin/errors")
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


@router.post("/admin/jobs/{job_id}/retry")
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
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Retryable ingestion job not found")
        conn.commit()
    return {"task_id": row[0], "type": row[1], "status": row[2], "payload": row[3] or {}, "source": row[4]}


@router.post("/admin/scrape")
async def run_scrape():
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(f"{get_settings().scraper_api_url}/admin/discover")
        response.raise_for_status()
        return response.json()


@router.post("/admin/reindex")
async def reindex(payload: ReindexRequest):
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(f"{get_settings().rag_api_url}/admin/index", json=payload.model_dump(mode="json"))
        if _is_missing_openai_response(response):
            return JSONResponse(status_code=503, content=response.json())
        response.raise_for_status()
        return response.json()


@router.get("/admin/status")
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
