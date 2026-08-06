"""
app/ingest/extractors/__init__.py — Multi-format document extraction package.

Provides a unified interface for extracting text, tables, and metadata from:
  - PDF, DOCX, TXT, Markdown, JSON  (via Docling)
  - JS-rendered HTML pages           (via Playwright → Docling)
  - Images (PNG, JPG, WEBP)          (via Docling + EasyOCR)
"""

from app.ingest.extractors.docling_extractor import DoclingExtractor, ExtractedDocument
from app.ingest.extractors.playwright_extractor import PlaywrightExtractor, PlaywrightCapture
from app.ingest.extractors.chunker import HierarchicalChunker, Chunk

__all__ = [
    "DoclingExtractor",
    "ExtractedDocument",
    "PlaywrightExtractor",
    "PlaywrightCapture",
    "HierarchicalChunker",
    "Chunk",
]
