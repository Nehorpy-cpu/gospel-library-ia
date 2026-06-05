from urllib.parse import urljoin
from urllib.parse import urlparse

import scrapy

from app.core.config import get_settings
from app.crawler.items import DiscoveredUrlItem
from app.utils.urls import is_allowed_host, normalize_url


class SourceSpider(scrapy.Spider):
    name = "source_spider"

    def __init__(self, source_key: str, start_url: str, max_pages_per_run: int | None = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.source_key = source_key
        self.start_urls = [start_url]
        self.allowed_domain_values = get_settings().allowed_domains
        parsed_start = urlparse(start_url)
        self.start_host = parsed_start.netloc.lower()
        self.start_path_prefix = parsed_start.path.rstrip("/")
        self.max_pages_per_run = int(max_pages_per_run or get_settings().crawler_concurrency * 3)
        self.discovered_count = 0

    def _is_allowed_link(self, url: str) -> bool:
        if not url.startswith(("http://", "https://")):
            return False
        if not is_allowed_host(url, self.allowed_domain_values):
            return False
        if not is_allowed_host(url, [self.start_host]):
            return False
        if self.start_path_prefix:
            path = urlparse(url).path.rstrip("/")
            return path == self.start_path_prefix or path.startswith(f"{self.start_path_prefix}/")
        return True

    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(
                url,
                callback=self.parse,
                meta={"playwright": True, "depth": 0},
                dont_filter=True,
            )

    def parse(self, response):
        depth = response.meta.get("depth", 0)
        if self.discovered_count >= self.max_pages_per_run:
            return
        self.discovered_count += 1
        yield DiscoveredUrlItem(
            source_key=self.source_key,
            url=normalize_url(response.url),
            discovered_from=None,
            depth=depth,
        )

        if depth >= get_settings().crawler_max_depth:
            return

        for href in response.css("a::attr(href)").getall():
            if self.discovered_count >= self.max_pages_per_run:
                return
            url = normalize_url(urljoin(response.url, href))
            if not self._is_allowed_link(url):
                continue
            self.discovered_count += 1
            yield DiscoveredUrlItem(
                source_key=self.source_key,
                url=url,
                discovered_from=response.url,
                depth=depth + 1,
            )
            yield scrapy.Request(url, callback=self.parse, meta={"depth": depth + 1})
