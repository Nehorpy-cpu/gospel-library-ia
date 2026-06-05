from app.parsers.base import BaseParser


class DiscursoSudParser(BaseParser):
    source_key = "discursos_sud"

    def can_parse(self, url: str) -> bool:
        return "discursosud.com" in url

    def parse(self, url: str, html: str):
        document = super().parse(url, html)
        document.category = document.category or "Discursos SUD"
        document.metadata = {**document.metadata, "parser": "discursos_sud", "canonicalUrl": document.url}
        return document


class ByuSpeechesParser(BaseParser):
    source_key = "byu_speeches_en"

    def can_parse(self, url: str) -> bool:
        return "speeches.byu.edu" in url and "/spa/" not in url

    def parse(self, url: str, html: str):
        document = super().parse(url, html)
        document.category = document.category or "BYU Speeches"
        document.metadata = {**document.metadata, "parser": "byu_speeches_en", "canonicalUrl": document.url}
        return document


class ByuSpeechesSpanishParser(BaseParser):
    source_key = "byu_speeches_es"

    def can_parse(self, url: str) -> bool:
        return "speeches.byu.edu/spa/" in url

    def parse(self, url: str, html: str):
        document = super().parse(url, html)
        document.language = document.language or "es"
        document.category = document.category or "BYU Speeches Espanol"
        document.metadata = {**document.metadata, "parser": "byu_speeches_es", "canonicalUrl": document.url}
        return document


class ChurchParser(BaseParser):
    source_key = "general_conference"

    def can_parse(self, url: str) -> bool:
        return "churchofjesuschrist.org" in url

    def parse(self, url: str, html: str):
        document = super().parse(url, html)
        if "/study/scriptures" in url:
            document.category = document.category or "Escrituras"
        elif "/study/manual" in url:
            document.category = document.category or "Manuales de la Iglesia"
        else:
            document.category = document.category or "Conferencia General"
        document.metadata = {**document.metadata, "parser": "church_library", "canonicalUrl": document.url}
        return document


class JosephSmithPapersParser(BaseParser):
    source_key = "joseph_smith_papers"

    def can_parse(self, url: str) -> bool:
        return "josephsmithpapers.org" in url

    def parse(self, url: str, html: str):
        document = super().parse(url, html)
        document.category = document.category or "Documento historico"
        document.metadata = {
            **document.metadata,
            "parser": "joseph_smith_papers",
            "canonicalUrl": document.url,
            "source_note": "Fuente historica/documental; no es manual doctrinal oficial de la Iglesia.",
        }
        return document


class ByuRscParser(BaseParser):
    source_key = "byu_rsc"

    def can_parse(self, url: str) -> bool:
        return "rsc.byu.edu" in url

    def parse(self, url: str, html: str):
        document = super().parse(url, html)
        document.category = document.category or "BYU Religious Studies Center"
        document.metadata = {**document.metadata, "parser": "byu_rsc", "canonicalUrl": document.url}
        return document


PARSERS: list[BaseParser] = [
    DiscursoSudParser(),
    ByuSpeechesSpanishParser(),
    ByuSpeechesParser(),
    ChurchParser(),
    JosephSmithPapersParser(),
    ByuRscParser(),
]


def parser_for_url(url: str) -> BaseParser:
    for parser in PARSERS:
        if parser.can_parse(url):
            return parser
    raise ValueError(f"No parser registered for URL: {url}")
