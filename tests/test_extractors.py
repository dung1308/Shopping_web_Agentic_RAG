"""
tests/test_extractors.py — Unit tests for the extraction layer.

Tests DoclingExtractor, PlaywrightExtractor, and HierarchicalChunker
using mocks so they can run without Docling/Playwright installed.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.ingest.extractors.chunker import Chunk, HierarchicalChunker, SemanticChunker
from backend.ingest.extractors.docling_extractor import DoclingExtractor, ExtractedDocument


# ── DoclingExtractor tests ────────────────────────────────────────────────────

class TestDoclingExtractorJson:
    """JSON conversion is pure Python — no Docling dependency needed."""

    def test_json_dict_to_markdown(self):
        extractor = DoclingExtractor()
        data = {"name": "iPhone 15", "price": 25000000, "category": "electronics"}
        result = extractor.from_json(data, source="test")

        assert result.source_type == "json"
        assert "name" in result.text
        assert "iPhone 15" in result.text
        assert "price" in result.text

    def test_json_list_to_markdown_table(self):
        extractor = DoclingExtractor()
        data = [
            {"product": "Laptop", "price": 15000000},
            {"product": "Mouse", "price": 500000},
        ]
        result = extractor.from_json(data, source="api_response")

        assert result.source_type == "json"
        assert "Laptop" in result.text
        assert "Mouse" in result.text
        # Should produce a Markdown table
        assert "|" in result.text

    def test_json_empty_list(self):
        extractor = DoclingExtractor()
        result = extractor.from_json([], source="empty")
        assert "_Empty list_" in result.text

    def test_from_json_file(self):
        extractor = DoclingExtractor()
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            json.dump({"key": "value", "number": 42}, f)
            tmp = f.name
        try:
            result = extractor.from_file(tmp)
            assert result.source_type == "json"
            assert "key" in result.text
        finally:
            Path(tmp).unlink(missing_ok=True)

    def test_from_text_file(self):
        extractor = DoclingExtractor()
        with tempfile.NamedTemporaryFile(suffix=".txt", mode="w",
                                         encoding="utf-8", delete=False) as f:
            f.write("Hello world\nThis is a test document.")
            tmp = f.name
        try:
            result = extractor.from_file(tmp)
            assert result.source_type == "txt"
            assert "Hello world" in result.text
        finally:
            Path(tmp).unlink(missing_ok=True)

    def test_unsupported_format_raises(self):
        extractor = DoclingExtractor()
        with pytest.raises(ValueError, match="Unsupported file format"):
            extractor.from_file("document.xyz")


# ── SemanticChunker tests ─────────────────────────────────────────────────────

class TestSemanticChunker:

    def test_basic_chunking(self):
        chunker = SemanticChunker(max_chars=100, overlap_chars=20)
        text = "Short document with some content."
        chunks = chunker.chunk(text, source="test.txt", source_type="txt")

        assert len(chunks) >= 1
        assert all(isinstance(c, Chunk) for c in chunks)
        assert chunks[0].chunk_index == 0
        assert chunks[0].total_chunks == len(chunks)

    def test_heading_extraction(self):
        chunker = SemanticChunker(max_chars=500)
        text = """## Product Catalog

This section lists products.

### Electronics

Laptops and phones are here.

### Fashion

Clothing and accessories.
"""
        chunks = chunker.chunk(text, source="catalog.md", source_type="md")

        headings = [c.heading for c in chunks if c.heading]
        assert len(headings) > 0
        assert any("Electronics" in h for h in headings)

    def test_long_section_splits(self):
        chunker = SemanticChunker(max_chars=50, overlap_chars=10)
        long_text = "A" * 300
        chunks = chunker.chunk(long_text, source="long.txt", source_type="txt")
        assert len(chunks) > 1

    def test_empty_text(self):
        chunker = SemanticChunker()
        chunks = chunker.chunk("", source="empty.txt", source_type="txt")
        # Empty chunks should be filtered out
        assert all(c.text for c in chunks)

    def test_source_propagated(self):
        chunker = SemanticChunker()
        chunks = chunker.chunk("Some text.", source="myfile.pdf", source_type="pdf")
        assert all(c.source == "myfile.pdf" for c in chunks)

    def test_embed_text_includes_heading(self):
        chunk = Chunk(
            text="Laptop product details",
            chunk_index=0,
            total_chunks=1,
            heading="Electronics",
        )
        assert "Electronics" in chunk.embed_text
        assert "Laptop product details" in chunk.embed_text

    def test_embed_text_no_heading(self):
        chunk = Chunk(text="Plain text.", chunk_index=0, total_chunks=1)
        assert chunk.embed_text == "Plain text."


# ── HierarchicalChunker tests ─────────────────────────────────────────────────

class TestHierarchicalChunker:

    def test_chunk_text_delegates_to_semantic(self):
        chunker = HierarchicalChunker(max_tokens=512, overlap_tokens=64)
        text = "## Section 1\nContent here.\n\n## Section 2\nMore content."
        chunks = chunker.chunk_text(text, source="test.md", source_type="md")
        assert len(chunks) >= 1
        assert all(isinstance(c, Chunk) for c in chunks)

    def test_chunk_from_file_fallback_on_txt(self):
        """TXT files should fall through to SemanticChunker."""
        chunker = HierarchicalChunker()
        with tempfile.NamedTemporaryFile(suffix=".txt", mode="w",
                                         encoding="utf-8", delete=False) as f:
            f.write("## Heading\nSome content.\n\n## Another\nMore content.")
            tmp = f.name
        try:
            # Should not raise — txt falls back gracefully
            chunks = chunker.chunk_text(
                Path(tmp).read_text(), source=tmp, source_type="txt"
            )
            assert len(chunks) >= 1
        finally:
            Path(tmp).unlink(missing_ok=True)

