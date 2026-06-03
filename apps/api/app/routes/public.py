import httpx
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from uuid import uuid4

from app.core.config import get_settings
from app.schemas.api import ChatRequest, DocumentListResponse, SearchRequest
from app.services.db import get_conn
from app.services.qdrant_admin import QdrantAdmin
from app.services.rate_limit import RateLimiter

router = APIRouter(prefix="/api")
limiter = RateLimiter()


def _is_missing_openai_response(response: httpx.Response) -> bool:
    if response.status_code != 503:
        return False
    try:
        return response.json().get("status") == "missing_api_key"
    except ValueError:
        return False


@router.post("/search")
async def search(payload: SearchRequest, request: Request):
    await limiter.check(request)
    if _qdrant_points_count() <= 0:
        return _textual_search_response(payload, ["Busqueda semantica no disponible todavia."])
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(f"{get_settings().rag_api_url}/search", json=payload.model_dump(mode="json"))
            if _is_missing_openai_response(response):
                return _textual_search_response(
                    payload,
                    [
                        "Falta configurar la clave de OpenAI para busqueda IA.",
                        "Busqueda semantica no disponible todavia.",
                        "OPENAI_API_KEY is required for semantic search and chat",
                    ],
                )
            response.raise_for_status()
            data = response.json()
            if not data.get("results"):
                fallback = _textual_search_response(payload, ["Sin resultados semanticos; se uso busqueda textual basica."])
                if fallback["results"]:
                    return fallback
            return data
    except Exception:
        return _textual_search_response(payload, ["Busqueda semantica no disponible todavia."])


@router.post("/chat")
async def chat(payload: ChatRequest, request: Request):
    await limiter.check(request, get_settings().chat_rate_limit_per_minute)
    if _qdrant_points_count() <= 0:
        return _local_chat_response(payload, ["Busqueda semantica no disponible todavia."])
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(f"{get_settings().rag_api_url}/chat", json=payload.model_dump(mode="json"))
            if _is_missing_openai_response(response):
                return _local_chat_response(
                    payload,
                    [
                        "Falta configurar la clave de OpenAI para busqueda IA.",
                        "Busqueda semantica no disponible todavia.",
                        "OPENAI_API_KEY is required for semantic search and chat",
                    ],
                )
            response.raise_for_status()
            return response.json()
    except Exception:
        return _local_chat_response(payload, ["Busqueda semantica no disponible todavia."])


DOCUMENT_STATUSES = ("READY", "PENDING", "FAILED", "INDEXED")


