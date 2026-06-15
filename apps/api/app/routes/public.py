from fastapi import APIRouter, HTTPException, Request, status
from uuid import UUID, uuid4

from app.core.config import get_settings
from app.schemas.api import ChatRequest, DocumentListResponse, SearchRequest, SearchResponse
from app.services.db import get_conn
from app.services.rate_limit import RateLimiter
from app.services.calling_focus import calling_application_note
from app.services.scripture_refs import structured_scripture_refs
from app.services.source_filters import canonical_source_options, normalize_source_type, source_type_aliases
from app.services.spanish_text import normalize_tag_es, normalize_text_es, normalize_visible_metadata

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


def confirmed_duplicate_filter(alias: str = "d") -> str:
    return f"""
    NOT EXISTS (
      SELECT 1
      FROM document_duplicate_relations duplicate_relation
      WHERE duplicate_relation.duplicate_document_id = {alias}.id
        AND duplicate_relation.review_status = 'confirmed'
        AND duplicate_relation.classification IN ('exact_duplicate', 'probable_duplicate')
    )
    """.strip()


@router.post("/search", response_model=SearchResponse)
async def search(payload: SearchRequest, request: Request):
    await limiter.check(request)
    return _textual_search_response(payload)


@router.post("/chat")
async def chat(payload: ChatRequest, request: Request):
    settings = get_settings()
    await limiter.check(request, settings.chat_rate_limit_per_minute)
    await limiter.check_daily(request, settings.max_user_chat_messages_per_day, "chat")
    return _local_chat_response(payload, ["Busqueda semantica no disponible todavia."])


DOCUMENT_STATUSES = ("READY", "PENDING", "FAILED", "INDEXED")


