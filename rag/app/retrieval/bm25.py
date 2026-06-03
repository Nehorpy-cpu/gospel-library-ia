from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.retrieval.types import RetrievedChunk
from app.schemas.search import MetadataFilter


class BM25Retriever:
    def search(self, db: Session, query: str, filters: MetadataFilter, limit: int) -> list[RetrievedChunk]:
        where = ["dc.search_vector @@ plainto_tsquery('simple', :query)"]
        params: dict = {"query": query, "limit": limit}

        if filters.languages:
            where.append("d.language = ANY(:languages)")
            params["languages"] = filters.languages
        if filters.source_keys:
            where.append("s.key = ANY(:source_keys)")
            params["source_keys"] = filters.source_keys
        if filters.authors:
            where.append("d.author = ANY(:authors)")
            params["authors"] = filters.authors
        if filters.categories:
            where.append("d.category = ANY(:categories)")
            params["categories"] = filters.categories
        if filters.document_ids:
            where.append("d.id = ANY(:document_ids)")
            params["document_ids"] = [str(value) for value in filters.document_ids]
        if filters.published_after:
            where.append("d.published_at >= :published_after")
            params["published_after"] = filters.published_after
        if filters.published_before:
            where.append("d.published_at <= :published_before")
            params["published_before"] = filters.published_before

        sql = text(
            f"""
            SELECT
              dc.id AS chunk_id,
              d.id AS document_id,
              d.title,
              dc.text,
              d.author,
              s.key AS source_key,
              d.canonical_url,
              d.published_at,
              d.language,
              dc.section_title,
              dc.metadata,
              ts_rank_cd(dc.search_vector, plainto_tsquery('simple', :query)) AS bm25_score
            FROM document_chunks dc
            JOIN documents d ON d.id = dc.document_id
            JOIN sources s ON s.id = d.source_id
            WHERE {" AND ".join(where)}
            ORDER BY bm25_score DESC
            LIMIT :limit
            """
        )
        rows = db.execute(sql, params).mappings().all()
        return [
            RetrievedChunk(
                chunk_id=UUID(str(row["chunk_id"])),
                document_id=UUID(str(row["document_id"])),
                title=row["title"],
                text=row["text"],
                author=row["author"],
                source_key=row["source_key"],
                canonical_url=row["canonical_url"],
                published_at=row["published_at"],
                language=row["language"],
                section_title=row["section_title"],
                bm25_score=float(row["bm25_score"] or 0),
                metadata=row["metadata"] or {},
            )
            for row in rows
        ]
