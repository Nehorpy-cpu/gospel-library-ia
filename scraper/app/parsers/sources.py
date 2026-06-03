from app.parsers.base import BaseParser


class DiscursoSudParser(BaseParser):
    source_key = "discursos_sud"

    def can_parse(self, url: str) -> bool:
        return "discursosud.com" in url


class ByuSpeechesParser(BaseParser):
    source_key = "byu_speeches_en"

    def can_parse(self, url: str) -> bool:
        return "speeches.byu.edu" in url and "/spa/" not in url


class ByuSpeechesSpanishParser(BaseParser):
    source_key = "byu_speeches_es"

    def can_parse(self, url: str) -> bool:
        return "speeches.byu.edu/spa/" in url


class ChurchParser(BaseParser):
    source_key = "general_conference"

    def can_parse(self, url: str) -> bool:
        return "churchofjesuschrist.org" in url


class JosephSmithPapersParser(BaseParser):
    source_key = "joseph_smith_papers"

    def can_parse(self, url: str) -> bool:
        return "josephsmithpapers.org" in url


class ByuRscParser(BaseParser):
    source_key = "byu_rsc"

    def can_parse(self, url: str) -> bool:
        return "rsc.byu.edu" in url


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
