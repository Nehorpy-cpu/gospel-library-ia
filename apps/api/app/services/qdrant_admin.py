from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

from app.core.config import get_settings


class QdrantAdmin:
    def __init__(self) -> None:
        settings = get_settings()
        self.settings = settings
        self.client = QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)

    def ensure_collection(self) -> dict:
        existing = [c.name for c in self.client.get_collections().collections]
        if self.settings.qdrant_collection not in existing:
            self.client.create_collection(
                collection_name=self.settings.qdrant_collection,
                vectors_config=VectorParams(size=self.settings.qdrant_dimensions, distance=Distance.COSINE),
            )
        for field in ["author", "language", "source_key", "category", "topic", "published_at", "tags"]:
            try:
                self.client.create_payload_index(
                    collection_name=self.settings.qdrant_collection,
                    field_name=field,
                    field_schema="keyword",
                )
            except Exception:
                pass
        info = self.client.get_collection(self.settings.qdrant_collection)
        return {"collection": self.settings.qdrant_collection, "status": str(info.status), "vectors": info.points_count}
