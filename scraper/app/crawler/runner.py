from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

from app.crawler.spiders.source_spider import SourceSpider


def run_spider(source_key: str, start_url: str, max_pages_per_run: int | None = None) -> None:
    process = CrawlerProcess(get_project_settings())
    process.crawl(SourceSpider, source_key=source_key, start_url=start_url, max_pages_per_run=max_pages_per_run)
    process.start()
