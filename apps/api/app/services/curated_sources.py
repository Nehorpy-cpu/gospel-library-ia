from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import parse_qs, urlsplit


@dataclass(frozen=True)
class CuratedSource:
    key: str
    name: str
    source_type: str
    base_url: str
    is_official: bool
    trust_level: int


DISCURSOS_SUD = CuratedSource(
    key="discursos_sud_es",
    name="Discursos SUD",
    source_type="discursos_sud_es",
    base_url="https://discursosud.com",
    is_official=False,
    trust_level=8,
)
BYU_SPEECHES_ES = CuratedSource(
    key="byu_speeches_es",
    name="BYU Speeches Español",
    source_type="byu_speeches_es",
    base_url="https://speeches.byu.edu/spa/talks",
    is_official=False,
    trust_level=8,
)
CHURCH_OFFICIAL_ES = CuratedSource(
    key="church_official_es",
    name="La Iglesia de Jesucristo de los Santos de los Últimos Días",
    source_type="church_official_es",
    base_url="https://www.churchofjesuschrist.org/study",
    is_official=True,
    trust_level=10,
)

AUTHORIZED_SOURCES = {
    "discursosud.com": DISCURSOS_SUD,
    "www.discursosud.com": DISCURSOS_SUD,
    "speeches.byu.edu": BYU_SPEECHES_ES,
    "www.speeches.byu.edu": BYU_SPEECHES_ES,
    "churchofjesuschrist.org": CHURCH_OFFICIAL_ES,
    "www.churchofjesuschrist.org": CHURCH_OFFICIAL_ES,
}


def curated_source_for_url(value: str) -> CuratedSource | None:
    parsed = urlsplit(value)
    if parsed.scheme.casefold() != "https":
        return None
    source = AUTHORIZED_SOURCES.get((parsed.hostname or "").casefold())
    if not source:
        return None
    path = parsed.path.rstrip("/") or "/"
    if source is DISCURSOS_SUD:
        parts = [part.casefold() for part in path.split("/") if part]
        navigation_prefixes = {"author", "category", "page", "search", "tag"}
        return source if parts and parts[0] not in navigation_prefixes else None
    if source is BYU_SPEECHES_ES:
        parts = [part for part in path.split("/") if part]
        return source if len(parts) >= 4 and parts[:2] == ["spa", "talks"] else None
    if source is CHURCH_OFFICIAL_ES:
        language = parse_qs(parsed.query).get("lang", [])
        parts = [part for part in path.split("/") if part]
        return source if len(parts) >= 3 and parts[0] == "study" and "spa" in language else None
    return None
