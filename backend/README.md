# 🔵 Backend Module (`backend/`)

The **backend** contains the pure Python business logic for the Dual-View Agentic RAG system — independent of web frameworks or HTTP servers.

---

## 📁 Directory Structure

- [`agents/`](./agents/) — LangGraph multi-agent RAG workflow (Supervisor, Retriever, Responder, MallRAGState).
- [`api/`](./api/) — Internal router endpoints (`user`, `admin`, `ingest`).
- [`cache/`](./cache/) — Async Redis client & helper functions (`cache_set`, `cache_get`, `cache_delete_pattern`).
- [`db/`](./db/) — SQLAlchemy 2.0 async ORM session & database models (`Store`, `Product`, `IngestJob`, `AuditFlag`).
- [`ingest/`](./ingest/) — Multi-format document & store ingestion pipeline.
  - [`agents/`](./ingest/agents/) — Scraper, Validator, Indexer, and DocumentIngester agents.
  - [`extractors/`](./ingest/extractors/) — Docling, Playwright, and Hierarchical Chunker.
  - [`readers/`](./ingest/readers/) — LiteLLM multi-provider LLM document reader/enricher.
  - [`cli.py`](./ingest/cli.py) — Typer CLI tool (`mall-ingest`).
- [`mcp/`](./mcp/) — Model Context Protocol (MCP) server implementation.
- [`schemas/`](./schemas/) — Pydantic AI validation models and AuditFlag generation rules.
- [`vector/`](./vector/) — **ChromaDB** client wrapper (`chroma_client.py`) supporting embedded local mode (`./chroma_data`) and HTTP server mode.
- [`config.py`](./config.py) — Centralized settings loaded via Pydantic-Settings v2 from `.env`.
- [`main.py`](./main.py) — FastAPI backend application initialization and lifespan management.

---

## ⚡ Key Responsibilities

1. **Agentic RAG Pipeline**: LangGraph state graph routing user queries through `Supervisor` → `Retriever` (ChromaDB hybrid search) → `Responder` (LLM streaming response).
2. **Vector DB (ChromaDB)**: Manages two distinct collections:
   - `mall_products`: Store product catalog vectors & metadata.
   - `mall_documents`: Parsed PDF/DOCX/HTML document chunk vectors & summaries.
3. **Data Governance & Validation**: Pydantic AI validation rules checking product price caps, category schemas, and flag creation for non-compliant store data.

---

## 🔗 Related Resources
- Read backend guidelines in [`../guidelines/02_backend_guide.md`](../guidelines/02_backend_guide.md)
- Read vector DB specification in [`../docs/hybrid_rag_specification.md`](../docs/hybrid_rag_specification.md)
