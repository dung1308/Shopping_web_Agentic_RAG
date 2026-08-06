"""
app/ingest/readers/base_reader.py — Abstract base for document readers.

Defines the ReadTask enum and ReadResult dataclass that all reader
implementations must produce. This keeps the document ingester decoupled
from any specific LLM provider.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from backend.ingest.extractors.chunker import Chunk


class ReadTask(str, Enum):
    """
    What the LLM reader should do with the document chunks.

    SUMMARIZE          — Produce a single paragraph summary of the full document.
    EXTRACT_STRUCTURED — Extract structured JSON fields (product name, price, etc.).
    ENRICH             — Add missing metadata fields to each chunk individually.
    QA                 — Answer a specific question over the document context.
    """
    SUMMARIZE = "summarize"
    EXTRACT_STRUCTURED = "extract_structured"
    ENRICH = "enrich"
    QA = "qa"


@dataclass
class ReadResult:
    """Output of a document reading operation."""
    task: ReadTask
    provider: str                              # e.g. "openai", "anthropic", "gemini", "local"
    model: str                                 # Full model string used
    summary: str | None = None                 # For SUMMARIZE / QA tasks
    extracted_data: dict[str, Any] | None = None  # For EXTRACT_STRUCTURED
    enriched_chunks: list[Chunk] | None = None # For ENRICH (chunks with metadata added)
    input_tokens: int = 0
    output_tokens: int = 0
    error: str | None = None                   # Non-None if the read failed gracefully


class BaseDocumentReader(ABC):
    """
    Abstract base class for all LLM document readers.

    Subclasses must implement `read()`.
    """

    @abstractmethod
    async def read(
        self,
        chunks: list[Chunk],
        task: ReadTask,
        question: str | None = None,           # Required for QA task
        schema: dict[str, Any] | None = None,  # JSON schema hint for EXTRACT_STRUCTURED
    ) -> ReadResult:
        """
        Process a list of document chunks and return a ReadResult.

        Args:
            chunks:   Document chunks from HierarchicalChunker / SemanticChunker
            task:     What the reader should do (summarize / extract / enrich / QA)
            question: Required for QA task — the question to answer
            schema:   Optional JSON schema for structured extraction guidance

        Returns:
            ReadResult with populated fields depending on task
        """
        ...

    @staticmethod
    def _build_context(chunks: list[Chunk], max_chars: int = 30_000) -> str:
        """
        Concatenate chunk texts into a single context string for the LLM.
        Respects max_chars to avoid token limit overruns.
        """
        parts: list[str] = []
        total = 0
        for chunk in chunks:
            section = f"[{chunk.heading or 'Section'}]\n{chunk.text}" if chunk.heading else chunk.text
            if total + len(section) > max_chars:
                remaining = max_chars - total
                if remaining > 200:
                    parts.append(section[:remaining] + "\n... [truncated]")
                break
            parts.append(section)
            total += len(section)
        return "\n\n---\n\n".join(parts)

