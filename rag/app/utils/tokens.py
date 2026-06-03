import re

import tiktoken

ENCODING = tiktoken.get_encoding("cl100k_base")
WHITESPACE_RE = re.compile(r"\s+")


def count_tokens(text: str) -> int:
    return len(ENCODING.encode(text or ""))


def trim_to_tokens(text: str, max_tokens: int) -> str:
    ids = ENCODING.encode(text or "")
    if len(ids) <= max_tokens:
        return text
    return ENCODING.decode(ids[:max_tokens]).strip()


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [WHITESPACE_RE.sub(" ", line).strip() for line in text.split("\n")]
    compacted: list[str] = []
    blank = False
    for line in lines:
        if not line:
            if not blank:
                compacted.append("")
            blank = True
        else:
            compacted.append(line)
            blank = False
    return "\n".join(compacted).strip()
