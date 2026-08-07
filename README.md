# 🛒 Shopping Web Agentic RAG — Dual-View AI System

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2.35-orange.svg)](https://python.langchain.com/docs/langgraph/)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-1.5.9-blueviolet.svg)](https://www.trychroma.com/)
[![Neon](https://img.shields.io/badge/Neon-PostgreSQL_Serverless-00e599.svg)](https://neon.tech/)
[![GitHub](https://img.shields.io/badge/GitHub-dung1308%2FShopping__web__Agentic__RAG-black?logo=github)](https://github.com/dung1308/Shopping_web_Agentic_RAG.git)

> An autonomous **Dual-View Agentic RAG (Retrieval-Augmented Generation)** system designed for modern shopping malls. Combines a **conversational AI assistant for shoppers** with a **data governance dashboard for admins** — backed by ChromaDB hybrid vector search, multi-format document ingestion (PDF, DOCX, HTML, Images), multi-provider LLM support (**OpenAI**, **Google Gemini**, **Anthropic**, **Local Ollama**), and multi-role authentication (**Admin**, **Store Manager**, **Data Auditor**, **Shopper/Guest**).

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
| [05](./guidelines/05_extraction_guide.md) | [**Extraction Guide**](./guidelines/05_extraction_guide.md) | Docling, Playwright, chunking strategies, LLM reader selection |
| [06](./guidelines/06_environment_setup.md) | [**Environment Setup**](./guidelines/06_environment_setup.md) | `.env` variables, LLM provider selection, service setup |
| [07](./guidelines/07_development_guide.md) | [**Development Guide**](./guidelines/07_development_guide.md) | Testing practices, CLI tools (`mall-ingest`), feature addition |

---

## ⚙️ How to Configure `.env` & Select Active LLM Provider

When setting up your local `.env` file, configure your API keys and **select the active provider** via `LLM_READER_PROVIDER`:

```env
# ── 1. Database Configuration (Neon Cloud PostgreSQL or Local) ────────────
DATABASE_URL=postgresql+asyncpg://user:password@ep-cool-name.us-east-2.aws.neon.tech/mallrag?ssl=require

# ── 2. Redis Cache ────────────────────────────────────────────────────────
REDIS_URL=redis://:redispass@localhost:6379/0

# ── 3. Cloud LLM API Keys (Set your OpenAI, Gemini, or Anthropic keys) ─────
OPENAI_API_KEY=sk-proj-your-openai-key-here
GEMINI_API_KEY=AIzaSyYourGeminiKeyHere
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key-here

# ── 4. SELECT ACTIVE LLM READER / ENRICHMENT PROVIDER ─────────────────────
# Options: "openai" | "gemini" | "anthropic" | "local" | "none"
# - "openai"   : Uses OPENAI_API_KEY (GPT-4o / GPT-4o-mini — best multimodal quality)
# - "gemini"   : Uses GEMINI_API_KEY (Google Gemini 1.5 Flash / Pro — fast native PDF)
# - "anthropic": Uses ANTHROPIC_API_KEY (Claude 3.5 Sonnet — high context)
# - "local"    : Uses local Ollama at LLM_BASE_URL (Default — offline, free, CPU-safe)
# - "none"     : Pure Docling extraction & vector embedding without LLM enrichment
LLM_READER_PROVIDER=gemini   # <--- Change this to "openai", "gemini", or "local"

# ── 5. Local Ollama LLM Settings ──────────────────────────────────────────
LLM_BASE_URL=http://localhost:11434/v1
LLM_MODEL=phi3.5-local

# ── 6. Security ───────────────────────────────────────────────────────────
API_SECRET_KEY=use_openssl_rand_hex_32_string_here
```

---

## 🛠️ Testing & Toggling LLMs in Frontend & Terminal

### 1. Visual Connection Setup Diagnostics UI (`/connection_status.html`)
Start the FastAPI server and navigate to `http://localhost:8000/connection_status.html`:
- **Real-Time Status Cards**: Shows live connection status badges and latency (ms) for **Neon DB**, **Redis**, **OpenAI**, **Google Gemini**, **Anthropic**, **Ollama**, **ChromaDB**, and **Embedding Server**.
- **Interactive LLM Provider Playground**: Allows you to toggle between **OpenAI (`gpt-4o-mini`)**, **Google Gemini (`gemini-1.5-flash`)**, **Anthropic Claude**, and **Local Ollama** with a dropdown to execute live test prompts in real time.

### 2. Terminal CLI Connection Diagnostic Script
Run the automated CLI probe directly from your terminal:
```bash
.venv\Scripts\python scripts/check_all_connections.py
```
This script will test all configured service endpoints in parallel and display colored status badges (`✅ CONNECTED`, `❌ FAILED`, `⚪ NOT CONFIGURED`), measured latency, and actionable fix hints.

---

## 🔐 Multi-Role Authorization & Identity Portal (`/auth.html`)

The system features JWT authentication and Role-Based Access Control (RBAC) with 4 distinct roles:

| Role | Access Scope | Description & Capabilities |
|---|---|---|
| 👑 **`admin`** | Full System Access | System setup, user management, global scrape jobs, data governance, audit flags, price rules. |
| 🏪 **`store_manager`** *(Middle Role)* | Store-scoped Access | Manage store products, view store metrics & scrape jobs for assigned store. |
| 🔍 **`data_auditor`** *(Middle Role)* | Data Governance | Review & resolve data quality audit flags, price bound rules, extraction accuracy reports. |
| 🛒 **`shopper` / `guest`** | Public Access | Public product search, shopper AI assistant chat, interactive mall map directory. |

### 1-Click Quick Demo Accounts (Test at `/auth.html`)
- **👑 System Admin**: `admin@mallrag.com` (password: `admin123`)
- **🏪 Store Manager**: `manager@nike.com` (password: `manager123`)
- **🔍 Data Auditor**: `auditor@mallrag.com` (password: `auditor123`)
- **🛒 Shopper / Guest**: `shopper@gmail.com` (password: `shopper123`)

---

## 📁 Interactive Project Directory Map

```
Shopping_web_Agentic_RAG/
│
├── 📘 guidelines/               ← Full system guidelines & standards
│
├── 🔵 backend/                  ← Core business logic & LangGraph state machine
│   ├── agents/                  LangGraph nodes (supervisor, retriever, responder)
│   ├── api/                     Internal routers (auth, user, admin, ingest, diagnostics)
│   ├── auth/                    JWT security & RBAC role authorization module
│   ├── cache/                   Async Redis client
│   ├── db/                      SQLAlchemy 2.0 async ORM & Neon Postgres models
│   ├── ingest/                  Scraper, Validator, Indexer, DocIngester, CLI
│   ├── mcp/                     Model Context Protocol server implementation
│   ├── schemas/                 Pydantic AI product & audit validation models
│   └── vector/                  ChromaDB client (embedded local & server modes)
│
├── 🌉 bridge/                   ← FastAPI bridge layer (REST + WebSockets + MCP)
│
├── 🟡 web_frontend/             ← Web pages (HTML5, Vanilla CSS 2026 Theme)
│   ├── index.html               AI Portal Main Dashboard
│   ├── auth.html                Login & Signup Authorization Portal
│   ├── connection_status.html   Service Setup & LLM Provider Diagnostic UI
│   ├── shopper_chat.html        Conversational AI Assistant with SSE streaming
│   ├── store_directory.html     Interactive Shopping Mall Map
│   ├── admin_governance.html    Admin Data Governance & Audit Flags
│   └── document_studio.html     Document & URL Ingestion Studio
│
├── 🖥️ desktop_gui/              ← Desktop management application launcher & tools
│
├── 🤖 models/                   ← Local GGUF LLM models (Phi-3.5)
│
├── 🔧 scripts/                  ← Helper scripts (`check_all_connections.py`, `verify_auth_system.py`)
│
├── 🧪 tests/                    ← Pytest automated unit & integration test suite
│
├── docker-compose.yml           ← Container orchestration (Postgres, Redis, Chroma, Infinity)
├── pyproject.toml               ← Dependencies & project scripts
├── .env.example                 ← Environment template
└── README.md                    ← Root documentation
```

---

## ⚡ Quick Start & GitHub Codespaces Setup

### ☁️ GitHub Codespaces (Automated 1-Click Setup)
When you open this repository in **GitHub Codespaces** (or VS Code Dev Containers):
1. **Automated Setup**: Codespaces uses [.devcontainer/devcontainer.json](file:///e:/VINSMART_Future_Thuc_Tap/portfolio/.devcontainer/devcontainer.json) and [.devcontainer/setup.sh](file:///e:/VINSMART_Future_Thuc_Tap/portfolio/.devcontainer/setup.sh) to automatically:
   - Install Python dependencies (`pip install -e ".[dev]"`).
   - Install **Ollama** and pull the default local GGUF model (`phi3.5`).
   - Pre-download the **`BAAI/bge-m3`** embedding model weights into cache.
   - Initialize `.env` from `.env.example`.
   - Run initial service diagnostic probes (`scripts/check_all_connections.py`).
2. **Manual Trigger (if needed)**: You can also trigger the setup script manually in any Codespace terminal:
   ```bash
   bash scripts/setup_codespaces.sh
   ```

---

### 💻 Local Machine Quick Start

#### 1. Clone & Install Dependencies
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
# Edit .env with your Neon PostgreSQL DSN, LLM_READER_PROVIDER, and API keys
```

### 3. Run Service Diagnostics
```bash
.venv\Scripts\python scripts/check_all_connections.py
```

### 4. Run API Server & Open Portal
```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```
Navigate to:
- **AI Portal Home**: `http://localhost:8000/index.html`
- **Setup Connection Diagnostics**: `http://localhost:8000/connection_status.html`
- **Login & Authorization Portal**: `http://localhost:8000/auth.html`
- **Interactive REST OpenAPI Specs**: `http://localhost:8000/docs`

---

## 🛠️ Technology Stack

| Layer | Technology | Role |
|---|---|---|
| **Agent Orchestration** | [LangGraph](https://python.langchain.com/docs/langgraph/) | Supervisor routing state machine → Retriever → Responder |
| **API Server** | [FastAPI](https://fastapi.tiangolo.com/) | Async REST API, WebSockets streaming, SSE events |
| **Authentication & RBAC** | PyJWT + Passlib | Multi-role authorization (`admin`, `store_manager`, `data_auditor`, `shopper`) |
| **LLM Providers** | OpenAI / Gemini / Anthropic / Ollama | Multi-provider LLM reading & text inference |
| **Vector Database** | [ChromaDB](https://www.trychroma.com/) | Dense vector similarity search & metadata filtering (`./chroma_data`) |
| **Relational Database** | [Neon PostgreSQL](https://neon.tech/) | Serverless Postgres for products, stores, users, audit flags |
| **Caching** | [Redis](https://redis.io/) / Fallback | In-memory session store & cache |
| **Validation** | [Pydantic AI](https://ai.pydantic.dev/) | Strict product validation & compliance rule enforcement |
| **Extraction** | [Docling](https://ds4sd.github.io/docling/) / [Playwright](https://playwright.dev/) | PDF/DOCX/HTML extraction & headless page scraping |

---

## 🧪 Testing

Run the automated test suite with `pytest`:
```bash
python -m pytest tests/ -v
```

---

## 📄 License
MIT License — see LICENSE for details.
