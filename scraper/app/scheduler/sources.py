from app.db.session import SessionLocal
from app.repositories import get_or_create_source


DEFAULT_SOURCES = [
    ("discursos_sud", "Discurso SUD", "https://discursosud.com/"),
    ("byu_speeches_en", "BYU Speeches", "https://speeches.byu.edu/"),
    ("byu_speeches_es", "BYU Speeches Spanish", "https://speeches.byu.edu/spa/talks/"),
    ("general_conference", "General Conference", "https://www.churchofjesuschrist.org/study/general-conference"),
    ("church_manuals", "Church Manuals", "https://www.churchofjesuschrist.org/study/manual"),
    ("joseph_smith_papers", "Joseph Smith Papers", "https://www.josephsmithpapers.org/"),
    ("byu_rsc", "BYU Religious Studies Center", "https://rsc.byu.edu/"),
]


def seed_sources() -> None:
    with SessionLocal() as db:
        for key, name, base_url in DEFAULT_SOURCES:
            get_or_create_source(db, key, name, base_url)
