from __future__ import annotations

from collections.abc import Mapping
import re
from typing import Any

SENSITIVE_KEYS = {
    "api_key",
    "apikey",
    "authorization",
    "cookie",
    "openai_api_key",
    "password",
    "password_hash",
    "qdrant_api_key",
    "refresh_token",
    "secret",
    "secret_access_key",
    "token",
}


def sanitize_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: ("[REDACTED]" if _is_sensitive_key(str(key)) else sanitize_value(item)) for key, item in value.items()}
    if isinstance(value, list):
        return [sanitize_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(sanitize_value(item) for item in value)
    if isinstance(value, str):
        return _redact_inline_secret(value)
    return value


def sanitize_event(_logger: Any, _method_name: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    return sanitize_value(event_dict)


def _is_sensitive_key(key: str) -> bool:
    normalized = key.lower().replace("-", "_")
    return normalized in SENSITIVE_KEYS or normalized.endswith("_token") or normalized.endswith("_secret")


def _redact_inline_secret(value: str) -> str:
    lowered = value.lower()
    if re.search(r"\bsk-[A-Za-z0-9_-]+", value):
        return "[REDACTED]"
    if any(marker in lowered for marker in ["authorization:", "bearer ", "api_key=", "password=", "secret="]):
        return "[REDACTED]"
    return value
