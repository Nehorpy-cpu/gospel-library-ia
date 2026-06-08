import re
from dataclasses import dataclass

from app.core.config import get_settings
from app.utils.hashing import sha256_text
from app.utils.tokens import count_tokens, normalize_text, trim_to_tokens


HEADING_RE = re.compile(r"^(#{1,6}\s+.+|[A-ZÁÉÍÓÚÑ][^.!?]{2,90})$")
PARAGRAPH_SPLIT_RE = re.compile(r"\n{2,}")
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


@dataclass(frozen=True)
class ChunkCandidate:
    chunk_index: int
    section_title: str | None
    start_char: int
    end_char: int
    token_count: int
    text: str
    text_hash: str


class SmartChunker:
    version = "smart-v1"

    def __init__(self) -> None:
        self.settings = get_settings()

    def chunk(self, text: str) -> list[ChunkCandidate]:
        normalized = normalize_text(text)
        blocks = self._blocks(normalized)
        chunks: list[ChunkCandidate] = []
        current: list[tuple[str, int, int, str | None]] = []
        current_tokens = 0
        current_section: str | None = None

        for block, start, end, section in blocks:
            block_tokens = count_tokens(block)
            if block_tokens > self.settings.effective_chunk_max_tokens:
                if current:
                    chunks.append(self._build_chunk(len(chunks), current))
                    current = []
                    current_tokens = 0
                for piece, p_start, p_end in self._split_large_block(block, start):
                    chunks.append(self._single_chunk(len(chunks), piece, p_start, p_end, current_section))
                continue

            if current and current_tokens + block_tokens > self.settings.effective_chunk_target_tokens:
                chunks.append(self._build_chunk(len(chunks), current))
                current = self._overlap_tail(current)
                current_tokens = sum(count_tokens(item[0]) for item in current)

            if section:
                current_section = section
            current.append((block, start, end, current_section))
            current_tokens += block_tokens

        if current:
            chunks.append(self._build_chunk(len(chunks), current))

        return chunks

    def _blocks(self, text: str) -> list[tuple[str, int, int, str | None]]:
        blocks: list[tuple[str, int, int, str | None]] = []
        cursor = 0
        current_section: str | None = None
        for raw in PARAGRAPH_SPLIT_RE.split(text):
            block = raw.strip()
            if not block:
                cursor += len(raw) + 2
                continue
            start = text.find(block, cursor)
            end = start + len(block)
            if HEADING_RE.match(block) and count_tokens(block) <= 24:
                current_section = block.replace("#", "").strip()
            blocks.append((block, start, end, current_section))
            cursor = end
        return blocks

    def _split_large_block(self, block: str, absolute_start: int) -> list[tuple[str, int, int]]:
        sentences = SENTENCE_SPLIT_RE.split(block)
        pieces: list[tuple[str, int, int]] = []
        current: list[str] = []
        local_cursor = 0
        start = 0
        current_tokens = 0
        for sentence in sentences:
            tokens = count_tokens(sentence)
            if current and current_tokens + tokens > self.settings.effective_chunk_target_tokens:
                text = " ".join(current).strip()
                pieces.append((text, absolute_start + start, absolute_start + start + len(text)))
                start = local_cursor
                current = []
                current_tokens = 0
            current.append(sentence)
            current_tokens += tokens
            local_cursor += len(sentence) + 1
        if current:
            text = " ".join(current).strip()
            pieces.append((text, absolute_start + start, absolute_start + start + len(text)))
        return pieces

    def _overlap_tail(self, current: list[tuple[str, int, int, str | None]]):
        tail: list[tuple[str, int, int, str | None]] = []
        tokens = 0
        for item in reversed(current):
            item_tokens = count_tokens(item[0])
            if tokens + item_tokens > self.settings.effective_chunk_overlap_tokens:
                break
            tail.insert(0, item)
            tokens += item_tokens
        return tail

    def _single_chunk(self, index: int, text: str, start: int, end: int, section: str | None):
        text = trim_to_tokens(text, self.settings.effective_chunk_max_tokens)
        return ChunkCandidate(
            chunk_index=index,
            section_title=section,
            start_char=start,
            end_char=end,
            token_count=count_tokens(text),
            text=text,
            text_hash=sha256_text(text),
        )

    def _build_chunk(self, index: int, items: list[tuple[str, int, int, str | None]]) -> ChunkCandidate:
        text = "\n\n".join(item[0] for item in items).strip()
        text = trim_to_tokens(text, self.settings.effective_chunk_max_tokens)
        return ChunkCandidate(
            chunk_index=index,
            section_title=items[-1][3],
            start_char=items[0][1],
            end_char=items[-1][2],
            token_count=count_tokens(text),
            text=text,
            text_hash=sha256_text(text),
        )
