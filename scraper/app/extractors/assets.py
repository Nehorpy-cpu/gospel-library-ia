from urllib.parse import urljoin

from bs4 import BeautifulSoup

from app.schemas.document import ExtractedAsset


def extract_assets(html: str, base_url: str) -> list[ExtractedAsset]:
    soup = BeautifulSoup(html, "lxml")
    assets: dict[str, ExtractedAsset] = {}

    for link in soup.find_all("a", href=True):
        href = urljoin(base_url, link["href"])
        lowered = href.lower().split("?")[0]
        if lowered.endswith(".pdf"):
            assets[href] = ExtractedAsset(url=href, asset_type="pdf", mime_type="application/pdf")
        elif lowered.endswith(".mp3"):
            assets[href] = ExtractedAsset(url=href, asset_type="mp3", mime_type="audio/mpeg")

    for audio in soup.find_all(["audio", "source"], src=True):
        src = urljoin(base_url, audio["src"])
        if ".mp3" in src.lower():
            assets[src] = ExtractedAsset(url=src, asset_type="mp3", mime_type="audio/mpeg")

    for iframe in soup.find_all("iframe", src=True):
        src = urljoin(base_url, iframe["src"])
        if "youtube" in src or "vimeo" in src or "churchofjesuschrist" in src:
            assets[src] = ExtractedAsset(url=src, asset_type="video", mime_type=None)

    return list(assets.values())
