import httpx
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from uuid import uuid4

from app.core.config import get_settings
from app.schemas.api import ChatRequest, DocumentListResponse, SearchRequest
from app.services.db import get_conn
from app.services.qdrant_admin import QdrantAdmin
from app.services.rate_limit import RateLimiter
from app.services.calling_focus import calling_application_note
from app.services.scripture_refs import structured_scripture_refs
from app.services.source_filters import canonical_source_options, normalize_source_type, source_type_aliases

LEADERSHIP_QUERY_TERMS = (
    "primera presidencia",
    "first presidency",
    "cuorum de los doce",
    "cuórum de los doce",
    "quorum of the twelve",
    "apostoles actuales",
    "apóstoles actuales",
    "liderazgo vigente",
    "current leadership",
    "presidente actual",
    "current president",
)

CURRENT_LEADERSHIP_FALLBACK_NOTE = (
    "Regla de actualidad: para liderazgo vigente se debe verificar la conformacion actual "
    "con fuentes oficiales de La Iglesia cuando haya conexion disponible. Referencia local 2026: "
    "Primera Presidencia: Presidente Dallin H. Oaks; Presidente Henry B. Eyring, Primer Consejero; "
    "Presidente D. Todd Christofferson, Segundo Consejero. Cuorum de los Doce Apostoles: "
    "David A. Bednar; Dieter F. Uchtdorf; Quentin L. Cook; Neil L. Andersen; Ronald A. Rasband; "
    "Gary E. Stevenson; Dale G. Renlund; Gerrit W. Gong; Ulisses Soares; Patrick Kearon; "
    "Gérald Caussé; Clark G. Gilbert."
)

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
    settings = get_settings()
    await limiter.check(request, settings.chat_rate_limit_per_minute)
    await limiter.check_daily(request, settings.max_user_chat_messages_per_day, "chat")
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
        source_type_values = source_type_aliases(sourceType)
        if source_type_values:
            where.append(f"({source_type_expr} = ANY(%(source_types)s) OR s.key = ANY(%(source_types)s))")
            params["source_types"] = source_type_values
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
            "sourceType": normalize_source_type(row[4]) or row[4],
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


@router.get("/sources/summary")
def sources_summary():
    with get_conn() as conn:
        columns = _document_columns(conn)
        metadata_column = "raw_metadata" if "raw_metadata" in columns else "metadata"
        deleted_filter = "d.deleted_at IS NULL" if "deleted_at" in columns else "1=1"
        rows = conn.execute(
            f"""
            SELECT
              COALESCE(d.{metadata_column}->>'source_type', s.key) AS source_type,
              s.key,
              s.name,
              count(*)::int AS document_count
            FROM documents d
            JOIN sources s ON s.id = d.source_id
            WHERE {deleted_filter}
            GROUP BY 1, 2, 3
            ORDER BY document_count DESC, source_type
            """
        ).fetchall()
    counts = {option.key: 0 for option in canonical_source_options()}
    names = {option.key: option.label for option in canonical_source_options()}
    extras: dict[str, dict] = {}
    for raw_source_type, source_key, source_name, document_count in rows:
        canonical = normalize_source_type(raw_source_type or source_key)
        if canonical in counts:
            counts[canonical] += document_count
        elif canonical:
            extras.setdefault(
                canonical,
                {
                    "key": canonical,
                    "label": source_name or canonical.replace("_", " ").title(),
                    "documentCount": 0,
                    "canonical": False,
                    "aliases": [raw_source_type, source_key],
                },
            )
            extras[canonical]["documentCount"] += document_count
    items = [
        {
            "key": option.key,
            "label": names[option.key],
            "documentCount": counts[option.key],
            "canonical": True,
            "aliases": list(option.aliases),
        }
        for option in canonical_source_options()
    ]
    items.extend(sorted(extras.values(), key=lambda item: item["label"]))
    return {"items": items}


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


