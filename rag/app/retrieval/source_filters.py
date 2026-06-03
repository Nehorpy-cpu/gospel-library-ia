CANONICAL_SOURCE_TYPES = (
    "byu_speeches_es",
    "byu_speeches_en",
    "discursos_sud",
    "general_conference",
    "church_manuals",
    "joseph_smith_papers",
    "byu_rsc",
)

SOURCE_ALIASES = {
    "byu_speeches_es": {"byu_speeches_es", "byu_speeches_spanish", "speeches_byu_es"},
    "byu_speeches_en": {"byu_speeches_en", "byu_speeches", "speeches_byu", "byu"},
    "discursos_sud": {"discursos_sud", "discurso_sud", "discursosud"},
    "general_conference": {"general_conference", "conference", "conferencia_general", "general-conference"},
    "church_manuals": {"church_manuals", "manuals", "manuales", "church_manual"},
    "joseph_smith_papers": {"joseph_smith_papers", "jsp", "josephsmithpapers"},
    "byu_rsc": {"byu_rsc", "rsc", "religious_studies_center"},
}


def normalize_source_type(value: str | None) -> str | None:
    if not value:
        return None
    normalized = value.strip().lower().replace("-", "_").replace(" ", "_")
    for canonical, aliases in SOURCE_ALIASES.items():
        if normalized == canonical or normalized in aliases:
            return canonical
    return normalized


def source_type_aliases(value: str | None) -> list[str]:
    normalized = normalize_source_type(value)
    if not normalized:
        return []
    aliases = set(SOURCE_ALIASES.get(normalized, set()))
    aliases.add(normalized)
    return sorted(aliases)


def expand_source_keys(values: list[str] | None) -> list[str] | None:
    if not values:
        return values
    expanded: set[str] = set()
    for value in values:
        expanded.update(source_type_aliases(value))
    return sorted(expanded)
