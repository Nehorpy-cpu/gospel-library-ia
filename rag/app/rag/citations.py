from app.retrieval.types import RetrievedChunk
from app.schemas.search import Citation


class CitationBuilder:
    def build(self, chunks: list[RetrievedChunk]) -> list[Citation]:
        citations: list[Citation] = []
        for index, chunk in enumerate(chunks, start=1):
            citations.append(
                Citation(
                    citation_id=index,
                    chunk_id=chunk.chunk_id,
                    document_id=chunk.document_id,
                    title=chunk.title,
                    author=chunk.author,
                    source_key=chunk.source_key,
                    canonical_url=chunk.canonical_url,
                    published_at=chunk.published_at,
                    language=chunk.language,
                    section_title=chunk.section_title,
                    quote=chunk.citation_quote(),
                    score=chunk.final_score,
                )
            )
        return citations

    def context_block(self, chunks: list[RetrievedChunk]) -> str:
        blocks: list[str] = []
        for index, chunk in enumerate(chunks, start=1):
            meta = [
                f"Title: {chunk.title}",
                f"Author: {chunk.author or 'Unknown'}",
                f"Source: {chunk.source_key or 'Unknown'}",
                f"Language: {chunk.language or 'unknown'}",
                f"URL: {chunk.canonical_url or ''}",
                f"Section: {chunk.section_title or ''}",
                f"Scripture refs: {', '.join(chunk.metadata.get('scripture_refs') or [])}",
            ]
            blocks.append(f"[{index}]\n" + "\n".join(meta) + f"\nText:\n{chunk.text}")
        return "\n\n---\n\n".join(blocks)
