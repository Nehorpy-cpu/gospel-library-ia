import random

import httpx
from playwright.async_api import async_playwright
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.config import get_settings
from app.extractors.anti_block import BlockDetection, detect_block


class FetchResult:
    def __init__(
        self,
        *,
        url: str,
        status_code: int,
        content: bytes,
        content_type: str | None,
        block: BlockDetection,
    ) -> None:
        self.url = url
        self.status_code = status_code
        self.content = content
        self.content_type = content_type
        self.block = block

    @property
    def text(self) -> str:
        return self.content.decode("utf-8", errors="replace")


class Fetcher:
    def __init__(self) -> None:
        self.settings = get_settings()

    def headers(self) -> dict[str, str]:
        return {
            "User-Agent": random.choice(self.settings.crawler_user_agent_pool),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "es,en-US;q=0.8,en;q=0.6,pt;q=0.5",
        }

    @retry(
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.TransportError)),
        stop=stop_after_attempt(get_settings().retry_max_attempts),
        wait=wait_exponential(
            multiplier=1,
            min=get_settings().retry_backoff_min_seconds,
            max=get_settings().retry_backoff_max_seconds,
        ),
        reraise=True,
    )
    async def fetch_http(self, url: str) -> FetchResult:
        async with httpx.AsyncClient(
            timeout=self.settings.crawler_timeout_seconds,
            follow_redirects=True,
            headers=self.headers(),
        ) as client:
            response = await client.get(url)
        content_type = response.headers.get("content-type")
        text = response.text if "html" in (content_type or "") else ""
        return FetchResult(
            url=str(response.url),
            status_code=response.status_code,
            content=response.content,
            content_type=content_type,
            block=detect_block(text, response.status_code),
        )

    async def fetch_playwright(self, url: str) -> FetchResult:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=self.settings.playwright_headless)
            page = await browser.new_page(user_agent=random.choice(self.settings.crawler_user_agent_pool))
            response = await page.goto(url, wait_until="networkidle", timeout=self.settings.crawler_timeout_seconds * 1000)
            content = await page.content()
            status = response.status if response else 200
            await browser.close()
        return FetchResult(
            url=url,
            status_code=status,
            content=content.encode("utf-8"),
            content_type="text/html; charset=utf-8",
            block=detect_block(content, status),
        )

    async def fetch(self, url: str) -> FetchResult:
        result = await self.fetch_http(url)
        if result.block.is_blocked and self.settings.playwright_enabled:
            return await self.fetch_playwright(url)
        return result
