from app.core.config import get_settings

settings = get_settings()

BOT_NAME = "gospel_library_ia"
SPIDER_MODULES = ["app.crawler.spiders"]
NEWSPIDER_MODULE = "app.crawler.spiders"

ROBOTSTXT_OBEY = settings.crawler_respect_robots_txt
CONCURRENT_REQUESTS = settings.crawler_concurrency
DOWNLOAD_DELAY = settings.crawler_download_delay_seconds
DOWNLOAD_TIMEOUT = settings.crawler_timeout_seconds
DEPTH_LIMIT = settings.crawler_max_depth
COOKIES_ENABLED = False

USER_AGENT = settings.crawler_user_agent_pool[0]

DOWNLOADER_MIDDLEWARES = {
    "app.crawler.middlewares.RandomUserAgentMiddleware": 400,
    "scrapy.downloadermiddlewares.retry.RetryMiddleware": 550,
}

RETRY_ENABLED = True
RETRY_TIMES = settings.retry_max_attempts
RETRY_HTTP_CODES = [408, 429, 500, 502, 503, 504, 522, 524]

ITEM_PIPELINES = {
    "app.crawler.pipelines.QueuePipeline": 300,
}

TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
DOWNLOAD_HANDLERS = {
    "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
    "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
}
PLAYWRIGHT_BROWSER_TYPE = "chromium"
PLAYWRIGHT_LAUNCH_OPTIONS = {"headless": settings.playwright_headless}
