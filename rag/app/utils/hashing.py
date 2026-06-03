import hashlib
import re


WHITESPACE_RE = re.compile(r"\s+")


def normalize_for_hash(value: str) -> str:
    return WHITESPACE_RE.sub(" ", value).strip()


def sha256_text(value: str) -> str:
    return hashlib.sha256(normalize_for_hash(value).encode("utf-8")).hexdigest()
