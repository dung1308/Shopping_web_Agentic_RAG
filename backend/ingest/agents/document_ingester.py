"""
app/ingest/agents/document_ingester.py — Full pipeline orchestrator.

Accepts any input source and runs:
  source → detect_format → extract → chunk → [llm_read/enrich] → embed → upsert_qdrant

Supports:
  - Local file (PDF, DOCX, TXT, JSON, image)
  - Remote URL (HTML/JS page via Playwright, or direct PDF/image URL)
  - Raw HTML string (from external Playwright capture)
  - Raw bytes (from HTTP download)
"""

from __future__ import annotations

import asyncio
import logging
import mimetypes
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from backend.config import get_settings
from backend.ingest.extractors.chunker import Chunk, HierarchicalChunker
from backend.ingest.extractors.docling_extractor import DoclingExtractor
from backend.ingest.extractors.playwright_extractor import PlaywrightExtractor
from backend.ingest.readers.base_reader import ReadTask, ReadResult
from backend.ingest.readers.litellm_reader import LiteLLMReader

settings = get_settings()
logger = logging.getLogger("mall_rag.document_ingester")

# ChromaDB collection for documents (separate from mall_products)
DOCUMENTS_COLLECTION = "mall_documents"


@dataclass
class IngestResult:
    """Summary of a completed ingestion job."""
    source: str
    source_type: str
    chunks_indexed: int
    llm_provider: str | None
    llm_task: str | None
    read_result: ReadResult | None = None
    errors: list[str] = None  # type: ignore[assignment]

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class DocumentIngester:
    """
    Full ingest pipeline: detect → extract → chunk → read (optional) → embed → index.

    Usage:
        ingester = DocumentIngester(store_id="uuid", store_name="Brand Store", floor=2)

        # From local file
        result = await ingester.ingest_file("catalog.pdf")

        # From URL (auto-detects HTML vs direct PDF link)
        result = await ingester.ingest_url("https://shop.example.com/products")

        # With LLM enrichment
        result = await ingester.ingest_file(
            "brochure.pdf", provider="gemini", task=ReadTask.EXTRACT_STRUCTURED
        )
    """

    def __init__(
        self,
        store_id: str,
        store_name: str = "Mall Store",
        floor: int = 1,
    ) -> None:
        self.store_id = store_id
        self.store_name = store_name
        self.floor = floor
        self._docling = DoclingExtractor()
        self._playwright = PlaywrightExtractor()
        self._chunker = HierarchicalChunker()

    # ── Public entry points ──────────────────────────────────────────────────

    async def ingest_file(
        self,
        file_path: str | Path,
        provider: str | None = None,
        task: ReadTask | str = ReadTask.EXTRACT_STRUCTURED,
    ) -> IngestResult:
        """Ingest a local file through the full pipeline."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        max_mb = settings.ingest_max_file_mb
        size_mb = path.stat().st_size / (1024 * 1024)
        if size_mb > max_mb:
            raise ValueError(f"File too large: {size_mb:.1f} MB (limit: {max_mb} MB)")

        logger.info(f"Ingesting file: {path.name} ({size_mb:.1f} MB)")

        # Extract
        extracted = self._docling.from_file(path)

        # Chunk — prefer HybridChunker for Docling-supported formats
        suffix = path.suffix.lower()
        if suffix in {".pdf", ".docx", ".doc", ".pptx"}:
            try:
                chunks = self._chunker.chunk_from_file(path)
            except Exception as exc:
                logger.warning(f"HybridChunker failed ({exc}), using SemanticChunker")
                chunks = self._chunker.chunk_text(
                    extracted.text, source=str(path), source_type=extracted.source_type
                )
        else:
            chunks = self._chunker.chunk_text(
                extracted.text, source=str(path), source_type=extracted.source_type
            )

        return await self._run_pipeline(
            chunks=chunks,
            source=str(path),
            source_type=extracted.source_type,
            provider=provider,
            task=task,
        )

    async def ingest_url(
        self,
        url: str,
        mode: str = "auto",              # "auto" | "html" | "pdf" | "image"
        provider: str | None = None,
        task: ReadTask | str = ReadTask.EXTRACT_STRUCTURED,
        capture_screenshot: bool = False,
    ) -> IngestResult:
        """
        Ingest content from a URL.

        Modes:
          auto — detect from Content-Type header
          html — always use Playwright rendering
          pdf  — download and treat as PDF
          image — download and OCR
        """
        logger.info(f"Ingesting URL: {url} (mode={mode})")

        resolved_mode = await self._detect_url_mode(url, mode)

        if resolved_mode == "html":
            return await self._ingest_html_url(url, provider, task, capture_screenshot)
        else:
            # Download file and ingest
            content, filename = await self._download_file(url)
            with __import__("tempfile").NamedTemporaryFile(
                suffix=Path(filename).suffix, delete=False
            ) as f:
                f.write(content)
                tmp_path = f.name
            try:
                result = await self.ingest_file(tmp_path, provider=provider, task=task)
                result.source = url
                return result
            finally:
                Path(tmp_path).unlink(missing_ok=True)

    async def ingest_html_string(
        self,
        html: str,
        source_url: str = "unknown",
        xhr_payloads: list[dict[str, Any]] | None = None,
        provider: str | None = None,
        task: ReadTask | str = ReadTask.EXTRACT_STRUCTURED,
    ) -> IngestResult:
        """Ingest from a raw HTML string (e.g., pre-captured Playwright output)."""
        logger.info(f"Ingesting raw HTML ({len(html) // 1024} KB, src={source_url})")

        all_chunks: list[Chunk] = []

        # Extract HTML → Docling → chunks
        extracted = self._docling.from_html(html, source_url=source_url)
        chunks = self._chunker.chunk_text(
            extracted.text, source=source_url, source_type="html"
        )
        all_chunks.extend(chunks)

        # Process intercepted XHR payloads as additional JSON docs
        if xhr_payloads:
            for i, payload in enumerate(xhr_payloads):
                xhr_doc = self._docling.from_json(
                    payload.get("data", payload),
                    source=payload.get("url", f"{source_url}#xhr-{i}"),
                )
                xhr_chunks = self._chunker.chunk_text(
                    xhr_doc.text,
                    source=xhr_doc.source,
                    source_type="json",
                )
                all_chunks.extend(xhr_chunks)

        return await self._run_pipeline(
            chunks=all_chunks,
            source=source_url,
            source_type="html",
            provider=provider,
            task=task,
        )

    # ── Internal pipeline ────────────────────────────────────────────────────

    async def _run_pipeline(
        self,
        chunks: list[Chunk],
        source: str,
        source_type: str,
        provider: str | None,
        task: ReadTask | str,
    ) -> IngestResult:
        """
        Core pipeline: [llm_read] → embed → upsert.
        LLM reading is skipped if provider is None or 'none'.
        """
        read_result: ReadResult | None = None
        actual_provider = provider or settings.llm_reader_provider

        if actual_provider and actual_provider.lower() not in ("none", "off", "skip"):
            read_task = ReadTask(task) if isinstance(task, str) else task
            logger.info(f"LLM reading with provider={actual_provider}, task={read_task.value}")
            reader = LiteLLMReader(provider=actual_provider)
            read_result = await reader.read(chunks, task=read_task)

            # Merge enriched chunks back if task was ENRICH
            if read_result.enriched_chunks:
                chunks = read_result.enriched_chunks

            # Append LLM summary as an extra metadata field on all chunks
            if read_result.summary:
                for chunk in chunks:
                    chunk.metadata["llm_summary"] = read_result.summary[:500]

        # Embed all chunks
        texts = [c.embed_text for c in chunks]
        embeddings = await self._get_embeddings(texts)

        # Upsert to Qdrant
        indexed = await self._upsert_to_qdrant(
            chunks=chunks,
            embeddings=embeddings,
            source=source,
            source_type=source_type,
            read_result=read_result,
        )

        logger.info(f"Ingestion complete: {source} → {indexed} chunks indexed in Qdrant")

        return IngestResult(
            source=source,
            source_type=source_type,
            chunks_indexed=indexed,
            llm_provider=actual_provider if read_result else None,
            llm_task=task if isinstance(task, str) else task.value,
            read_result=read_result,
        )

    async def _ingest_html_url(
        self, url: str, provider, task, capture_screenshot: bool
    ) -> IngestResult:
        """Capture JS-rendered HTML via Playwright, then ingest."""
        capture = await self._playwright.capture(
            url,
            capture_screenshot=capture_screenshot,
            intercept_xhr=True,
        )
        return await self.ingest_html_string(
            html=capture.html,
            source_url=url,
            xhr_payloads=capture.xhr_payloads,
            provider=provider,
            task=task,
        )

    # ── Embedding ────────────────────────────────────────────────────────────

    async def _get_embeddings(self, texts: list[str]) -> list[list[float]]:
        """Call local bge-m3 embedding service with fallback."""
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    f"{settings.embed_base_url}/embeddings",
                    json={"input": texts, "model": settings.embed_model},
                )
                resp.raise_for_status()
                data = resp.json()
                return [item["embedding"] for item in data["data"]]
        except Exception as exc:
            logger.warning(f"Embedding service offline: {exc}. Using mock vectors.")
            return [[0.01 * (i % 10) for i in range(settings.embed_dim)] for _ in texts]

    # ── ChromaDB upsert ───────────────────────────────────────────────────────

    async def _upsert_to_qdrant(
        self,
        chunks: list[Chunk],
        embeddings: list[list[float]],
        source: str,
        source_type: str,
        read_result: ReadResult | None,
    ) -> int:
        """Upsert all chunk vectors into the mall_documents ChromaDB collection."""
        from backend.vector.chroma_client import upsert_vectors

        now_iso = datetime.now(timezone.utc).isoformat()
        llm_provider = read_result.provider if read_result else None
        llm_summary = read_result.summary if read_result else None

        points: list[dict[str, Any]] = []
        for chunk, vector in zip(chunks, embeddings):
            point_id = str(uuid.uuid5(
                uuid.NAMESPACE_DNS,
                f"{self.store_id}-{source}-{chunk.chunk_index}"
            ))
            payload: dict[str, Any] = {
                "store_id": self.store_id,
                "store_name": self.store_name,
                "floor": self.floor,
                "source": source,
                "source_type": source_type,
                "chunk_index": chunk.chunk_index,
                "total_chunks": chunk.total_chunks,
                "heading": chunk.heading,
                "page_number": chunk.page_number,
                "text_preview": chunk.text[:200],
                "llm_provider": llm_provider,
                "llm_summary": llm_summary,
                "extracted_at": now_iso,
                **chunk.metadata,  # merge any LLM enrichment (tags, category, etc.)
            }
            points.append({"id": point_id, "vector": vector, "payload": payload})

        try:
            await upsert_vectors(points, collection_name=DOCUMENTS_COLLECTION)
        except Exception as exc:
            logger.error(f"ChromaDB upsert failed: {exc}")
            raise

        return len(points)

    # ── Helpers ──────────────────────────────────────────────────────────────

    async def _detect_url_mode(self, url: str, mode: str) -> str:
        """Auto-detect whether a URL should be handled as HTML or file download."""
        if mode != "auto":
            return mode
        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                resp = await client.head(url)
                ct = resp.headers.get("content-type", "")
                if "pdf" in ct:
                    return "pdf"
                if "image/" in ct:
                    return "image"
                return "html"
        except Exception:
            return "html"

    async def _download_file(self, url: str) -> tuple[bytes, str]:
        """Download a file from URL. Returns (bytes, filename)."""
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()

        # Try to guess filename from URL or Content-Disposition
        cd = resp.headers.get("content-disposition", "")
        if "filename=" in cd:
            filename = cd.split("filename=")[-1].strip('"\'')
        else:
            filename = Path(url.split("?")[0]).name or "download"

        ct = resp.headers.get("content-type", "")
        ext = mimetypes.guess_extension(ct.split(";")[0]) or ""
        if ext and not filename.endswith(ext):
            filename += ext

        return resp.content, filename

