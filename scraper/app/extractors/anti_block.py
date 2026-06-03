from dataclasses import dataclass


BLOCK_PATTERNS = (
    "cloudflare",
    "attention required",
    "checking your browser",
    "access denied",
    "temporarily blocked",
    "captcha",
    "verify you are human",
)


@dataclass(frozen=True)
class BlockDetection:
    is_blocked: bool
    reason: str | None = None


def detect_block(html: str, status: int | None = None) -> BlockDetection:
    if status in {403, 429, 503}:
        return BlockDetection(True, f"http_status_{status}")
    lowered = html[:8000].lower()
    for pattern in BLOCK_PATTERNS:
        if pattern in lowered:
            return BlockDetection(True, pattern)
    return BlockDetection(False)
