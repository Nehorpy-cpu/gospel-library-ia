import argparse
import asyncio

from app.db.session import SessionLocal
from app.services.indexer import IndexingService


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    with SessionLocal() as db:
        count = await IndexingService().index_pending(db, limit=args.limit, force=args.force)
    print(f"indexed_chunks={count}")


if __name__ == "__main__":
    asyncio.run(main())
