# 🛒 Shopping Web Agentic RAG — Dual-View AI System

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2.35-orange.svg)](https://python.langchain.com/docs/langgraph/)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-1.5.9-blueviolet.svg)](https://www.trychroma.com/)
[![Neon](https://img.shields.io/badge/Neon-PostgreSQL_Serverless-00e599.svg)](https://neon.tech/)
[![GitHub](https://img.shields.io/badge/GitHub-dung1308%2FShopping__web__Agentic__RAG-black?logo=github)](https://github.com/dung1308/Shopping_web_Agentic_RAG.git)

> An autonomous **Dual-View Agentic RAG (Retrieval-Augmented Generation)** system designed for modern shopping malls. Combines a **conversational AI assistant for shoppers** with a **data governance dashboard for admins** — backed by ChromaDB hybrid vector search, multi-format document ingestion (PDF, DOCX, HTML, Images), and multi-provider LLM reading.

---

## 📖 System Guidelines & Architecture

All primary documentation lives in [`guidelines/`](./guidelines). Click any link below to explore:

| # | Guide | What You'll Learn |
|---|-------|------------------|
| [00](./guidelines/00_overview.md) | [**System Overview**](./guidelines/00_overview.md) | Design philosophy, 3-layer architecture, tech decisions |
| [01](./guidelines/01_architecture.md) | [**Architecture Diagrams**](./guidelines/01_architecture.md) | End-to-end flow, RAG state machine, document ingestion pipeline |
| [02](./guidelines/02_backend_guide.md) | [**Backend Guide**](./guidelines/02_backend_guide.md) | LangGraph agents, ChromaDB vector search, SQLAlchemy async ORM |
| [03](./guidelines/03_frontend_guide.md) | [**Frontend Guide**](./guidelines/03_frontend_guide.md) | Web HTML/JS interface & Desktop Tkinter GUI apps |
| [04](./guidelines/04_bridge_guide.md) | [**API Bridge Guide**](./guidelines/04_bridge_guide.md) | REST routers, WebSocket chat streaming, MCP server integration |
| [05](./guidelines/05_extraction_guide.md) | [**Extraction Guide**](./guidelines/05_extraction_guide.md) | Docling, Playwright, chunking strategies, LiteLLM reader |
| [06](./guidelines/06_environment_setup.md) | [**Environment Setup**](./guidelines/06_environment_setup.md) | `.env` variables, service setup, credentials |
| [07](./guidelines/07_development_guide.md) | [**Development Guide**](./guidelines/07_development_guide.md) | Testing practices, CLI tools (`mall-ingest`), feature addition |

---

## 📁 Interactive Project Directory Map

Click any folder name to navigate directly to its dedicated README and module documentation:

```
Shopping_web_Agentic_RAG/
│
├── 📘 guidelines/               ← Full system guidelines & standards
│
├── 🔵 backend/                  ← Core business logic & LangGraph state machine
│   ├── agents/                  LangGraph nodes (supervisor, retriever, responder)
│   ├── api/                     Internal routers
│   ├── cache/                   Async Redis client
│   ├── db/                      SQLAlchemy 2.0 async ORM & Neon Postgres models
│   ├── ingest/                  Scraper, Validator, Indexer, DocIngester, CLI
│   ├── mcp/                     Model Context Protocol server implementation
│   ├── schemas/                 Pydantic AI product & audit validation models
│   └── vector/                  ChromaDB client (embedded local & server modes)
│
├── 🌉 bridge/                   ← FastAPI bridge layer (REST + WebSockets + MCP)
│   ├── api/                     REST routers & WebSocket stream router
│   ├── mcp/                     MCP tool bridges
│   └── main.py                  FastAPI server factory & CLI runner (`mall-serve`)
│
├── 🟡 frontend/                 ← User & Admin UI interfaces
│   ├── web/                     6 Web pages (HTML5, Vanilla CSS 2026 Theme)
│   └── desktop/                 Python Tkinter desktop GUI module
│
├── 🖥️ desktop_gui/              ← Desktop management application launcher & tools
│
├── 📄 docs/                     ← Technical specifications & architecture specs
│
├── 🤖 models/                   ← Local GGUF LLM models (Phi-3.5)
│
├── 🔧 scripts/                  ← Helper scripts (model downloader, LLM check)
│
├── 🧪 tests/                    ← Pytest automated unit & integration test suite
│
├── 📦 app/                      ← Mirrored application package
│
├── docker-compose.yml           ← Container orchestration (Postgres, Redis, Chroma, Infinity)
├── pyproject.toml               ← Dependencies & project scripts
├── .env.example                 ← Environment template
└── README.md                    ← Root documentation
```

---

## ⚡ Quick Start Guide

### 1. Clone & Install Dependencies
```bash
git clone https://github.com/dung1308/Shopping_web_Agentic_RAG.git
cd Shopping_web_Agentic_RAG

# Install editable package with dev dependencies
pip install -e ".[dev]"
playwright install chromium
```

### 2. Configure Environment
```bash
cp .env.example .env
# Edit .env with your Neon PostgreSQL DSN and optional LLM keys
# Detailed reference: guidelines/06_environment_setup.md
```

### 3. Vector Database Mode
ChromaDB supports **Embedded Local Mode** (no Docker required for dev):
- Default setting: `CHROMA_PATH=./chroma_data` automatically stores vectors locally in `./chroma_data`.

Optionally, run full infrastructure with Docker Compose:
```bash
docker-compose up -d
```

### 4. Run API Server (Bridge)
```bash
# Start server via CLI
mall-serve

# Or via uvicorn:
uvicorn bridge.main:app --host 0.0.0.0 --port 8000 --reload
```
Interactive REST OpenAPI documentation will be available at: `http://localhost:8000/docs`.

### 5. Launch Desktop GUI (Optional)
```bash
python desktop_gui/main.py
```

### 6. Ingest Documents or Store Pages
```bash
# Ingest PDF catalog
mall-ingest ingest-file \
    --file catalog.pdf \
    --store-id "store-uuid-123" \
    --store-name "Zara" \
    --floor 2

# Scrape and ingest live store URL
mall-ingest ingest-url \
    --url "https://zara.com.vn/collection" \
    --store-id "store-uuid-123"
```

---

## 🛠️ Technology Stack

| Layer | Technology | Role |
|---|---|---|
| **Agent Orchestration** | [LangGraph](https://python.langchain.com/docs/langgraph/) | Supervisor routing state machine → Retriever → Responder |
| **API Server** | [FastAPI](https://fastapi.tiangolo.com/) | Async REST API, WebSockets streaming, SSE events |
| **Vector Database** | [ChromaDB](https://www.trychroma.com/) | Dense vector similarity search & metadata filtering (`./chroma_data`) |
| **Relational Database** | [Neon PostgreSQL](https://neon.tech/) | Serverless Postgres for products, stores, audit flags |
| **Caching** | [Redis](https://redis.io/) / Fallback | In-memory session store & cache |
| **Validation** | [Pydantic AI](https://ai.pydantic.dev/) | Strict product validation & compliance rule enforcement |
| **Extraction** | [Docling](https://ds4sd.github.io/docling/) / [Playwright](https://playwright.dev/) | PDF/DOCX/HTML extraction & headless page scraping |
| **Embeddings** | `BAAI/bge-m3` via [Infinity](https://github.com/michaelfeil/infinity) | Multilingual 1024-dim vector embeddings |

---

## 🧪 Testing

Run the automated test suite with `pytest`:
```bash
python -m pytest tests/ -v
```

---

## 📄 License
MIT License — see LICENSE for details.