@router.get("/documents/summary")
def documents_summary():
    with get_conn() as conn:
        rows = conn.execute(
            f"""
            SELECT
              CASE WHEN d.is_indexed THEN 'INDEXED' ELSE upper(coalesce(d.status, 'PENDING')) END AS status,
              count(*)::int
            FROM documents d
            WHERE {confirmed_duplicate_filter("d")}
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
    includeSeed: bool = True,
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
        where.append(confirmed_duplicate_filter("d"))
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
        if not includeSeed:
            where.append(
                f"coalesce(d.{metadata_column}->>'is_seed', d.{metadata_column}->>'seed_content', 'false') <> 'true'"
            )
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
          ORDER BY
            CASE
              WHEN coalesce(d.{metadata_column}->>'is_seed', d.{metadata_column}->>'seed_content', 'false') = 'true'
              THEN 1 ELSE 0
            END ASC,
            d.updated_at DESC,
            d.id
          LIMIT %(limit)s
          OFFSET %(offset)s
        """
        rows = conn.execute(sql, params).fetchall()
    items = [
        {
            "id": row[0],
            "title": normalize_text_es(row[1]),
            "author": normalize_text_es(row[2]) if row[2] else None,
            "source": normalize_text_es(row[3]),
            "sourceType": normalize_source_type(row[4]) or row[4],
            "language": row[5],
            "status": row[6],
            "createdAt": row[7].isoformat() if row[7] else None,
            "updatedAt": row[8].isoformat() if row[8] else None,
            "url": row[9],
            "sourceUrl": row[10],
            "excerpt": normalize_text_es(row[11], preserve_newlines=True) if row[11] else None,
            "publishedAt": row[12].isoformat() if row[12] else None,
            "metadata": normalize_visible_metadata(row[13] or {}),
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
              AND {confirmed_duplicate_filter("d")}
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
def document_detail(document_id: str, include_chunks: bool = False):
    try:
        normalized_document_id = str(UUID(document_id))
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Documento no encontrado") from error

    with get_conn() as conn:
        columns = _document_columns(conn)
        metadata_column = "raw_metadata" if "raw_metadata" in columns else "metadata"
        text_column = "text" if "text" in columns else "content_text"
        author_column = "d.author" if "author" in columns else "NULL::text"
        category_column = "d.category" if "category" in columns else "NULL::text"
        tags_column = "d.tags" if "tags" in columns else "'[]'::jsonb"
        status_column = "d.status" if "status" in columns else "'READY'"
        created_at_column = "d.created_at AS created_at" if "created_at" in columns else "NULL::timestamptz AS created_at"
        updated_at_column = "d.updated_at AS updated_at" if "updated_at" in columns else "NULL::timestamptz AS updated_at"
        source_url_expr = f"COALESCE(d.{metadata_column}->>'source_url', d.canonical_url)"
        description_expr = _document_description_expr(columns, metadata_column)
        chunks_available_expr = (
            "(SELECT count(*)::int FROM document_chunks dc WHERE dc.document_id = d.id)"
            if _table_exists(conn, "document_chunks")
            else "0"
        )
        active_document_filter = "AND d.deleted_at IS NULL" if "deleted_at" in columns else ""
        doc = conn.execute(
            f"""
            SELECT
              d.id::text,
              d.title,
              {author_column} AS author,
              s.name AS source_name,
              COALESCE(d.{metadata_column}->>'source_type', s.key) AS source_type,
              {source_url_expr} AS source_url,
              d.canonical_url,
              d.language,
              {category_column} AS category,
              d.published_at,
              {description_expr} AS summary,
              d.{text_column} AS document_text,
              {tags_column} AS tags,
              CASE WHEN d.is_indexed THEN 'INDEXED' ELSE upper(coalesce({status_column}, 'PENDING')) END AS document_status,
              {created_at_column},
              {updated_at_column},
              d.{metadata_column} AS metadata,
              {chunks_available_expr} AS chunks_available
            FROM documents d
            JOIN sources s ON s.id = d.source_id
            WHERE d.id = %s
              {active_document_filter}
            """,
            (normalized_document_id,),
        ).fetchone()
        related_tags = []
        document_tag_columns = _table_columns(conn, "document_tags") if _table_exists(conn, "document_tags") else set()
        tag_columns = _table_columns(conn, "tags") if _table_exists(conn, "tags") else set()
        if doc and {"document_id", "tag_id"} <= document_tag_columns and {"id", "name"} <= tag_columns:
            related_tags = [
                row[0]
                for row in conn.execute(
                    """
                    SELECT t.name AS tag_name
                    FROM document_tags dt
                    JOIN tags t ON t.id = dt.tag_id
                    WHERE dt.document_id = %s
                    ORDER BY t.name
                    """,
                    (normalized_document_id,),
                ).fetchall()
            ]
        chunks = []
        if doc and include_chunks and _table_exists(conn, "document_chunks"):
            chunk_columns = _table_columns(conn, "document_chunks")
            chunk_text_column = "text" if "text" in chunk_columns else "content"
            chunk_metadata_column = "metadata" if "metadata" in chunk_columns else "'{}'::jsonb"
            chunk_section_column = "section_title" if "section_title" in chunk_columns else "NULL"
            chunks = conn.execute(
                f"""
                SELECT
                  dc.id::text AS id,
                  dc.chunk_index AS chunk_index,
                  {f"dc.{chunk_section_column}" if chunk_section_column != "NULL" else "NULL::text"} AS section_title,
                  dc.{chunk_text_column} AS chunk_text,
                  {f"dc.{chunk_metadata_column}" if chunk_metadata_column != "'{}'::jsonb" else chunk_metadata_column} AS metadata
                FROM document_chunks dc
                WHERE dc.document_id = %s
                ORDER BY dc.chunk_index
                LIMIT 200
                """,
                (normalized_document_id,),
            ).fetchall()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Documento no encontrado")
    source_type = normalize_source_type(doc[4]) or doc[4]
    published_at = doc[9].isoformat() if doc[9] else None
    created_at = doc[14].isoformat() if doc[14] else None
    updated_at = doc[15].isoformat() if doc[15] else None
    tags = list(dict.fromkeys(normalize_tag_es(tag) for tag in [*_string_list(doc[12]), *related_tags]))
    return {
        "id": doc[0],
        "title": normalize_text_es(doc[1]),
        "author": normalize_text_es(doc[2]) if doc[2] else None,
        "source": normalize_text_es(doc[3]),
        "source_type": source_type,
        "sourceType": source_type,
        "source_url": doc[5],
        "sourceUrl": doc[5],
        "canonical_url": doc[6],
        "canonicalUrl": doc[6],
        "language": doc[7],
        "category": doc[8],
        "type": doc[8] or source_type,
        "published_at": published_at,
        "publishedAt": published_at,
        "year": doc[9].year if doc[9] else None,
        "summary": normalize_text_es(doc[10], preserve_newlines=True) if doc[10] else None,
        "description": normalize_text_es(doc[10], preserve_newlines=True) if doc[10] else None,
        "text": normalize_text_es(doc[11], preserve_newlines=True) if doc[11] else None,
        "tags": tags,
        "topics": tags,
        "status": doc[13],
        "created_at": created_at,
        "createdAt": created_at,
        "updated_at": updated_at,
        "updatedAt": updated_at,
        "chunks_available": doc[17],
        "chunksAvailable": doc[17],
        "metadata": normalize_visible_metadata(_safe_metadata(doc[16])),
        "chunks": [
            {
                "id": chunk[0],
                "index": chunk[1],
                "section_title": normalize_text_es(chunk[2]) if chunk[2] else None,
                "text": normalize_text_es(chunk[3], preserve_newlines=True),
                "metadata": normalize_visible_metadata(_safe_metadata(chunk[4])),
            }
            for chunk in chunks
        ],
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
                return {"items": [{"id": r[0], "name": normalize_text_es(r[1]), "slug": r[2]} for r in rows]}
        fallback_where = f"author IS NOT NULL AND author <> '' AND {confirmed_duplicate_filter('documents')}"
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
            {
                "name": normalize_text_es(row[0]),
                "slug": normalize_text_es(row[0]).lower().replace(" ", "-"),
                "documentCount": row[1],
            }
            for row in rows
        ]
    }


@router.get("/topics")
def topics(limit: int = 50):
    with get_conn() as conn:
        if _table_exists(conn, "tags"):
            rows = conn.execute("SELECT id::text, name, slug FROM tags ORDER BY name LIMIT %s", (limit,)).fetchall()
            if rows:
                return {"items": [{"id": r[0], "name": normalize_tag_es(r[1]), "slug": r[2]} for r in rows]}
        rows = conn.execute(
            f"""
            SELECT name, sum(count)::int AS count
            FROM (
              SELECT value AS name, count(*)::int AS count
              FROM documents d
              CROSS JOIN LATERAL jsonb_array_elements_text(
                CASE WHEN jsonb_typeof(d.tags) = 'array' THEN d.tags ELSE '[]'::jsonb END
              ) AS tag(value)
              WHERE {confirmed_duplicate_filter("d")}
              GROUP BY value
              UNION ALL
              SELECT category AS name, count(*)::int AS count
              FROM documents d
              WHERE category IS NOT NULL AND category <> ''
                AND {confirmed_duplicate_filter("d")}
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
                f"""
                SELECT title AS name, 1::int AS count
                FROM documents d
                WHERE {confirmed_duplicate_filter("d")}
                ORDER BY updated_at DESC, title
                LIMIT %(limit)s
                """,
                {"limit": limit},
            ).fetchall()
    return {
        "items": [
            {
                "name": normalize_tag_es(row[0]),
                "slug": normalize_tag_es(row[0]).lower().replace(" ", "-"),
                "documentCount": row[1],
            }
            for row in rows
        ]
    }


def _document_search(query: str, limit: int, filters=None, language: str | None = None) -> list[dict]:
    normalized_query = query.strip()
    if len(normalized_query) < 2:
        return []
    with get_conn() as conn:
        columns = _document_columns(conn)
        metadata_column = "raw_metadata" if "raw_metadata" in columns else "metadata"
        text_column = "text" if "text" in columns else "content_text"
        author_column = "author" if "author" in columns else "NULL"
        tags_column = "d.tags" if "tags" in columns else "'[]'::jsonb"
        scripture_refs_expr = "d.scripture_refs" if "scripture_refs" in columns else "'[]'::jsonb"
        source_type_expr = f"COALESCE(d.{metadata_column}->>'source_type', s.key)"
        source_url_expr = f"COALESCE(d.{metadata_column}->>'source_url', d.canonical_url)"
        description_expr = _document_description_expr(columns, metadata_column)
        chunk_columns = _table_columns(conn, "document_chunks") if _table_exists(conn, "document_chunks") else set()
        has_chunks = {"document_id", "chunk_index"} <= chunk_columns and bool({"text", "content"} & chunk_columns)
        chunk_text_column = "text" if "text" in chunk_columns else "content"
        chunk_section_column = "dc.section_title" if "section_title" in chunk_columns else "NULL::text AS section_title"
        document_tag_columns = _table_columns(conn, "document_tags") if _table_exists(conn, "document_tags") else set()
        tag_columns = _table_columns(conn, "tags") if _table_exists(conn, "tags") else set()
        has_document_tags = {"document_id", "tag_id"} <= document_tag_columns and {"id", "name"} <= tag_columns
        chunk_match_expr = (
            "EXISTS (SELECT 1 FROM document_chunks search_chunk "
            f"WHERE search_chunk.document_id = d.id AND search_chunk.{chunk_text_column} ILIKE ANY(%(patterns)s))"
            if has_chunks
            else "FALSE"
        )
        chunk_join = (
            f"""
            LEFT JOIN LATERAL (
              SELECT dc.id::text, {chunk_section_column}, dc.{chunk_text_column}
              FROM document_chunks dc
              WHERE dc.document_id = d.id
                AND dc.{chunk_text_column} ILIKE ANY(%(patterns)s)
              ORDER BY dc.chunk_index
              LIMIT 1
            ) matched_chunk ON TRUE
            """
            if has_chunks
            else "LEFT JOIN LATERAL (SELECT NULL::text AS id, NULL::text AS section_title, NULL::text AS text) matched_chunk ON TRUE"
        )
        related_tag_match_expr = (
            "EXISTS (SELECT 1 FROM document_tags dt JOIN tags t ON t.id = dt.tag_id "
            "WHERE dt.document_id = d.id AND t.name ILIKE ANY(%(patterns)s))"
            if has_document_tags
            else "FALSE"
        )
        related_tags_expr = (
            "COALESCE((SELECT jsonb_agg(t.name ORDER BY t.name) FROM document_tags dt "
            "JOIN tags t ON t.id = dt.tag_id WHERE dt.document_id = d.id), "
            f"{tags_column}, '[]'::jsonb)"
            if has_document_tags
            else f"COALESCE({tags_column}, '[]'::jsonb)"
        )
        filter_where, filter_params = _metadata_filter_sql(filters, language, source_type_expr, columns)
        if "deleted_at" in columns:
            filter_where.append("d.deleted_at IS NULL")
        filter_where.append(confirmed_duplicate_filter("d"))
        patterns = [f"%{normalized_query}%"]
        terms = _search_terms(normalized_query)
        patterns.extend(f"%{term}%" for term in terms if len(term) >= 3)
        patterns = list(dict.fromkeys(patterns))
        match_where = f"""
          d.title ILIKE ANY(%(patterns)s)
          OR coalesce({author_column}, '') ILIKE ANY(%(patterns)s)
          OR s.name ILIKE ANY(%(patterns)s)
          OR coalesce({description_expr}, '') ILIKE ANY(%(patterns)s)
          OR coalesce(d.{text_column}, '') ILIKE ANY(%(patterns)s)
          OR {tags_column}::text ILIKE ANY(%(patterns)s)
          OR {chunk_match_expr}
          OR {related_tag_match_expr}
        """
        rows = conn.execute(
            f"""
            SELECT
              d.id::text,
              d.title,
              {author_column},
              s.name,
              d.language,
              d.canonical_url,
              {source_url_expr},
              {source_type_expr} AS source_key,
              left(
                coalesce(
                  nullif(matched_chunk.text, ''),
                  nullif({description_expr}, ''),
                  nullif(d.{text_column}, ''),
                  d.title
                ),
                520
              ) AS snippet,
              {scripture_refs_expr} AS scripture_refs,
              {related_tags_expr} AS tags,
              matched_chunk.id,
              matched_chunk.section_title,
              (
                CASE WHEN d.title ILIKE %(exact)s THEN 5 ELSE 0 END +
                CASE WHEN coalesce({author_column}, '') ILIKE %(exact)s THEN 3 ELSE 0 END +
                CASE WHEN s.name ILIKE %(exact)s THEN 2 ELSE 0 END +
                CASE WHEN coalesce({description_expr}, '') ILIKE ANY(%(patterns)s) THEN 2 ELSE 0 END +
                CASE WHEN coalesce(d.{text_column}, '') ILIKE ANY(%(patterns)s) THEN 1 ELSE 0 END +
                CASE WHEN {tags_column}::text ILIKE ANY(%(patterns)s) OR {related_tag_match_expr} THEN 2 ELSE 0 END +
                CASE WHEN matched_chunk.id IS NOT NULL THEN 2 ELSE 0 END
              )::float AS match_score
            FROM documents d
            JOIN sources s ON s.id = d.source_id
            {chunk_join}
            WHERE ({match_where})
              {"AND " + " AND ".join(filter_where) if filter_where else ""}
            ORDER BY match_score DESC, d.updated_at DESC
            LIMIT %(limit)s
            """,
            {
                "exact": f"%{normalized_query}%",
                "patterns": patterns,
                "limit": limit,
                **filter_params,
            },
        ).fetchall()
    return [
        {
            "id": row[0],
            "title": normalize_text_es(row[1]),
            "author": normalize_text_es(row[2]) if row[2] else None,
            "source": normalize_text_es(row[3]),
            "language": row[4],
            "canonical_url": row[5],
            "source_url": row[6],
            "source_key": normalize_source_type(row[7]) or row[7],
            "snippet": normalize_text_es(row[8], preserve_newlines=True),
            "scripture_refs": row[9] or [],
            "tags": [normalize_tag_es(tag) for tag in _string_list(row[10])],
            "chunk_id": row[11],
            "section_title": normalize_text_es(row[12]) if row[12] else None,
            "score": min(float(row[13] or 0) / 17, 1.0),
        }
        for row in rows
    ]


def _textual_search_response(payload: SearchRequest, warnings: list[str] | None = None) -> dict:
    rows = _document_search(payload.query, payload.limit, payload.filters, payload.language)
    response_warnings = list(warnings or [])
    if payload.query and len(payload.query) < 2:
        response_warnings.append("Escribe al menos 2 caracteres para buscar.")
    items = [
        {
            "chunk_id": row["chunk_id"] or row["id"],
            "document_id": row["id"],
            "title": row["title"],
            "author": row["author"],
            "source": row["source"],
            "source_key": row["source_key"],
            "source_url": row["source_url"],
            "canonical_url": row["canonical_url"],
            "language": row["language"],
            "section_title": row["section_title"] or "Documento",
            "snippet": row["snippet"],
            "score": row["score"],
            "semantic_score": None,
            "bm25_score": None,
            "rerank_score": None,
            "tags": row["tags"],
            "metadata": {
                "fallback": "postgres_text",
                "scripture_refs": row["scripture_refs"],
                "scripture_refs_structured": structured_scripture_refs(row["scripture_refs"]),
            },
        }
        for row in rows
    ]
    return {
        "query": payload.query,
        "rewritten_query": None,
        "mode": "postgres_text",
        "warnings": response_warnings,
        "items": items,
        "results": items,
        "total": len(items),
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
    if filters.include_seed is False:
        metadata_column = "raw_metadata" if "raw_metadata" in columns else "metadata"
        where.append(
            f"coalesce(d.{metadata_column}->>'is_seed', d.{metadata_column}->>'seed_content', 'false') <> 'true'"
        )
    return where, params


def _document_columns(conn) -> set[str]:
    return _table_columns(conn, "documents")


def _table_columns(conn, table_name: str) -> set[str]:
    return {
        row[0]
        for row in conn.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = %s
            """,
            (table_name,),
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


def _document_description_expr(columns: set[str], metadata_column: str) -> str:
    options = []
    if "summary" in columns:
        options.append("d.summary")
    if "description" in columns:
        options.append("d.description")
    options.extend(
        [
            f"d.{metadata_column}->>'summary'",
            f"d.{metadata_column}->>'description'",
        ]
    )
    return f"COALESCE({', '.join(options)})"


def _search_terms(query: str) -> list[str]:
    stopwords = {
        "about",
        "como",
        "cual",
        "desde",
        "does",
        "from",
        "mention",
        "mentions",
        "para",
        "pero",
        "por",
        "que",
        "sources",
        "sobre",
        "teach",
        "that",
        "the",
        "una",
        "what",
        "where",
        "with",
    }
    cleaned = query.replace("?", " ").replace(",", " ").replace(".", " ")
    return [
        token.casefold()
        for token in cleaned.split()
        if len(token) > 2 and token.casefold() not in stopwords
    ][:8]


def _string_list(value) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if item]
    if isinstance(value, tuple):
        return [str(item) for item in value if item]
    if isinstance(value, dict):
        return [str(item) for item in value.values() if item]
    return [str(value)]


SENSITIVE_METADATA_TERMS = (
    "api_key",
    "authorization",
    "cookie",
    "database_url",
    "password",
    "secret",
    "service_role",
    "token",
)


def _safe_metadata(value):
    if isinstance(value, dict):
        return {
            str(key): _safe_metadata(item)
            for key, item in value.items()
            if not any(term in str(key).casefold() for term in SENSITIVE_METADATA_TERMS)
        }
    if isinstance(value, list):
        return [_safe_metadata(item) for item in value]
    return value
