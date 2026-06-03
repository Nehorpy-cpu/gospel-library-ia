from app.services.qdrant_admin import QdrantAdmin


if __name__ == "__main__":
    print(QdrantAdmin().ensure_collection())
