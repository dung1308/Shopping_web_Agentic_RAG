# ⚙️ 06 — Environment Setup & LLM Provider Configuration Guide

> Complete reference for all `.env` variables, LLM provider selection, setup connection diagnostics, and multi-role authentication credentials.

---

## Quick Start

```bash
cp .env.example .env
# Edit .env with your PostgreSQL DSN and API keys, then:
pip install -e ".[dev]"
.venv\Scripts\python scripts/check_all_connections.py
uvicorn backend.main:app --port 8000 --reload
```

---

## 🤖 LLM Provider Selection & Key Configuration

When configuring your `.env`, set your API keys (`OPENAI_API_KEY`, `GEMINI_API_KEY`, `ANTHROPIC_API_KEY`) and explicitly choose the active LLM provider via `LLM_READER_PROVIDER`:

```env
# ── Cloud LLM API Keys ───────────────────────────────────────────────────
# 1. OpenAI — GPT-4o / GPT-4o-mini (Best multimodal quality & vision)
OPENAI_API_KEY=sk-proj-your-key-here

# 2. Google Gemini — Gemini 1.5 Flash / Pro (Native PDF inline & fast search)
GEMINI_API_KEY=AIzaSyYourKeyHere

# 3. Anthropic — Claude 3.5 Sonnet (Upload-once Files API & prompt caching)
ANTHROPIC_API_KEY=sk-ant-your-key-here

# ── SELECT ACTIVE LLM READER / ENRICHMENT PROVIDER ────────────────────────
# Options: "openai" | "gemini" | "anthropic" | "local" | "none"
# - "openai"   : Uses OPENAI_API_KEY
# - "gemini"   : Uses GEMINI_API_KEY
# - "anthropic": Uses ANTHROPIC_API_KEY
# - "local"    : Uses local Ollama at LLM_BASE_URL (Default — offline, free, CPU-safe)
# - "none"     : Pure Docling extraction & vector embedding (no LLM reading)
LLM_READER_PROVIDER=gemini   # <--- Set to "openai" or "gemini" or "local"
```

### How to Toggle / Test LLM Providers in Frontend & CLI

1. **Visual Connection Setup Diagnostics UI (`/connection_status.html`)**:
   - Navigate to `http://localhost:8000/connection_status.html` in your browser.
   - Go to the **LLM Provider Playground** tab.
   - Select **Google Gemini (`gemini-1.5-flash`)**, **OpenAI (`gpt-4o-mini`)**, **Anthropic Claude**, or **Local Ollama** from the dropdown menu.
   - Click **🚀 Test Inference Query** to send a test prompt and verify response latency and key validity in real time.

2. **Terminal CLI Probe Script**:
   - Run `.venv\Scripts\python scripts/check_all_connections.py` directly in terminal.
   - Automatically probes Neon DB, Redis, OpenAI, Gemini, Anthropic, Ollama, ChromaDB, and Embedding Server in parallel.

---

## All Environment Variables Reference

### Application & Security
```env
APP_ENV=development          # development | production | test
API_HOST=0.0.0.0             # Server bind host
API_PORT=8000                # Server bind port
API_SECRET_KEY=...           # JWT secret — run: openssl rand -hex 32
ADMIN_JWT_ALGORITHM=HS256
ADMIN_JWT_EXPIRE_MINUTES=60
```

### PostgreSQL (Neon Cloud or Local)
```env
POSTGRES_USER=neondb_owner
POSTGRES_PASSWORD=your_password
POSTGRES_DB=neondb
POSTGRES_HOST=your-host.neon.tech
POSTGRES_PORT=5432

# Async DSN (used by SQLAlchemy 2.0 ORM):
DATABASE_URL=postgresql+asyncpg://user:pass@ep-cool-name.us-east-2.aws.neon.tech/mallrag?ssl=require
```

### Redis Cache
```env
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=redispass
REDIS_URL=redis://:redispass@localhost:6379/0
SESSION_TTL_SECONDS=3600     # How long chat sessions stay in memory
```

### Local LLM (Ollama / vLLM)
```env
LLM_BASE_URL=http://localhost:11434/v1
LLM_API_KEY=ollama           # Placeholder — Ollama doesn't need a real key
LLM_MODEL=phi3.5-local
LLM_TEMPERATURE=0.3
LLM_MAX_TOKENS=2048
```

Setup Ollama:
```bash
# Install from https://ollama.com
ollama pull phi3.5          # or: ollama pull qwen2.5:7b
ollama create phi3.5-local -f models/Modelfile
```

### ChromaDB Vector Database
```env
CHROMA_PATH=./chroma_data     # Embedded persistent folder mode (Default)
CHROMA_HOST=                 # Set to host (e.g. "localhost") if using Chroma HTTP server
CHROMA_PORT=8200
CHROMA_COLLECTION=mall_products
```

---

## 🔐 Multi-Role Demo Credentials

The backend includes automatic database seeding for 4 roles:

| Role | Email | Password | Access Level |
|---|---|---|---|
| 👑 **System Admin** | `admin@mallrag.com` | `admin123` | Full administrative access |
| 🏪 **Store Manager** | `manager@nike.com` | `manager123` | Store products & store jobs access |
| 🔍 **Data Auditor** | `auditor@mallrag.com` | `auditor123` | Audit flags & data quality access |
| 🛒 **Shopper / Guest** | `shopper@gmail.com` | `shopper123` | Public assistant & search access |

Log in to test at `http://localhost:8000/auth.html`.
