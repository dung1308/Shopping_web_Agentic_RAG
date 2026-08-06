# ⚙️ 06 — Environment Setup Guide

> Complete reference for all `.env` variables. Copy `.env.example` to `.env` and fill in your values.

---

## Quick Start

```bash
cp .env.example .env
# Edit .env with your values, then:
pip install -e ".[dev]"
python -m alembic upgrade head
uvicorn bridge.main:app --port 8000 --reload
```

---

## All Variables

### Application
```env
APP_ENV=development          # development | production | test
API_HOST=0.0.0.0             # Server bind host
API_PORT=8000                # Server bind port
API_SECRET_KEY=...           # JWT secret — run: openssl rand -hex 32
ADMIN_JWT_ALGORITHM=HS256
ADMIN_JWT_EXPIRE_MINUTES=60
```

### PostgreSQL (Neon)
```env
POSTGRES_USER=neondb_owner
POSTGRES_PASSWORD=your_password
POSTGRES_DB=neondb
POSTGRES_HOST=your-host.neon.tech
POSTGRES_PORT=5432

# Full DSN (auto-built if not set, but can override):
DATABASE_URL=postgresql://user:pass@host/db?sslmode=require
# ↑ Automatically converted to postgresql+asyncpg:// internally
```

Get a free Neon DB at https://neon.tech — takes 2 minutes.

### Redis
```env
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=redispass
REDIS_URL=redis://:redispass@localhost:6379/0
SESSION_TTL_SECONDS=3600     # How long chat sessions stay in memory
```

Start Redis with Docker:
```bash
docker run -d -p 6379:6379 redis:alpine redis-server --requirepass redispass
```

### Qdrant (Vector Database)
```env
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=qdrantdev     # Any string for local; real key for cloud
QDRANT_COLLECTION=mall_products
# mall_documents collection is auto-created alongside it
```

Start Qdrant with Docker:
```bash
docker run -d -p 6333:6333 qdrant/qdrant
```

### Local LLM (Ollama)
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
# Load custom model from models/Modelfile:
ollama create phi3.5-local -f models/Modelfile
```

### Embedding Model (Infinity)
```env
EMBED_BASE_URL=http://localhost:7997
EMBED_MODEL=BAAI/bge-m3
EMBED_DIM=1024
EMBED_DEVICE=cpu             # "cpu" (safe) | "cuda" (faster if GPU)
```

Start Infinity with Docker:
```bash
docker run -d -p 7997:7997 michaelf34/infinity:latest \
    --model-name-or-path BAAI/bge-m3 --device cpu
```

### Playwright / Scraping
```env
PLAYWRIGHT_HEADLESS=true     # false = see browser window (debug)
SCRAPE_CONCURRENCY=4         # Parallel scrape workers
SCRAPE_TIMEOUT_SECONDS=30    # Per-page timeout
SCRAPE_CRON="0 */6 * * *"   # Cron schedule (every 6 hours)
```

### Docling (Document Extraction)
```env
DOCLING_DEVICE=cpu           # "cpu" (your machine) | "cuda" (5x faster)
DOCLING_ENABLE_OCR=true      # Extract text from images in PDFs
DOCLING_OCR_ENGINE=easyocr   # "easyocr" (pip only) | "tesseract" (system)
```

### Chunking
```env
INGEST_CHUNK_SIZE=512        # Max tokens per chunk (64–4096)
INGEST_CHUNK_OVERLAP=64      # Overlap tokens between chunks (0–512)
INGEST_MAX_FILE_MB=50        # Max local file size in MB
```

**Tuning advice:**
- Shorter chunks (256) → better precision for short queries
- Longer chunks (1024) → better for documents with long context
- More overlap (128) → less risk of splitting key sentences

### LLM Reader
```env
LLM_READER_PROVIDER=local    # Default: Ollama (free, no GPU)
# Options: openai | anthropic | gemini | local | none
```

### LLM API Keys (cloud providers — optional)
```env
OPENAI_API_KEY=sk-...        # GPT-4o — best for images, vision tasks
ANTHROPIC_API_KEY=sk-ant-... # Claude — best for large docs, caching
GEMINI_API_KEY=AI...         # Gemini Flash — fast, native PDF support
```

All three are optional. If `LLM_READER_PROVIDER=local`, no key is needed.

### MCP (Model Context Protocol)
```env
MCP_TRANSPORT=stdio          # "stdio" (local) | "sse" (remote)
MCP_SSE_PORT=8001            # Port for SSE transport
```

---

## Services Checklist

Before running, ensure these are accessible:

| Service | Check | Command |
|---------|-------|---------|
| PostgreSQL (Neon) | `psql $DATABASE_URL -c "SELECT 1"` | Managed cloud |
| Redis | `redis-cli ping` → PONG | `docker run -d -p 6379:6379 redis` |
| Qdrant | `curl http://localhost:6333/health` | `docker run -d -p 6333:6333 qdrant/qdrant` |
| Ollama | `curl http://localhost:11434/api/tags` | `ollama serve` |
| Infinity | `curl http://localhost:7997/health` | `docker run ...` (see above) |

Or start everything with Docker Compose:
```bash
docker-compose up -d
```

---

## Common Issues

| Problem | Fix |
|---------|-----|
| `DATABASE_URL` asyncpg error | Let config.py auto-convert — don't add `+asyncpg` manually |
| `Qdrant not initialised` | Call `init_qdrant()` first (bridge lifespan does this) |
| OCR very slow | Set `DOCLING_DEVICE=cpu` and be patient; EasyOCR loads ~30s first time |
| Import `from app.` error | Update to `from backend.` — old package name changed |
| `mall-serve` not found | Run `pip install -e ".[dev]"` to reinstall entry points |
