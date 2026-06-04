CURRENT_LEADERSHIP_REFERENCE = {
    "reference_year": 2026,
    "verification_required": True,
    "official_sources": [
        "https://www.churchofjesuschrist.org/study/manual/leadership-portraits/001?lang=eng",
        "https://www.churchofjesuschrist.org/learn/quorum-of-the-twelve-apostles?lang=eng",
        "https://newsroom.churchofjesuschrist.org/article/first-presidencys-2026-easter-message",
    ],
    "first_presidency": [
        {
            "name": "Dallin H. Oaks",
            "title": "President of The Church of Jesus Christ of Latter-day Saints",
        },
        {"name": "Henry B. Eyring", "title": "First Counselor in the First Presidency"},
        {"name": "D. Todd Christofferson", "title": "Second Counselor in the First Presidency"},
    ],
    "quorum_of_the_twelve": [
        "David A. Bednar",
        "Dieter F. Uchtdorf",
        "Quentin L. Cook",
        "Neil L. Andersen",
        "Ronald A. Rasband",
        "Gary E. Stevenson",
        "Dale G. Renlund",
        "Gerrit W. Gong",
        "Ulisses Soares",
        "Patrick Kearon",
        "Gérald Caussé",
        "Clark G. Gilbert",
    ],
    "historical_prophet_reference": "Russell M. Nelson",
    "current_president_reference": "Dallin H. Oaks",
}


LEADERSHIP_QUERY_TERMS = (
    "primera presidencia",
    "first presidency",
    "cuorum de los doce",
    "cuórum de los doce",
    "quorum of the twelve",
    "apostoles actuales",
    "apóstoles actuales",
    "liderazgo vigente",
    "current leadership",
    "presidente actual",
    "current president",
)


def leadership_system_policy() -> str:
    first_presidency = "; ".join(
        f"{leader['name']} ({leader['title']})"
        for leader in CURRENT_LEADERSHIP_REFERENCE["first_presidency"]
    )
    twelve = "; ".join(CURRENT_LEADERSHIP_REFERENCE["quorum_of_the_twelve"])
    sources = "; ".join(CURRENT_LEADERSHIP_REFERENCE["official_sources"])
    return f"""
Regla de actualidad sobre liderazgo general:
- Cuando cites o te refieras a la Primera Presidencia o al Cuorum de los Doce Apostoles, trata la conformacion vigente como informacion sensible al tiempo.
- Si el CONTEXTO contiene fuentes oficiales recientes de La Iglesia de Jesucristo de los Santos de los Ultimos Dias, verifica y usa esas fuentes antes de afirmar quienes integran el liderazgo vigente.
- Si el CONTEXTO no contiene evidencia oficial suficiente para confirmar la conformacion vigente, dilo claramente y no presentes la referencia local como verificacion definitiva.
- Referencia local para 2026, hasta que fuentes oficiales mas recientes indiquen otra cosa:
  Primera Presidencia: {first_presidency}.
  Cuorum de los Doce Apostoles: {twelve}.
- Modo historico/devocional: puedes incluir citas del Presidente Russell M. Nelson como profeta anterior y lider doctrinal muy relevante cuando el contexto lo respalde.
- Modo liderazgo vigente: prioriza citas del Presidente Dallin H. Oaks como Presidente actual de la Iglesia cuando el contexto lo respalde; tambien puedes incluir ensenanzas del Presidente Nelson cuando sean doctrinalmente pertinentes.
- Fuentes oficiales de referencia para verificacion: {sources}.
""".strip()


def is_current_leadership_query(text: str) -> bool:
    normalized = text.casefold()
    return any(term in normalized for term in LEADERSHIP_QUERY_TERMS)
