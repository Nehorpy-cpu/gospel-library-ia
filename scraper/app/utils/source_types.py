from urllib.parse import urlparse


def source_type_for_url(source_key: str | None, url: str | None) -> str:
    parsed = urlparse(url or "")
    host = parsed.netloc.lower()
    path = parsed.path.lower()

    if "speeches.byu.edu" in host:
        return "byu_speeches_es" if "/spa/" in path else "byu_speeches_en"
    if "discursosud.com" in host:
        return "discursos_sud"
    if "josephsmithpapers.org" in host:
        return "joseph_smith_papers"
    if "rsc.byu.edu" in host:
        return "byu_rsc"
    if "churchofjesuschrist.org" in host:
        if "/general-conference" in path:
            return "general_conference"
        if "/manual" in path or "/study/manual" in path:
            return "church_manuals"
        if "/scriptures" in path:
            return "scriptures"
        if "news" in host or "/news" in path:
            return "church_news"
        if source_key in {"general_conference", "church_manuals", "scriptures"}:
            return source_key
        return "churchofjesuschrist"

    legacy_map = {
        "byu_speeches": "byu_speeches_en",
        "discursosud": "discursos_sud",
        "churchofjesuschrist": "churchofjesuschrist",
        "josephsmithpapers": "joseph_smith_papers",
    }
    return legacy_map.get(source_key or "", source_key or "custom")
