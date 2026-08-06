# 📦 05 — Extraction Pipeline Guide

> How the system reads any document type — PDF, DOCX, HTML, images, JSON — and prepares it for RAG.

---

## The Pipeline in 4 Steps

```
1. CAPTURE   — Get the raw content (Playwright or local file)
2. EXTRACT   — Convert to clean Markdown (Docling)
3. CHUNK     — Split into RAG-sized pieces (HybridChunker)
4. READ      — Optional LLM enrichment (LiteLLMReader)
```

---

## Step 1: Capture

### From a URL (JavaScript-heavy page)
```python
from backend.ingest.extractors.playwright_extractor import PlaywrightExtractor

extractor = PlaywrightExtractor()
capture = await extractor.capture(
    "https://shop.example.com/products",
    intercept_xhr=True,       # Capture JSON API calls the page makes
    capture_screenshot=False,
)

print(capture.html)           # Full rendered HTML after JS executed
print(capture.xhr_payloads)   # List of JSON responses from XHR/fetch calls
```

**What `intercept_xhr=True` does:**
When a JS page loads, it often calls its own API (e.g., `GET /api/products.json`). Playwright intercepts these responses. You get the rendered HTML *and* the underlying JSON data — both are indexed.

### From a local file
```python
from backend.ingest.extractors.docling_extractor import DoclingExtractor

extractor = DoclingExtractor()

# PDF
doc = extractor.from_file("catalog.pdf")

# DOCX
doc = extractor.from_file("brochure.docx")

# Image (OCR)
doc = extractor.from_file("receipt.png")

# JSON
doc = extractor.from_json({"products": [...]}, source="api_dump")
```

---

## Step 2: Extract (Docling)

Docling converts any format to clean **Markdown**:

| Input | Output |
|-------|--------|
| PDF | Markdown with headings, tables, paragraphs preserved |
| DOCX | Markdown with document structure |
| HTML | Markdown (strips navigation, ads, scripts) |
| Image | Markdown via EasyOCR (CPU-safe) |
| JSON | Markdown table or key-value list |
| TXT/MD | Pass-through |

**CPU-safe settings (your machine):**
```env
DOCLING_DEVICE=cpu
DOCLING_ENABLE_OCR=true
DOCLING_OCR_ENGINE=easyocr    # No system install needed
```

---

## Step 3: Chunk

Two chunking strategies:

### HybridChunker (primary — for PDF/DOCX)
Uses Docling's own chunker which understands document structure:
- Keeps tables as single chunks (not split mid-row)
- Preserves heading hierarchy as metadata
- Respects reading order

```python
from backend.ingest.extractors.chunker import HierarchicalChunker

chunker = HierarchicalChunker(max_tokens=512, overlap_tokens=64)
chunks = chunker.chunk_from_file("catalog.pdf")

for chunk in chunks:
    print(chunk.heading)      # "Section 2 > Electronics > Phones"
    print(chunk.page_number)  # 7
    print(chunk.text[:100])   # "iPhone 15 Pro — Available at Store B..."
    print(chunk.embed_text)   # heading + text (what gets embedded)
```

### SemanticChunker (fallback — for HTML/TXT/JSON)
Splits on Markdown heading boundaries (`##`, `###`) then applies sliding window:

```python
from backend.ingest.extractors.chunker import SemanticChunker

chunker = SemanticChunker(max_chars=2048, overlap_chars=256)
chunks = chunker.chunk(markdown_text, source="page.html", source_type="html")
```

**Why overlap?**
If chunk A ends mid-sentence and chunk B starts there, the query "price of leather bag" might match chunk B but the name was in chunk A. Overlap ensures context isn't lost at boundaries.

---

## Step 4: Read (LiteLLMReader)

Optional step. The LLM reads the chunks and can:

| Task | What it does | Use when |
|------|-------------|----------|
| `SUMMARIZE` | Writes a 3-5 sentence summary | Long PDFs |
| `EXTRACT_STRUCTURED` | Returns JSON of key fields | Product catalogs |
| `ENRICH` | Adds `category`, `tags`, `language`, `key_entities` | General docs |
| `QA` | Answers a specific question | Targeted extraction |

### Provider selection
```env
LLM_READER_PROVIDER=local      # Ollama Phi-3.5, free, CPU-safe ← default
LLM_READER_PROVIDER=gemini     # Fast, native PDF, needs GEMINI_API_KEY
LLM_READER_PROVIDER=openai     # Best accuracy, needs OPENAI_API_KEY
LLM_READER_PROVIDER=anthropic  # Large docs, prompt caching, needs key
LLM_READER_PROVIDER=none       # Skip LLM reading entirely
```

---

## CLI Commands

```bash
# Ingest a PDF (uses local Ollama by default)
mall-ingest ingest-file --file catalog.pdf --store-id <uuid>

# Ingest with Gemini for structured extraction
mall-ingest ingest-file --file catalog.pdf --store-id <uuid> \
    --provider gemini --task extract_structured

# Capture a JavaScript page
mall-ingest ingest-url --url https://shop.example.com --store-id <uuid>

# Ingest DOCX and enrich metadata with LLM
mall-ingest ingest-file --file manual.docx --store-id <uuid> \
    --provider local --task enrich

# Skip LLM, fastest (embedding-only)
mall-ingest ingest-file --file data.json --store-id <uuid> --provider none

# List available providers
mall-ingest list-providers-cmd
```

---

## What Gets Stored in Qdrant

Each chunk becomes a vector point in `mall_documents` with this payload:

```json
{
  "store_id": "uuid",
  "store_name": "Zara",
  "floor": 2,
  "source": "catalog.pdf",
  "source_type": "pdf",
  "chunk_index": 4,
  "total_chunks": 28,
  "heading": "Winter Collection > Outerwear",
  "page_number": 7,
  "text_preview": "Leather jacket — premium quality...",
  "llm_provider": "gemini",
  "llm_summary": "Section covers leather outerwear...",
  "category": "fashion",
  "tags": ["leather", "jacket", "winter"],
  "extracted_at": "2026-08-05T11:00:00Z"
}
```
