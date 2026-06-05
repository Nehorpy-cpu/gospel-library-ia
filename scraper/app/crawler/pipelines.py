from sqlalchemy import select

from app.db.session import SessionLocal
from app.logging.structured import logger
from app.models.crawl import Source
from app.models.enums import CrawlStatus
from app.repositories import upsert_crawl_url
from app.workers.tasks import fetch_url_task

log = logger(__name__)


class QueuePipeline:
    def process_item(self, item, spider):
        with SessionLocal() as db:
            source = db.scalar(select(Source).where(Source.key == item["source_key"]))
            if not source:
                return item
            crawl_url = upsert_crawl_url(
                db,
                source.id,
                item["url"],
                depth=int(item.get("depth") or 0),
                discovered_from=item.get("discovered_from"),
                status=CrawlStatus.QUEUED,
            )
            if getattr(crawl_url, "_was_requeued", True) is False:
                log.info(
                    "crawl_url_skipped_already_processed",
                    source_key=item["source_key"],
                    url=item["url"],
                    crawl_url_id=str(crawl_url.id),
                    status=crawl_url.status,
                )
                return item
            fetch_url_task.delay(str(crawl_url.id))
            log.info(
                "crawl_url_queued",
                source_key=item["source_key"],
                url=item["url"],
                crawl_url_id=str(crawl_url.id),
                depth=int(item.get("depth") or 0),
            )
        return item
