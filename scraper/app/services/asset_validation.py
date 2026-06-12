def asset_response_error(
    *,
    asset_type: str,
    final_url: str,
    status_code: int,
    content: bytes,
    content_type: str | None,
) -> str | None:
    normalized_content_type = (content_type or "").lower()
    normalized_url = final_url.lower()
    if status_code >= 400:
        return f"Asset returned HTTP {status_code}"
    if not content:
        return "Asset response was empty"
    if (
        "text/html" in normalized_content_type
        or "application/xhtml" in normalized_content_type
        or "/study/login" in normalized_url
    ):
        return f"Asset URL resolved to HTML/login content ({final_url})"
    if asset_type == "pdf" and b"%PDF-" not in content[:1024]:
        return f"PDF signature missing (content-type: {content_type or 'unknown'})"
    return None
