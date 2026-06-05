import re

from bs4 import BeautifulSoup

try:
    from readability import Document as ReadabilityDocument
except ImportError:  # pragma: no cover - local lightweight test env fallback.
    ReadabilityDocument = None

try:
    import ftfy
except ImportError:  # pragma: no cover - local lightweight test env fallback.
    ftfy = None


SCRIPT_STYLE_RE = re.compile(r"(?is)<(script|style|noscript).*?>.*?</\1>")
WHITESPACE_RE = re.compile(r"[ \t\r\f\v]+")
MULTI_NEWLINE_RE = re.compile(r"\n{3,}")
CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def _strip_control_chars(value: str) -> str:
    return CONTROL_CHAR_RE.sub("", value)


def clean_html(html: str) -> str:
    html = _strip_control_chars(html)
    html = SCRIPT_STYLE_RE.sub("", html)
    try:
        readable = ReadabilityDocument(html).summary(html_partial=True) if ReadabilityDocument else html
    except Exception:
        readable = html
    soup = BeautifulSoup(readable, "lxml")
    for node in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
        node.decompose()
    return str(soup)


def html_to_text(html: str) -> str:
    html = _strip_control_chars(html)
    soup = BeautifulSoup(html, "lxml")
    for br in soup.find_all("br"):
        br.replace_with("\n")
    for block in soup.find_all(["p", "div", "section", "article", "li", "h1", "h2", "h3"]):
        block.append("\n")
    text = soup.get_text("\n")
    text = ftfy.fix_text(text) if ftfy else text
    text = WHITESPACE_RE.sub(" ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = MULTI_NEWLINE_RE.sub("\n\n", text)
    return text.strip()


def compact_text(text: str) -> str:
    text = ftfy.fix_text(text) if ftfy else text
    text = WHITESPACE_RE.sub(" ", text)
    text = MULTI_NEWLINE_RE.sub("\n\n", text)
    return text.strip()
