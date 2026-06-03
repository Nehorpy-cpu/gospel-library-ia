from uuid import UUID

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, FieldCondition, Filter, MatchAny, PointStruct, VectorParams

from app.core.config import get_settings


class QdrantService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.client = QdrantClient(url=self.settings.qdrant_url, api_key=self.settings.qdrant_api_key)

    def ensure_collection(self) -> None:
        existing = [collection.name for collection in self.client.get_collections().collections]
        if self.settings.qdrant_collection not in existing:
            self.client.create_collection(
                collection_name=self.settings.qdrant_collection,
                vectors_config=VectorParams(
                    size=self.settings.openai_embedding_dimensions,
                    distance=Distance.COSINE,
                ),
            )
            for field in ["document_id", "source_key", "language", "author", "category", "topic", "published_at", "tags"]:
                self.client.create_payload_index(
                    collection_name=self.settings.qdrant_collection,
                    field_name=field,
                    field_schema="keyword",
                )

    def upsert(self, points: list[PointStruct]) -> None:
        self.ensure_collection()
        self.client.upsert(collection_name=self.settings.qdrant_collection, points=points, wait=False)

    def search(self, vector: list[float], limit: int, filters: dict | None = None):
        q_filter = self._build_filter(filters or {})
        return self.client.search(
            collection_name=self.settings.qdrant_collection,
            query_vector=vector,
            limit=limit,
            query_filter=q_filter,
            with_payload=True,
        )

    def _build_filter(self, filters: dict) -> Filter | None:
        must: list[FieldCondition] = []
        mapping = {
            "document_ids": "document_id",
            "source_keys": "source_key",
            "languages": "language",
            "authors": "author",
            "categories": "category",
        }
        for input_key, payload_key in mapping.items():
            values = filters.get(input_key)
            if values:
                must.append(
                    FieldCondition(
                        key=payload_key,
                        match=MatchAny(any=[str(value) for value in values]),
                    )
                )
        return Filter(must=must) if must else None


def point_id_for_chunk(chunk_id: UUID) -> UUID:
    return chunk_id
