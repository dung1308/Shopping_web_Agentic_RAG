"""
app/ingest/extractors/docling_extractor.py — Docling-powered multi-format extractor.

Supports:
  - PDF  (.pdf)
  - DOCX (.docx, .doc)
  - TXT  (.txt, .md)
  - JSON (.json)         — pretty-printed as Markdown table / code block
  - HTML (string)        — from Playwright capture or raw HTML file
  - Images (.png, .jpg, .jpeg, .webp, .tiff) — via EasyOCR on CPU

CPU-first design: set DOCLING_DEVICE=cpu to avoid VRAM usage.
GPU is used only if DOCLING_DEVICE=cuda and torch/CUDA is available.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger("mall_rag.extractor.docling")

# Supported extensions → Docling can handle them natively
DOCLING_SUPPORTED = {".pdf", ".docx", ".doc", ".pptx", ".xlsx", ".html", ".htm",
                     ".png", ".jpg", ".jpeg", ".webp", ".tiff", ".bmp"}
TEXT_PASSTHROUGH = {".txt", ".md", ".rst"}


@dataclass
class ExtractedDocument:
    """Unified output of any extraction operation."""
    text: str                          # Full Markdown representation
    source: str                        # Original file path or URL
    source_type: str                   # "pdf" | "docx" | "html" | "image" | "txt" | "json"
    page_count: int = 0
    tables: list[dict[str, Any]] = field(default_factory=list)
    images: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class DoclingExtractor:
    """
    Wraps docling.DocumentConverter to extract text from any supported format.

    Usage:
        extractor = DoclingExtractor()
        doc = extractor.from_file("report.pdf")
        doc = extractor.from_html("<html>...</html>", source_url="https://...")
        doc = extractor.from_json({"key": "value"}, source="api_response")
    """

    def __init__(self) -> None:
        self._converter = None  # lazy-loaded to avoid import cost at startup

    def _get_converter(self):
        """Lazy-load Docling DocumentConverter with CPU-safe pipeline options."""
        if self._converter is not None:
            return self._converter

        try:
            from docling.document_converter import DocumentConverter, ConversionStatus
            from docling.datamodel.pipeline_options import (
                PdfPipelineOptions,
                EasyOcrOptions,
            )

            device = os.environ.get("DOCLING_DEVICE", "cpu").lower()
            enable_ocr = os.environ.get("DOCLING_ENABLE_OCR", "true").lower() == "true"

            # Build PDF pipeline options (CPU-safe)
            pdf_opts = PdfPipelineOptions()
            pdf_opts.do_ocr = enable_ocr

            if enable_ocr:
                ocr_engine = os.environ.get("DOCLING_OCR_ENGINE", "easyocr").lower()
                if ocr_engine == "easyocr":
                    pdf_opts.ocr_options = EasyOcrOptions(use_gpu=(device == "cuda"))
                # Note: tesseract option available but requires system install

            self._converter = DocumentConverter()
            logger.info(f"Docling DocumentConverter ready (device={device}, ocr={enable_ocr})")
        except ImportError as exc:
            raise RuntimeError(
                "Docling is not installed. Run: pip install docling docling-core"
            ) from exc

        return self._converter

    # ── Public API ──────────────────────────────────────────────────────────

    def from_file(self, file_path: str | Path) -> ExtractedDocument:
        """Extract content from a local file. Auto-detects format by extension."""
        path = Path(file_path)
        suffix = path.suffix.lower()

        logger.info(f"Extracting from file: {path.name} (type={suffix})")

        # Plain text / Markdown — pass through directly
        if suffix in TEXT_PASSTHROUGH:
            return self._from_text_file(path)

        # JSON — convert to readable Markdown representation
        if suffix == ".json":
            return self._from_json_file(path)

        # Everything else — use Docling
        if suffix in DOCLING_SUPPORTED:
            return self._run_docling(str(path), source_type=suffix.lstrip("."))

        raise ValueError(f"Unsupported file format: {suffix}. Supported: "
                         f"{DOCLING_SUPPORTED | TEXT_PASSTHROUGH}")

    def from_html(self, html_content: str, source_url: str = "unknown") -> ExtractedDocument:
        """
        Extract from a raw HTML string (e.g., output of Playwright capture).
        Writes to a temp file and feeds into Docling's HTML pipeline.
        """
        logger.info(f"Extracting from HTML string ({len(html_content)} chars, src={source_url})")

        with tempfile.NamedTemporaryFile(suffix=".html", mode="w",
                                         encoding="utf-8", delete=False) as f:
            f.write(html_content)
            tmp_path = f.name

        try:
            doc = self._run_docling(tmp_path, source_type="html")
            doc.source = source_url
            return doc
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def from_json(self, data: dict | list, source: str = "json_input") -> ExtractedDocument:
        """
        Convert a JSON object/array into an ExtractedDocument with Markdown text.
        Useful for XHR API responses captured by Playwright.
        """
        logger.info(f"Extracting from JSON object (src={source})")
        text = self._json_to_markdown(data)
        return ExtractedDocument(
            text=text,
            source=source,
            source_type="json",
            metadata={"original_keys": list(data.keys()) if isinstance(data, dict) else []},
        )

    def from_bytes(self, content: bytes, filename: str) -> ExtractedDocument:
        """Extract from raw bytes (e.g., downloaded PDF from URL)."""
        suffix = Path(filename).suffix.lower()
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
            f.write(content)
            tmp_path = f.name

        try:
            return self.from_file(tmp_path)
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    # ── Internal helpers ─────────────────────────────────────────────────────

    def _run_docling(self, file_path: str, source_type: str) -> ExtractedDocument:
        """Run Docling DocumentConverter on a file and return ExtractedDocument."""
        converter = self._get_converter()

        try:
            result = converter.convert(file_path)
        except Exception as exc:
            logger.error(f"Docling conversion failed for {file_path}: {exc}")
            raise RuntimeError(f"Docling failed to convert {file_path}: {exc}") from exc

        doc = result.document
        markdown_text = doc.export_to_markdown()

        # Extract tables as list of dicts
        tables: list[dict[str, Any]] = []
        try:
            for tbl in doc.tables:
                tables.append({
                    "caption": tbl.caption_text(doc) if hasattr(tbl, "caption_text") else "",
                    "markdown": tbl.export_to_markdown(),
                })
        except Exception:
            pass  # Tables optional

        # Extract image references
        images: list[dict[str, Any]] = []
        try:
            for fig in doc.pictures:
                images.append({
                    "caption": fig.caption_text(doc) if hasattr(fig, "caption_text") else "",
                    "page": getattr(fig.prov[0], "page_no", 0) if fig.prov else 0,
                })
        except Exception:
            pass  # Images optional

        page_count = 0
        try:
            page_count = len(doc.pages) if doc.pages else 0
        except Exception:
            pass

        return ExtractedDocument(
            text=markdown_text,
            source=file_path,
            source_type=source_type,
            page_count=page_count,
            tables=tables,
            images=images,
            metadata={
                "page_count": page_count,
                "table_count": len(tables),
                "image_count": len(images),
            },
        )

    def _from_text_file(self, path: Path) -> ExtractedDocument:
        """Read plain text / Markdown file directly."""
        text = path.read_text(encoding="utf-8", errors="replace")
        return ExtractedDocument(
            text=text,
            source=str(path),
            source_type=path.suffix.lstrip(".") or "txt",
            metadata={"char_count": len(text)},
        )

    def _from_json_file(self, path: Path) -> ExtractedDocument:
        """Load JSON file and convert to readable Markdown."""
        raw = path.read_text(encoding="utf-8", errors="replace")
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            # Treat as plain text if not valid JSON
            return ExtractedDocument(
                text=raw, source=str(path), source_type="txt",
                metadata={"parse_error": "invalid_json"}
            )
        text = self._json_to_markdown(data)
        return ExtractedDocument(
            text=text, source=str(path), source_type="json",
            metadata={"original_keys": list(data.keys()) if isinstance(data, dict) else []},
        )

    @staticmethod
    def _json_to_markdown(data: dict | list) -> str:
        """Convert JSON to a readable Markdown representation for LLM consumption."""
        if isinstance(data, list):
            if not data:
                return "_Empty list_"
            if isinstance(data[0], dict):
                # Build a Markdown table from list of dicts
                headers = list(data[0].keys())
                rows = [headers] + [[str(item.get(h, "")) for h in headers] for item in data]
                col_widths = [max(len(str(r[i])) for r in rows) for i in range(len(headers))]
                lines = []
                for i, row in enumerate(rows):
                    line = "| " + " | ".join(str(cell).ljust(col_widths[j])
                                              for j, cell in enumerate(row)) + " |"
                    lines.append(line)
                    if i == 0:
                        lines.append("| " + " | ".join("-" * w for w in col_widths) + " |")
                return "\n".join(lines)
            return "\n".join(f"- {item}" for item in data)

        # Dict → key-value list
        lines = ["| Key | Value |", "| --- | ----- |"]
        for k, v in data.items():
            v_str = json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else str(v)
            lines.append(f"| {k} | {v_str} |")
        return "\n".join(lines)
