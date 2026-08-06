"""
app/ingest/extractors/chunker.py — Hierarchical document chunker for RAG.

Two strategies:
  1. HierarchicalChunker — uses Docling's native DOC_CHUNKS for structure-aware splitting.
     Best for PDFs, DOCX — preserves headings, tables, paragraphs as atomic units.

  2. SemanticChunker — character-based fallback with heading-boundary awareness.
     Used for plain text, JSON-converted Markdown, HTML extracts.

Each Chunk carries rich metadata for Qdrant payload (heading, page, chunk_index, etc.).
"""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from backend.config import get_settings

settings = get_settings()
logger = logging.getLogger("mall_rag.chunker")

# ── Chunk dataclass ──────────────────────────────────────────────────────────

@dataclass
class Chunk:
    """A single text chunk ready for embedding and Qdrant indexing."""
    text: str
    chunk_index: int
    total_chunks: int
    heading: str = ""
    page_number: int = 0
    source: str = ""
    source_type: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def embed_text(self) -> str:
        """Text to embed — prepends heading context for better semantic matching."""
        if self.heading:
            return f"{self.heading}\n\n{self.text}"
        return self.text


# ── HierarchicalChunker ──────────────────────────────────────────────────────

class HierarchicalChunker:
    """
    Uses Docling's native chunking (HybridChunker) when available.
    Falls back to SemanticChunker for plain-text/JSON documents.

    Usage:
        chunker = HierarchicalChunker()
        chunks = chunker.chunk(extracted_doc)
    """

    def __init__(
        self,
        max_tokens: int | None = None,
        overlap_tokens: int | None = None,
    ) -> None:
        self.max_tokens = max_tokens or settings.ingest_chunk_size
        self.overlap_tokens = overlap_tokens or settings.ingest_chunk_overlap

    def chunk_from_file(self, file_path: str | Path) -> list[Chunk]:
        """
        Best-path: use Docling's HybridChunker directly on the source file.
        This preserves headings, table structure, and reading order natively.
        """
        try:
            from docling.document_converter import DocumentConverter
            from docling_core.transforms.chunker.hybrid_chunker import HybridChunker
            from docling_core.transforms.chunker.tokenizer.openai_tokenizer import (
                OpenAITokenizer,
            )

            converter = DocumentConverter()
            result = converter.convert(str(file_path))
            doc = result.document

            tokenizer = OpenAITokenizer(model_name="gpt-4o")
            chunker = HybridChunker(
                tokenizer=tokenizer,
                max_tokens=self.max_tokens,
                merge_peers=True,
            )
            chunk_iter = chunker.chunk(doc)

            chunks: list[Chunk] = []
            raw = list(chunk_iter)
            for i, dc in enumerate(raw):
                text = chunker.serialize(chunk=dc)
                heading = ""
                page_no = 0
                try:
                    if dc.meta and dc.meta.headings:
                        heading = " > ".join(dc.meta.headings)
                    if dc.meta and dc.meta.doc_items:
                        for item in dc.meta.doc_items:
                            if item.prov:
                                page_no = item.prov[0].page_no
                                break
                except Exception:
                    pass

                chunks.append(Chunk(
                    text=text,
                    chunk_index=i,
                    total_chunks=len(raw),
                    heading=heading,
                    page_number=page_no,
                    source=str(file_path),
                    source_type=Path(file_path).suffix.lstrip("."),
                ))

            logger.info(f"HybridChunker produced {len(chunks)} chunks from {file_path}")
            return chunks

        except ImportError:
            logger.warning("docling_core.HybridChunker not available, falling back to SemanticChunker")
            from backend.ingest.extractors.docling_extractor import DoclingExtractor
            doc = DoclingExtractor().from_file(file_path)
            return SemanticChunker(
                max_chars=self.max_tokens * 4,  # approx 4 chars per token
                overlap_chars=self.overlap_tokens * 4,
            ).chunk(doc.text, source=str(file_path), source_type=doc.source_type)

        except Exception as exc:
            logger.error(f"HierarchicalChunker.chunk_from_file failed: {exc}")
            raise

    def chunk_text(
        self,
        text: str,
        source: str = "",
        source_type: str = "txt",
    ) -> list[Chunk]:
        """Chunk plain Markdown/text using SemanticChunker."""
        return SemanticChunker(
            max_chars=self.max_tokens * 4,
            overlap_chars=self.overlap_tokens * 4,
        ).chunk(text, source=source, source_type=source_type)


# ── SemanticChunker ──────────────────────────────────────────────────────────

class SemanticChunker:
    """
    Heading-boundary aware text chunker for plain Markdown / HTML extracts.

    Algorithm:
    1. Split text into sections at Markdown headings (##, ###, ####)
    2. Within each section, split further at max_chars with overlap
    3. Each chunk carries its parent heading as metadata
    """

    # Regex: matches Markdown headings (# H1, ## H2, ### H3, #### H4)
    HEADING_RE = re.compile(r"^(#{1,4})\s+(.+)$", re.MULTILINE)

    def __init__(
        self,
        max_chars: int = 2048,   # ~512 tokens × 4 chars/token
        overlap_chars: int = 256,
    ) -> None:
        self.max_chars = max_chars
        self.overlap_chars = overlap_chars

    def chunk(
        self,
        text: str,
        source: str = "",
        source_type: str = "txt",
    ) -> list[Chunk]:
        """Split text into semantically coherent chunks."""
        sections = self._split_into_sections(text)
        raw_chunks: list[tuple[str, str]] = []  # (heading, text)

        for heading, section_text in sections:
            if len(section_text) <= self.max_chars:
                raw_chunks.append((heading, section_text.strip()))
            else:
                # Sub-split long sections with overlap
                sub = self._sliding_window(section_text)
                for piece in sub:
                    raw_chunks.append((heading, piece.strip()))

        # Remove empty chunks
        raw_chunks = [(h, t) for h, t in raw_chunks if t]
        total = len(raw_chunks)

        return [
            Chunk(
                text=text_,
                chunk_index=i,
                total_chunks=total,
                heading=heading_,
                source=source,
                source_type=source_type,
            )
            for i, (heading_, text_) in enumerate(raw_chunks)
        ]

    def _split_into_sections(self, text: str) -> list[tuple[str, str]]:
        """Split Markdown into (heading, body) sections."""
        matches = list(self.HEADING_RE.finditer(text))
        if not matches:
            return [("", text)]

        sections: list[tuple[str, str]] = []
        for i, match in enumerate(matches):
            heading = match.group(2).strip()
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            body = text[start:end]
            sections.append((heading, body))

        # Prepend any text before the first heading
        preamble = text[:matches[0].start()].strip()
        if preamble:
            sections.insert(0, ("", preamble))

        return sections

    def _sliding_window(self, text: str) -> list[str]:
        """Split a long block into overlapping windows."""
        chunks: list[str] = []
        start = 0
        while start < len(text):
            end = start + self.max_chars
            chunk = text[start:end]
            chunks.append(chunk)
            if end >= len(text):
                break
            start = end - self.overlap_chars
        return chunks

