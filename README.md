# 🛒 Mall RAG — Agentic AI System for Shopping Malls

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.141-009688.svg)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-1.2-orange.svg)](https://python.langchain.com/docs/langgraph/)
[![Docling](https://img.shields.io/badge/Docling-2.118-blueviolet.svg)](https://ds4sd.github.io/docling/)
[![LiteLLM](https://img.shields.io/badge/LiteLLM-1.95-yellow.svg)](https://litellm.ai/)
[![Qdrant](https://img.shields.io/badge/Qdrant-Vector_DB-red.svg)](https://qdrant.tech/)
[![Neon](https://img.shields.io/badge/Neon-PostgreSQL_18-00e599.svg)](https://neon.tech/)

> An autonomous agentic RAG (Retrieval-Augmented Generation) system for modern shopping malls. Combines a **conversational AI assistant** for shoppers with a **data governance dashboard** for admins — backed by a hybrid vector search engine, multi-format document ingestion, and a multi-provider LLM reader.

---

## 📖 Read the Guidelines First

All documentation lives in [`guidelines/`](./guidelines/). Start here:

| # | Guide | What you'll learn |
|---|-------|------------------|
| [00](./guidelines/00_overview.md) | System Overview | Design philosophy, 3-layer architecture, tech decisions |
| [01](./guidelines/01_architecture.md) | Architecture Diagrams | Full system + RAG pipeline + ingestion flow diagrams |
| [02](./guidelines/02_backend_guide.md) | Backend Guide | LangGraph agents, RAG pipeline, Qdrant, config system |
| [03](./guidelines/03_frontend_guide.md) | Frontend Guide | Web pages, desktop GUI, how they talk to the bridge |
| [04](./guidelines/04_bridge_guide.md) | **API Bridge Guide** | **GraphQL vs REST vs SSE — when and why to use each** |
| [05](./guidelines/05_extraction_guide.md) | Extraction Guide | Docling, Playwright, chunking, LLM reading pipeline |
| [06](./guidelines/06_environment_setup.md) | Environment Setup | All `.env` variables, service setup, common issues |
| [07](./guidelines/07_development_guide.md) | Development Guide | Testing, CLI commands, adding new features |

---

## 🏗️ Project Structure

```
portfolio/
│
├── 📘 guidelines/               ← Read this first — all documentation
│   ├── 00_overview.md
│   ├── 01_architecture.md
│   ├── 02_backend_guide.md
│   ├── 03_frontend_guide.md
│   ├── 04_bridge_guide.md       ← GraphQL + SSE + REST explained
│   ├── 05_extraction_guide.md
│   ├── 06_environment_setup.md
│   └── 07_development_guide.md
│
├── 🟡 frontend/                 ← What users see & touch
│   ├── web/                     HTML + Vanilla JS (6 pages)
│   │   ├── index.html           Landing page
│   │   ├── shopper_chat.html    AI chat assistant
│   │   ├── store_directory.html Browse stores
│   │   ├── admin_governance.html Audit dashboard
│   │   ├── rag_debugger.html    RAG pipeline debug
│   │   └── scraper_manager.html Scrape job manager
│   └── desktop/                 Python Tkinter desktop GUI
│       ├── main.py
│       ├── admin_dashboard.py
│       ├── shopper_assistant.py
│       └── ...
│
├── 🌉 bridge/                   ← API layer connecting frontend ↔ backend
│   ├── main.py                  FastAPI app factory (entry point)
│   ├── api/
│   │   ├── websocket.py         WebSocket /ws/chat/{session_id}
│   │   └── routers/
│   │       ├── user.py          GET /api/user/* (products, stores, chat)
│   │       ├── admin.py         GET/POST /api/admin/* (audit, jobs)
│   │       └── ingest.py        POST /api/ingest/* (pipeline triggers)
│   └── mcp/                     MCP tool bridge (stdio/SSE)
│
├── 🔵 backend/                  ← Pure business logic (no HTTP)
│   ├── config.py                All settings via Pydantic-Settings v2
│   ├── agents/                  LangGraph RAG pipeline
│   │   ├── state.py             MallRAGState shared data bag
│   │   ├── supervisor.py        Intent classifier + router
│   │   ├── retriever.py         Qdrant hybrid vector search
│   │   ├── responder.py         LLM answer generator + streaming
│   │   └── mall_graph.py        Compiled LangGraph StateGraph
│   ├── db/                      SQLAlchemy 2.0 async ORM
│   ├── cache/                   Async Redis client
│   ├── vector/                  Qdrant client (2 collections)
│   ├── schemas/                 Pydantic AI validation models
│   └── ingest/                  Document ingestion pipeline
│       ├── cli.py               Typer CLI (mall-ingest)
│       ├── agents/              Scraper / Validator / Indexer / DocIngester
│       ├── extractors/          Docling / Playwright / Chunker
│       └── readers/             LiteLLM multi-provider reader
│
├── 🗄️  alembic/                 Database migrations
├── 🤖 models/                   Local LLM weights (Phi-3.5.gguf)
├── 🔧 scripts/                  Utility scripts
├── 🧪 tests/                    Pytest suite (33 tests)
│
├── docker-compose.yml
├── pyproject.toml
├── .env.example
└── README.md
```

---

## ⚡ Quick Start

### 1. Prerequisites
- Python 3.11+
- [Ollama](https://ollama.com) (local LLM)
- [Docker](https://docker.com) (for Qdrant, Redis, Infinity)
- A [Neon](https://neon.tech) account (free Postgres)

### 2. Install
```bash
git clone <repository-url>
cd portfolio
pip install -e ".[dev]"
playwright install chromium
```

### 3. Configure
```bash
cp .env.example .env
# Fill in your Neon DATABASE_URL and any optional API keys
# See guidelines/06_environment_setup.md for all variables
```

### 4. Start Services
```bash
# Qdrant + Redis + Infinity embedding server
docker-compose up -d

# Ollama local LLM
ollama pull phi3.5
ollama create phi3.5-local -f models/Modelfile
```

### 5. Migrate Database
```bash
python -m alembic upgrade head
```

### 6. Run the Server
```bash
uvicorn bridge.main:app --host 127.0.0.1 --port 8000 --reload
# → REST docs:    http://127.0.0.1:8000/docs
# → GraphQL:      http://127.0.0.1:8000/graphql  (coming soon)
```

### 7. Ingest Your First Document
```bash
# Index a product catalog PDF
mall-ingest ingest-file \
    --file catalog.pdf \
    --store-id "your-store-uuid" \
    --store-name "Store Name" \
    --floor 2

# Or capture a live product page
mall-ingest ingest-url \
    --url "https://store.example.com/products" \
    --store-id "your-store-uuid"
```

---

## 🛠️ Technology Stack

### Core
| Layer | Technology | Version | Role |
|-------|-----------|---------|------|
| Agent orchestration | [LangGraph](https://github.com/langchain-ai/langgraph) | 1.2 | State machine: Supervisor → Retriever → Responder |
| API bridge | [FastAPI](https://fastapi.tiangolo.com) | 0.141 | Async REST + WebSocket + SSE server |
| Data validation | [Pydantic AI](https://ai.pydantic.dev) | 2.21 | Strict product validation + AuditFlag generation |

### Storage
| Layer | Technology | Role |
|-------|-----------|------|
| Relational DB | [Neon PostgreSQL](https://neon.tech) | Products, stores, jobs, audit logs |
| Vector DB | [Qdrant](https://qdrant.tech) | Hybrid dense+sparse search (2 collections) |
| Cache | [Redis](https://redis.io) | Session memory + query result cache |

### AI / ML
| Layer | Technology | Role |
|-------|-----------|------|
| Embeddings | `BAAI/bge-m3` via [Infinity](https://github.com/michaelfeil/infinity) | 1024-dim multilingual vectors, CPU-safe |
| Local LLM | Phi-3.5 via [Ollama](https://ollama.com) | Answer generation, runs offline, no VRAM |
| Cloud LLMs | OpenAI / Anthropic / Gemini via [LiteLLM](https://litellm.ai) | Optional enrichment |

### Document Ingestion
| Layer | Technology | Role |
|-------|-----------|------|
| Extraction | [Docling](https://ds4sd.github.io/docling/) | PDF/DOCX/HTML/image/JSON → Markdown, CPU-safe |
| JS Capture | [Playwright](https://playwright.dev/python/) | Renders JS pages, intercepts XHR responses |

---

## 🧪 Tests

```bash
python -m pytest tests/ -v
# 33 passed in 0.52s
```

---

## 📄 License

MIT License — see LICENSE for details.