def _document_search(query: str, limit: int, filters=None, language: str | None = None) -> list[dict]:
    with get_conn() as conn:
        columns = {
            row[0]
            for row in conn.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_name = 'documents'"
            ).fetchall()
        }
        metadata_column = "raw_metadata" if "raw_metadata" in columns else "metadata"
        text_column = "text" if "text" in columns else "content_text"
        author_column = "author" if "author" in columns else "NULL"
        scripture_refs_expr = "d.scripture_refs" if "scripture_refs" in columns else "'[]'::jsonb"
        source_type_expr = f"COALESCE(d.{metadata_column}->>'source_type', s.key)"
        filter_where, filter_params = _metadata_filter_sql(filters, language, source_type_expr, columns)
        rows = conn.execute(
            f"""
            SELECT
              d.id::text,
              d.title,
              {author_column},
              d.language,
              d.canonical_url,
              {source_type_expr} AS source_key,
              left(coalesce(d.{text_column}, ''), 520) AS snippet,
              {scripture_refs_expr} AS scripture_refs
            FROM documents d
            JOIN sources s ON s.id = d.source_id
            WHERE (d.title ILIKE %(q)s OR coalesce(d.{text_column}, '') ILIKE %(q)s)
              {"AND " + " AND ".join(filter_where) if filter_where else ""}
            ORDER BY d.updated_at DESC
            LIMIT %(limit)s
            """,
            {"q": f"%{query}%", "limit": limit, **filter_params},
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
                      {source_type_expr} AS source_key,
                      left(coalesce(d.{text_column}, ''), 520) AS snippet,
                      {scripture_refs_expr} AS scripture_refs,
                      ({score_expr}) AS match_score
                    FROM documents d
                    JOIN sources s ON s.id = d.source_id
                    WHERE ({where_expr})
                      {"AND " + " AND ".join(filter_where) if filter_where else ""}
                    ORDER BY match_score DESC, d.updated_at DESC
                    LIMIT %(limit)s
                    """,
                    {**params, **filter_params},
                ).fetchall()
    return [
        {
            "id": row[0],
            "title": row[1],
            "author": row[2],
            "language": row[3],
            "canonical_url": row[4],
            "source_key": normalize_source_type(row[5]) or row[5],
            "snippet": row[6],
            "scripture_refs": row[7] or [],
        }
        for row in rows
    ]


def _textual_search_response(payload: SearchRequest, warnings: list[str] | None = None) -> dict:
    rows = _document_search(payload.query, payload.limit, payload.filters, payload.language)
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
                "metadata": {
                    "fallback": "postgres_text",
                    "scripture_refs": row["scripture_refs"],
                    "scripture_refs_structured": structured_scripture_refs(row["scripture_refs"]),
                },
            }
            for row in rows
        ],
    }


def _local_chat_response(payload: ChatRequest, warnings: list[str] | None = None) -> dict:
    rows = _document_search(payload.message, 5, payload.filters, payload.language)
    response_warnings = list(warnings or ["Busqueda semantica no disponible todavia."])
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
            "metadata": {
                "scripture_refs": row["scripture_refs"],
                "scripture_refs_structured": structured_scripture_refs(row["scripture_refs"]),
            },
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
    if _is_current_leadership_query(payload.message):
        message = f"{message}\n\n{CURRENT_LEADERSHIP_FALLBACK_NOTE}"
        response_warnings.append(
            "Liderazgo vigente requiere verificacion con fuentes oficiales antes de generar "
            "analisis dependiente de lideres actuales."
        )
    if payload.calling_focus:
        message = f"{message}\n\n{calling_application_note(payload.calling_focus)}"
    return {
        "session_id": payload.session_id or str(uuid4()),
        "message": message,
        "citations": citations,
        "grounded": bool(rows),
        "mode": "textual_fallback",
        "warnings": response_warnings,
    }


def _is_current_leadership_query(text: str) -> bool:
    normalized = text.casefold()
    return any(term in normalized for term in LEADERSHIP_QUERY_TERMS)


def _metadata_filter_sql(filters, language: str | None, source_type_expr: str, columns: set[str]) -> tuple[list[str], dict]:
    where: list[str] = []
    params: dict = {}
    if not filters:
        filters = SearchRequest(query="_").filters

    source_values: list[str] = []
    for source_key in filters.source_keys or []:
        source_values.extend(source_type_aliases(source_key))
    source_values = sorted(set(source_values))
    if source_values:
        where.append(f"({source_type_expr} = ANY(%(filter_source_keys)s) OR s.key = ANY(%(filter_source_keys)s))")
        params["filter_source_keys"] = source_values

    languages = filters.languages or ([language] if language else None)
    if languages:
        where.append("d.language = ANY(%(filter_languages)s)")
        params["filter_languages"] = languages
    if filters.authors and "author" in columns:
        where.append("d.author = ANY(%(filter_authors)s)")
        params["filter_authors"] = filters.authors
    if filters.categories and "category" in columns:
        where.append("d.category = ANY(%(filter_categories)s)")
        params["filter_categories"] = filters.categories
    if filters.tags and "tags" in columns:
        where.append("d.tags::text ILIKE ANY(%(filter_tags)s)")
        params["filter_tags"] = [f"%{tag}%" for tag in filters.tags]
    if filters.scripture_refs and "scripture_refs" in columns:
        where.append("d.scripture_refs::text ILIKE ANY(%(filter_scripture_refs)s)")
        params["filter_scripture_refs"] = [f"%{ref}%" for ref in filters.scripture_refs]
    if filters.document_ids:
        where.append("d.id::text = ANY(%(filter_document_ids)s)")
        params["filter_document_ids"] = [str(value) for value in filters.document_ids]
    if filters.published_after and "published_at" in columns:
        where.append("d.published_at >= %(filter_published_after)s")
        params["filter_published_after"] = filters.published_after
    if filters.published_before and "published_at" in columns:
        where.append("d.published_at <= %(filter_published_before)s")
        params["filter_published_before"] = filters.published_before
    return where, params


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
