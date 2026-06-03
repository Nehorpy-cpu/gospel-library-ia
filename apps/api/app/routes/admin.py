import httpx
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.schemas.api import ReindexRequest
from app.services.db import get_conn
from app.services.qdrant_admin import QdrantAdmin

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
    return {
        "postgres": {"database": pg[0], "time": pg[1].isoformat(), "documents": documents, "errors": errors},
        "qdrant": qdrant,
    }