@router.get("/documents/summary")
def documents_summary():
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT
              CASE WHEN is_indexed THEN 'INDEXED' ELSE upper(coalesce(status, 'PENDING')) END AS status,
              count(*)::int
            FROM documents
            GROUP BY 1
            """
        ).fetchall()
    counts = {status: 0 for status in DOCUMENT_STATUSES}
    for row in rows:
        status = row[0] if row[0] in counts else "PENDING"
        counts[status] += row[1]
    return {"documents": [{"status": status, "count": counts[status]} for status in DOCUMENT_STATUSES]}


@router.get("/documents", response_model=DocumentListResponse)
def documents(
    q: str | None = None,
    language: str | None = None,
    limit: int = 30,
    offset: int = 0,
    status: str | None = None,
    sourceType: str | None = None,
    search: str | None = None,
    cursor: str | None = None,
):
    limit = max(1, min(limit, 100))
    offset = max(0, offset)
    search_term = search or q
    with get_conn() as conn:
        columns = _document_columns(conn)
        metadata_column = "raw_metadata" if "raw_metadata" in columns else "metadata"
        deleted_filter = "deleted_at IS NULL" if "deleted_at" in columns else "1=1"
        author_expr = "d.author" if "author" in columns else "NULL"
        status_expr = "d.status" if "status" in columns else "'READY'"
        text_column = "text" if "text" in columns else "content_text"
        where = [f"d.{deleted_filter}" if deleted_filter != "1=1" else deleted_filter]
        params: dict = {"limit": limit, "offset": offset}
        if search_term:
            where.append(
                f"(d.title ILIKE %(search)s OR coalesce(d.{text_column}, '') ILIKE %(search)s OR coalesce({author_expr}, '') ILIKE %(search)s)"
            )
            params["search"] = f"%{search_term}%"
        if language:
            where.append("d.language = %(language)s")
            params["language"] = language
        if status:
            where.append(
                "CASE WHEN d.is_indexed THEN 'INDEXED' ELSE upper(coalesce(d.status, 'PENDING')) END = %(status)s"
                if "status" in columns
                else "CASE WHEN d.is_indexed THEN 'INDEXED' ELSE 'READY' END = %(status)s"
            )
            params["status"] = status.upper()
        elif "status" in columns:
            where.append("upper(coalesce(d.status, 'PENDING')) <> 'FAILED'")
        source_type_expr = f"COALESCE(d.{metadata_column}->>'source_type', s.key)"
        source_url_expr = f"COALESCE(d.{metadata_column}->>'source_url', d.canonical_url)"
        if sourceType:
            where.append(f"({source_type_expr} = %(source_type)s OR s.key = %(source_type)s)")
            params["source_type"] = sourceType
        if cursor:
            where.append("d.id::text > %(cursor)s")
            params["cursor"] = cursor
        sql = f"""
          SELECT
            d.id::text,
            d.title,
            {author_expr},
            s.name AS source,
            {source_type_expr} AS source_type,
            d.language,
            CASE WHEN d.is_indexed THEN 'INDEXED' ELSE upper(coalesce({status_expr}, 'PENDING')) END AS display_status,
            d.created_at,
            d.updated_at,
            d.canonical_url,
            {source_url_expr} AS source_url,
            left(coalesce(d.{text_column}, ''), 360) AS excerpt,
            d.published_at,
            d.{metadata_column},
            count(*) OVER()::int AS total_count
          FROM documents d
          JOIN sources s ON s.id = d.source_id
          WHERE {" AND ".join(where)}
          ORDER BY d.updated_at DESC, d.id
          LIMIT %(limit)s
          OFFSET %(offset)s
        """
        rows = conn.execute(sql, params).fetchall()
    items = [
        {
            "id": row[0],
            "title": row[1],
            "author": row[2],
            "source": row[3],
            "sourceType": row[4],
            "language": row[5],
            "status": row[6],
            "createdAt": row[7].isoformat() if row[7] else None,
            "updatedAt": row[8].isoformat() if row[8] else None,
            "url": row[9],
            "sourceUrl": row[10],
            "excerpt": row[11] or None,
            "publishedAt": row[12].isoformat() if row[12] else None,
            "metadata": row[13] or {},
        }
        for row in rows
    ]
    total = rows[0][14] if rows else 0
    return {
        "items": items,
        "documents": items,
        "total": total,
        "limit": limit,
        "offset": offset,
        "next_cursor": items[-1]["id"] if len(items) == limit else None,
    }


@router.get("/documents/{document_id}")
def document_detail(document_id: str):
    with get_conn() as conn:
        columns = _document_columns(conn)
        metadata_column = "raw_metadata" if "raw_metadata" in columns else "metadata"
        text_column = "text" if "text" in columns else "content_text"
        author_column = "author" if "author" in columns else "NULL"
        doc = conn.execute(
            f"""
            SELECT id::text, title, {author_column}, language, canonical_url, published_at, {text_column}, {metadata_column}
            FROM documents WHERE id = %s
            """,
            (document_id,),
        ).fetchone()
        try:
            chunks = conn.execute(
                """
                SELECT id::text, chunk_index, section_title, text
                FROM document_chunks WHERE document_id = %s ORDER BY chunk_index LIMIT 200
                """,
                (document_id,),
            ).fetchall()
        except Exception:
            chunks = []
    if not doc:
        return {"id": document_id, "not_found": True}
    return {
        "id": doc[0],
        "title": doc[1],
        "author": doc[2],
        "language": doc[3],
        "canonical_url": doc[4],
        "published_at": doc[5].isoformat() if doc[5] else None,
        "text": doc[6],
        "metadata": doc[7] or {},
        "chunks": [{"id": c[0], "index": c[1], "section_title": c[2], "text": c[3]} for c in chunks],
    }


@router.get("/authors")
def authors(q: str | None = None, limit: int = 30):
    with get_conn() as conn:
        if _table_exists(conn, "authors"):
            author_where = ""
            author_params: tuple = (limit,)
            if q:
                author_where = "WHERE display_name ILIKE %s"
                author_params = (f"%{q}%", limit)
            rows = conn.execute(
                f"SELECT id::text, display_name, slug FROM authors {author_where} ORDER BY display_name LIMIT %s",
                author_params,
            ).fetchall()
            if rows:
                return {"items": [{"id": r[0], "name": r[1], "slug": r[2]} for r in rows]}
        fallback_where = "author IS NOT NULL AND author <> ''"
        fallback_params: dict = {"limit": limit}
        if q:
            fallback_where += " AND author ILIKE %(q_like)s"
            fallback_params["q_like"] = f"%{q}%"
        rows = conn.execute(
            f"""
            SELECT author, count(*)::int
            FROM documents
            WHERE {fallback_where}
            GROUP BY author
            ORDER BY author
            LIMIT %(limit)s
            """,
            fallback_params,
        ).fetchall()
    return {
        "items": [
            {"name": row[0], "slug": row[0].lower().replace(" ", "-"), "documentCount": row[1]}
            for row in rows
        ]
    }


@router.get("/topics")
def topics(limit: int = 50):
    with get_conn() as conn:
        if _table_exists(conn, "tags"):
            rows = conn.execute("SELECT id::text, name, slug FROM tags ORDER BY name LIMIT %s", (limit,)).fetchall()
            if rows:
                return {"items": [{"id": r[0], "name": r[1], "slug": r[2]} for r in rows]}
        rows = conn.execute(
            """
            SELECT name, sum(count)::int AS count
            FROM (
              SELECT value AS name, count(*)::int AS count
              FROM documents d
              CROSS JOIN LATERAL jsonb_array_elements_text(
                CASE WHEN jsonb_typeof(d.tags) = 'array' THEN d.tags ELSE '[]'::jsonb END
              ) AS tag(value)
              GROUP BY value
              UNION ALL
              SELECT category AS name, count(*)::int AS count
              FROM documents
              WHERE category IS NOT NULL AND category <> ''
              GROUP BY category
            ) topics
            GROUP BY name
            ORDER BY name
            LIMIT %(limit)s
            """,
            {"limit": limit},
        ).fetchall()
        if not rows:
            rows = conn.execute(
                """
                SELECT title AS name, 1::int AS count
                FROM documents
                ORDER BY updated_at DESC, title
                LIMIT %(limit)s
                """,
                {"limit": limit},
            ).fetchall()
    return {
        "items": [
            {"name": row[0], "slug": row[0].lower().replace(" ", "-"), "documentCount": row[1]}
            for row in rows
        ]
    }


def _document_search(query: str, limit: int) -> list[dict]:
    with get_conn() as conn:
        columns = {
            row[0]
            for row in conn.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_name = 'documents'"
            ).fetchall()
        }
        text_column = "text" if "text" in columns else "content_text"
        author_column = "author" if "author" in columns else "NULL"
        rows = conn.execute(
            f"""
            SELECT
              d.id::text,
              d.title,
              {author_column},
              d.language,
              d.canonical_url,
              COALESCE(d.raw_metadata->>'source_type', s.key) AS source_key,
              left(coalesce(d.{text_column}, ''), 520) AS snippet
            FROM documents d
            JOIN sources s ON s.id = d.source_id
            WHERE d.title ILIKE %(q)s OR coalesce(d.{text_column}, '') ILIKE %(q)s
            ORDER BY d.updated_at DESC
            LIMIT %(limit)s
            """,
            {"q": f"%{query}%", "limit": limit},
        ).fetchall()
        if not rows:
            stopwords = {
                "about",
                "does",
                "from",
                "mention",
                "mentions",
                "sources",
                "teach",
                "that",
                "the",
                "what",
                "where",
                "with",
            }
            terms = [
                token.lower()
                for token in query.replace("?", " ").replace(",", " ").split()
                if len(token) > 2 and token.lower() not in stopwords
            ][:8]
            if terms:
                params = {"limit": limit, **{f"term_{i}": f"%{term}%" for i, term in enumerate(terms)}}
                score_expr = " + ".join(
                    f"CASE WHEN d.title ILIKE %(term_{i})s OR coalesce(d.{text_column}, '') ILIKE %(term_{i})s THEN 1 ELSE 0 END"
                    for i in range(len(terms))
                )
                where_expr = " OR ".join(
                    f"d.title ILIKE %(term_{i})s OR coalesce(d.{text_column}, '') ILIKE %(term_{i})s"
                    for i in range(len(terms))
                )
                rows = conn.execute(
                    f"""
                    SELECT
                      d.id::text,
                      d.title,
                      {author_column},
                      d.language,
                      d.canonical_url,
                      COALESCE(d.raw_metadata->>'source_type', s.key) AS source_key,
                      left(coalesce(d.{text_column}, ''), 520) AS snippet,
                      ({score_expr}) AS match_score
                    FROM documents d
                    JOIN sources s ON s.id = d.source_id
                    WHERE {where_expr}
                    ORDER BY match_score DESC, d.updated_at DESC
                    LIMIT %(limit)s
                    """,
                    params,
                ).fetchall()
    return [
        {
            "id": row[0],
            "title": row[1],
            "author": row[2],
            "language": row[3],
            "canonical_url": row[4],
            "source_key": row[5],
            "snippet": row[6],
        }
        for row in rows
    ]


def _textual_search_response(payload: SearchRequest, warnings: list[str] | None = None) -> dict:
    rows = _document_search(payload.query, payload.limit)
    return {
        "query": payload.query,
        "rewritten_query": None,
        "mode": "textual_fallback",
        "warnings": warnings or [],
        "results": [
            {
                "chunk_id": row["id"],
                "document_id": row["id"],
                "title": row["title"],
                "author": row["author"],
                "source_key": row["source_key"],
                "canonical_url": row["canonical_url"],
                "language": row["language"],
                "section_title": "Documento",
                "snippet": row["snippet"],
                "score": 0.5,
                "semantic_score": None,
                "bm25_score": None,
                "rerank_score": None,
                "metadata": {"fallback": "postgres_text"},
            }
            for row in rows
        ],
    }


def _local_chat_response(payload: ChatRequest, warnings: list[str] | None = None) -> dict:
    rows = _document_search(payload.message, 5)
    citations = [
        {
            "citation_id": index,
            "chunk_id": row["id"],
            "document_id": row["id"],
            "title": row["title"],
            "author": row["author"],
            "source_key": row["source_key"],
            "canonical_url": row["canonical_url"],
            "language": row["language"],
            "section_title": "Documento",
            "quote": row["snippet"],
            "score": 0.5,
        }
        for index, row in enumerate(rows, start=1)
    ]
    if rows:
        message = (
            "Modo basico sin embeddings: no puedo generar una respuesta IA completa todavia, "
            "pero encontre fuentes reales relacionadas: "
            + ", ".join(f"[{i}] {row['title']}" for i, row in enumerate(rows, start=1))
        )
    else:
        message = (
            "Modo basico sin embeddings: la busqueda semantica y el chat IA aun no estan disponibles. "
            "No encontre fuentes locales relacionadas con esta consulta."
        )
    return {
        "session_id": payload.session_id or str(uuid4()),
        "message": message,
        "citations": citations,
        "grounded": bool(rows),
        "mode": "textual_fallback",
        "warnings": warnings or ["Busqueda semantica no disponible todavia."],
    }


def _qdrant_points_count() -> int:
    try:
        return int(QdrantAdmin().ensure_collection().get("vectors") or 0)
    except Exception:
        return 0


def _document_columns(conn) -> set[str]:
    return {
        row[0]
        for row in conn.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name = 'documents'"
        ).fetchall()
    }


def _table_exists(conn, table_name: str) -> bool:
    row = conn.execute(
        """
        SELECT EXISTS (
          SELECT 1
          FROM information_schema.tables
          WHERE table_schema = 'public' AND table_name = %s
        )
        """,
        (table_name,),
    ).fetchone()
    return bool(row and row[0])
