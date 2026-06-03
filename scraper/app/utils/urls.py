from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

import tldextract


TRACKING_PREFIXES = ("utm_",)
TRACKING_KEYS = {"fbclid", "gclid", "mc_cid", "mc_eid"}


def normalize_url(url: str, base_url: str | None = None) -> str:
    absolute = urljoin(base_url, url) if base_url else url
    parsed = urlparse(absolute)
    query = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=False)
        if key not in TRACKING_KEYS and not key.startswith(TRACKING_PREFIXES)
    ]
    normalized = parsed._replace(
        scheme=parsed.scheme.lower() or "https",
        netloc=parsed.netloc.lower(),
        query=urlencode(sorted(query)),
        fragment="",
    )
    result = urlunparse(normalized)
    return result[:-1] if result.endswith("/") else result


def registered_domain(url: str) -> str:
    extracted = tldextract.extract(url)
    return ".".join(part for part in [extracted.domain, extracted.suffix] if part)


def is_same_registered_domain(url: str, allowed_domains: list[str]) -> bool:
    domain = registered_domain(url)
    return any(domain == registered_domain(f"https://{allowed}") for allowed in allowed_domains)


def is_allowed_host(url: str, allowed_domains: list[str]) -> bool:
    host = urlparse(url).netloc.lower().split(":", 1)[0]
    for allowed in allowed_domains:
        allowed_host = allowed.lower().split(":", 1)[0]
        if host == allowed_host or host.endswith(f".{allowed_host}"):
            return True
    return False
