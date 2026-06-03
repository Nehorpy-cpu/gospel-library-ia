from app.db.session import Base, engine
from app.models import CrawlUrl, Document, DocumentAsset, IngestionJob, Source  # noqa: F401
from app.scheduler.sources import seed_sources
from app.storage.r2 import R2Storage


def main() -> None:
    Base.metadata.create_all(bind=engine)
    seed_sources()
    R2Storage().ensure_bucket()


if __name__ == "__main__":
    main()
