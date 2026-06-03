from urllib.parse import urljoin
from urllib.parse import urlparse

import scrapy

from app.core.config import get_settings
from app.crawler.items import DiscoveredUrlItem
from app.utils.urls import is_allowed_host, normalize_url


class SourceSpider(scrapy.Spider):
    name = "source_spider"

    def __init__(self, source_key: str, start_url: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.source_key = source_key
        self.start_urls = [start_url]
        self.allowed_domain_values = get_settings().allowed_domains
        self.start_host = urlparse(start_url).netloc.lower()

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
        yield DiscoveredUrlItem(
            source_key=self.source_key,
            url=normalize_url(response.url),
            discovered_from=None,
            depth=depth,
        )

        if depth >= get_settings().crawler_max_depth:
            return

        for href in response.css("a::attr(href)").getall():
            url = normalize_url(urljoin(response.url, href))
            if not url.startswith(("http://", "https://")):
                continue
            if not is_allowed_host(url, self.allowed_domain_values):
                continue
            if not is_allowed_host(url, [self.start_host]):
                continue
            yield DiscoveredUrlItem(
                source_key=self.source_key,
                url=url,
                discovered_from=response.url,
                depth=depth + 1,
            )
            yield scrapy.Request(url, callback=self.parse, meta={"depth": depth + 1})
