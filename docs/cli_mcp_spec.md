# 🛠️ CLI & MCP Specification — Mall Agentic RAG

> **Companion to**: [`implementation_plan.md`](file:///C:/Users/Admin/.gemini/antigravity-ide/brain/4eedaeb3-8936-48dd-849e-97219d523956/implementation_plan.md)
> **Version**: 1.0 | **Date**: 2026-07-31

This document is the definitive reference for:
- **CLI commands** used by developers and DevOps to run, manage, and fine-tune the system.
- **MCP (Model Context Protocol) server** and tool definitions for agent-tool integration.

---

## 1. Local LLM Stack

### 1.1 Model Choices

| Model | Size | Best For | Serving Backend |
|---|---|---|---|
| `Llama-3.1-8B-Instruct` | 8B | Fast inference, low VRAM | Ollama (dev), vLLM (prod) |
| `Llama-3.1-70B-Instruct` | 70B | High reasoning quality | vLLM (prod, multi-GPU) |
| `Qwen2.5-7B-Instruct` | 7B | Strong multilingual (VI/EN/ZH) | Ollama (dev), vLLM (prod) |
| `Qwen2.5-72B-Instruct` | 72B | Best quality, production grade | vLLM (prod, multi-GPU) |
| `bge-m3` | 570M | Multilingual embeddings | Infinity Embedding / vLLM |

> [!TIP]
> **Recommendation for v1**: Start with `Qwen2.5-7B-Instruct` via Ollama for development (Vietnamese support is superior to Llama on multilingual benchmarks). Upgrade to `Qwen2.5-72B` via vLLM for production.

---

## 2. CLI Reference

### 2.1 Ollama — Development LLM Serving

```bash
# Pull models
ollama pull qwen2.5:7b-instruct
ollama pull llama3.1:8b-instruct

# Run model server (default port 11434)
ollama serve

# Interactive chat (for prompt testing)
ollama run qwen2.5:7b-instruct

# List loaded models
ollama list

# Show model info / architecture
ollama show qwen2.5:7b-instruct

# Remove a model
ollama rm llama3.1:8b-instruct

# Check running model processes
ollama ps
```

**Ollama API endpoint** (OpenAI-compatible):
```
http://localhost:11434/v1/chat/completions
```

---

### 2.2 vLLM — Production LLM Serving

```bash
# Single GPU — Qwen2.5 7B
python -m vllm.entrypoints.openai.api_server \
  --model Qwen/Qwen2.5-7B-Instruct \
  --port 8080 \
  --max-model-len 8192 \
  --dtype auto \
  --served-model-name qwen2.5-7b

# Multi-GPU — Qwen2.5 72B (tensor parallel across 4 GPUs)
python -m vllm.entrypoints.openai.api_server \
  --model Qwen/Qwen2.5-72B-Instruct \
  --port 8080 \
  --tensor-parallel-size 4 \
  --max-model-len 32768 \
  --dtype bfloat16 \
  --served-model-name qwen2.5-72b

# Multi-GPU — Llama 3.1 70B
python -m vllm.entrypoints.openai.api_server \
  --model meta-llama/Meta-Llama-3.1-70B-Instruct \
  --port 8080 \
  --tensor-parallel-size 4 \
  --dtype bfloat16 \
  --served-model-name llama3.1-70b

# Health check
curl http://localhost:8080/health

# List available models
curl http://localhost:8080/v1/models
```

---

### 2.3 Embedding Model — bge-m3 (Infinity Embedding)

```bash
# Install
pip install infinity-emb[all]

# Serve bge-m3 (port 7997)
infinity_emb start \
  --model-name-or-path BAAI/bge-m3 \
  --port 7997 \
  --batch-size 32 \
  --device cuda

# Test embedding endpoint
curl -X POST http://localhost:7997/embeddings \
  -H "Content-Type: application/json" \
  -d '{"input": ["Túi da nữ chính hãng"], "model": "BAAI/bge-m3"}'
```

> [!NOTE]
> `bge-m3` produces 1024-dimensional embeddings. Configure Qdrant vector collection with `size=1024, distance=Cosine`.

---

### 2.4 Fine-Tuning Pipeline

#### Step 1 — Prepare dataset
```bash
# Convert scraped mall data to fine-tuning JSONL format
python scripts/finetune/prepare_dataset.py \
  --input data/scraped_products.json \
  --output data/finetune_train.jsonl \
  --format chatml \
  --task product_qa

# JSONL format (ChatML):
# {"messages": [
#   {"role": "system", "content": "You are a mall assistant..."},
#   {"role": "user", "content": "Có túi xách nào dưới 500k không?"},
#   {"role": "assistant", "content": "Có! Store ABC tại tầng 2..."}
# ]}
```

#### Step 2 — Fine-tune with LLaMA-Factory
```bash
# Install LLaMA-Factory
pip install llamafactory

# Fine-tune Qwen2.5-7B with LoRA (4-bit QLoRA)
llamafactory-cli train \
  --model_name_or_path Qwen/Qwen2.5-7B-Instruct \
  --stage sft \
  --do_train true \
  --finetuning_type lora \
  --lora_rank 16 \
  --lora_alpha 32 \
  --lora_dropout 0.05 \
  --quantization_bit 4 \
  --dataset mall_qa \
  --template qwen \
  --cutoff_len 2048 \
  --max_samples 5000 \
  --per_device_train_batch_size 4 \
  --gradient_accumulation_steps 4 \
  --lr_scheduler_type cosine \
  --learning_rate 5e-5 \
  --num_train_epochs 3 \
  --output_dir output/qwen2.5-7b-mall-lora \
  --logging_steps 10 \
  --save_steps 100

# Merge LoRA weights into base model
llamafactory-cli export \
  --model_name_or_path Qwen/Qwen2.5-7B-Instruct \
  --adapter_name_or_path output/qwen2.5-7b-mall-lora \
  --export_dir output/qwen2.5-7b-mall-merged \
  --export_size 4 \
  --export_dtype bfloat16

# Evaluate
llamafactory-cli eval \
  --model_name_or_path output/qwen2.5-7b-mall-merged \
  --task mmlu \
  --lang en
```

#### Step 3 — Serve the fine-tuned model
```bash
# Via Ollama (create Modelfile)
cat > Modelfile << 'EOF'
FROM ./output/qwen2.5-7b-mall-merged
SYSTEM "You are MallBot, an intelligent assistant for [Mall Name]. Answer only in Vietnamese or English based on user preference."
PARAMETER temperature 0.3
PARAMETER top_p 0.9
EOF

ollama create mallbot-qwen:7b -f Modelfile
ollama run mallbot-qwen:7b
```

---

### 2.5 Qdrant — Vector Database

```bash
# Pull and run Qdrant (Docker)
docker run -d --name qdrant \
  -p 6333:6333 \
  -p 6334:6334 \
  -v $(pwd)/qdrant_data:/qdrant/storage \
  qdrant/qdrant:latest

# Create product collection
curl -X PUT http://localhost:6333/collections/mall_products \
  -H "Content-Type: application/json" \
  -d '{
    "vectors": {
      "size": 1024,
      "distance": "Cosine"
    },
    "optimizers_config": {
      "default_segment_number": 4
    }
  }'

# List collections
curl http://localhost:6333/collections

# Collection info
curl http://localhost:6333/collections/mall_products

# Delete collection (caution)
curl -X DELETE http://localhost:6333/collections/mall_products

# Qdrant Web UI
open http://localhost:6333/dashboard
```

---

### 2.6 FastAPI Backend

```bash
# Development (with hot reload)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production (with Gunicorn workers)
gunicorn app.main:app \
  -k uvicorn.workers.UvicornWorker \
  -w 4 \
  --bind 0.0.0.0:8000 \
  --timeout 120

# Generate OpenAPI spec
python -c "
import json, app.main as m
print(json.dumps(m.app.openapi(), indent=2))
" > openapi.json

# Run database migrations (Alembic)
alembic upgrade head
alembic revision --autogenerate -m "add audit_flags table"
alembic downgrade -1
```

---

### 2.7 LangGraph — Agent Inspection CLI

```bash
# Visualize the agent state graph (generates PNG)
python scripts/graph/visualize_graph.py \
  --graph app.agents.mall_graph:build_graph \
  --output docs/agent_graph.png

# Run a single agent step in debug mode
python -m app.agents.debug_runner \
  --input '{"user_query": "tìm quần áo trẻ em giảm giá"}' \
  --step supervisor \
  --verbose

# Replay a session from stored state
python -m app.agents.replay \
  --session-id <UUID> \
  --from-step retrieval

# Inspect LangGraph thread checkpoints (if using PostgreSQL checkpointer)
python -m app.agents.checkpoints list --limit 10
python -m app.agents.checkpoints get --thread-id <UUID>
```

---

### 2.8 Scrape & Ingestion

```bash
# Trigger scrape for a single store (CLI)
python -m app.ingest.cli scrape \
  --store-id <UUID> \
  --url https://store-website.com \
  --headless true \
  --output-dir data/raw/

# Validate a raw JSON file against Pydantic schemas
python -m app.ingest.cli validate \
  --input data/raw/store_abc.json \
  --output data/validated/store_abc.json \
  --flags-output data/flags/store_abc_flags.json

# Re-index all validated products into Qdrant
python -m app.ingest.cli reindex \
  --store-id all \
  --batch-size 50

# Run full pipeline (scrape + validate + index) for all stores
python -m app.ingest.cli pipeline \
  --config config/stores.yaml \
  --workers 4
```

---

## 3. MCP (Model Context Protocol) Specification

### 3.1 Overview

The system exposes an **MCP server** so that LangGraph agents and external MCP clients (e.g., Claude Desktop, Cursor, custom tooling) can call structured tools with full schema enforcement.

```
MCP Client (agent / IDE)
        │
        │  JSON-RPC 2.0 over stdio / SSE
        ▼
┌─────────────────────────────┐
│     MCP SERVER              │
│  (FastAPI + mcp-python)     │
│                             │
│  Tools:                     │
│  • search_products          │
│  • get_store_info           │
│  • get_active_promotions    │
│  • trigger_scrape_job       │
│  • get_audit_flags          │
│  • resolve_audit_flag       │
│  • set_price_bound_rule     │
│  • get_job_status           │
└─────────────────────────────┘
```

---

### 3.2 MCP Server Config (`mcp_config.json`)

```json
{
  "mcpServers": {
    "mall-rag": {
      "command": "python",
      "args": ["-m", "app.mcp.server"],
      "env": {
        "FASTAPI_BASE_URL": "http://localhost:8000",
        "LLM_BASE_URL": "http://localhost:11434/v1",
        "LLM_MODEL": "mallbot-qwen:7b",
        "EMBED_BASE_URL": "http://localhost:7997",
        "EMBED_MODEL": "BAAI/bge-m3",
        "QDRANT_URL": "http://localhost:6333",
        "POSTGRES_DSN": "postgresql://user:pass@localhost:5432/mallrag",
        "REDIS_URL": "redis://localhost:6379/0"
      },
      "transport": "stdio"
    },
    "mall-rag-sse": {
      "url": "http://localhost:8000/mcp/sse",
      "transport": "sse"
    }
  }
}
```

> [!IMPORTANT]
> Use `stdio` transport for local dev (agent spawns server process). Use `sse` transport for deployed production where the MCP server is always running.

---

### 3.3 MCP Tool Registry

#### 🔍 `search_products`
Performs hybrid (dense + sparse) product search across the vector store.

```json
{
  "name": "search_products",
  "description": "Search for products in the mall using natural language. Returns ranked product cards with price, store, floor, and promo info.",
  "inputSchema": {
    "type": "object",
    "required": ["query"],
    "properties": {
      "query": { "type": "string", "description": "Natural language search query" },
      "max_price_vnd": { "type": "number", "description": "Maximum price filter in VND" },
      "min_price_vnd": { "type": "number", "description": "Minimum price filter in VND" },
      "category": { "type": "string", "enum": ["fashion", "food", "electronics", "beauty", "kids", "sports", "other"] },
      "floor": { "type": "integer", "minimum": 1, "maximum": 10 },
      "active_promo_only": { "type": "boolean", "default": false },
      "top_k": { "type": "integer", "default": 5, "maximum": 20 }
    }
  }
}
```

---

#### 🏪 `get_store_info`
Retrieves store details, operating hours, and current status.

```json
{
  "name": "get_store_info",
  "description": "Get detailed information about a specific store including hours, floor, and current open/closed status.",
  "inputSchema": {
    "type": "object",
    "required": ["store_id"],
    "properties": {
      "store_id": { "type": "string", "format": "uuid" },
      "include_products": { "type": "boolean", "default": false }
    }
  }
}
```

---

#### 🎉 `get_active_promotions`
Returns all date-validated, currently active promotions.

```json
{
  "name": "get_active_promotions",
  "description": "List all currently active promotional offers across the mall, validated against today's date.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "category": { "type": "string" },
      "floor": { "type": "integer" },
      "limit": { "type": "integer", "default": 10 }
    }
  }
}
```

---

#### 🔄 `trigger_scrape_job` *(Admin only)*
Triggers a new scrape pipeline for a store.

```json
{
  "name": "trigger_scrape_job",
  "description": "Trigger a new data scraping and validation job for a specific store. Requires admin privileges.",
  "inputSchema": {
    "type": "object",
    "required": ["store_id"],
    "properties": {
      "store_id": { "type": "string", "format": "uuid" },
      "force_reindex": { "type": "boolean", "default": false, "description": "Re-index even if data hasn't changed" }
    }
  }
}
```

---

#### 🚩 `get_audit_flags` *(Admin only)*
Retrieves data quality audit flags, filterable by store/severity.

```json
{
  "name": "get_audit_flags",
  "description": "Retrieve data quality audit flags generated by the Validator Agent. Filterable by store, severity, and resolution status.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "store_id": { "type": "string", "format": "uuid" },
      "severity": { "type": "string", "enum": ["warning", "error", "critical"] },
      "resolved": { "type": "boolean" },
      "issue_type": { "type": "string", "enum": ["price_out_of_bounds", "invalid_date", "missing_field", "schema_mismatch"] },
      "limit": { "type": "integer", "default": 20 }
    }
  }
}
```

---

#### ✅ `resolve_audit_flag` *(Admin only)*
Resolves a flag with an override value.

```json
{
  "name": "resolve_audit_flag",
  "description": "Mark an audit flag as resolved, optionally providing a corrected value that overrides the scraped data.",
  "inputSchema": {
    "type": "object",
    "required": ["flag_id"],
    "properties": {
      "flag_id": { "type": "string", "format": "uuid" },
      "corrected_value": { "description": "The corrected field value to store (any JSON type)" },
      "resolution_note": { "type": "string" }
    }
  }
}
```

---

#### 💰 `set_price_bound_rule` *(Admin only)*
Creates or updates a price bound rule for a category.

```json
{
  "name": "set_price_bound_rule",
  "description": "Set the acceptable price range for a product category. Used by the Validator Agent to flag out-of-bounds prices.",
  "inputSchema": {
    "type": "object",
    "required": ["category", "min_price_vnd", "max_price_vnd"],
    "properties": {
      "category": { "type": "string", "enum": ["fashion", "food", "electronics", "beauty", "kids", "sports", "other"] },
      "min_price_vnd": { "type": "number", "minimum": 0 },
      "max_price_vnd": { "type": "number", "minimum": 1 }
    }
  }
}
```

---

#### 📊 `get_job_status` *(Admin only)*
Polls the status of a scrape job.

```json
{
  "name": "get_job_status",
  "description": "Get the current status and progress of a scrape/ingestion job.",
  "inputSchema": {
    "type": "object",
    "required": ["job_id"],
    "properties": {
      "job_id": { "type": "string", "format": "uuid" }
    }
  }
}
```

---

## 4. Environment Variables Reference

```bash
# ── LLM ──────────────────────────────────────────────────────
LLM_BASE_URL=http://localhost:11434/v1          # Ollama (dev) or vLLM (prod)
LLM_MODEL=mallbot-qwen:7b                       # Fine-tuned model name
LLM_TEMPERATURE=0.3
LLM_MAX_TOKENS=2048

# ── Embedding ─────────────────────────────────────────────────
EMBED_BASE_URL=http://localhost:7997
EMBED_MODEL=BAAI/bge-m3
EMBED_DIM=1024

# ── Vector DB ─────────────────────────────────────────────────
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION=mall_products

# ── Relational DB ─────────────────────────────────────────────
POSTGRES_DSN=postgresql+asyncpg://user:pass@localhost:5432/mallrag

# ── Cache ─────────────────────────────────────────────────────
REDIS_URL=redis://localhost:6379/0
SESSION_TTL_SECONDS=3600

# ── FastAPI ───────────────────────────────────────────────────
APP_ENV=development                             # development | production
API_SECRET_KEY=<random-secret>
ADMIN_JWT_ALGORITHM=HS256
ADMIN_JWT_EXPIRE_MINUTES=60

# ── Scraping ──────────────────────────────────────────────────
PLAYWRIGHT_HEADLESS=true
SCRAPE_CONCURRENCY=4
SCRAPE_TIMEOUT_SECONDS=30
SCRAPE_CRON="0 */6 * * *"                      # every 6 hours

# ── MCP ───────────────────────────────────────────────────────
MCP_TRANSPORT=stdio                             # stdio | sse
MCP_SSE_PORT=8001
```

---

## 5. Docker Compose Service Map

```yaml
services:
  # ── Infrastructure ──────────────────────────────────────
  postgres:
    image: postgres:16-alpine
    ports: ["5432:5432"]

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]

  qdrant:
    image: qdrant/qdrant:latest
    ports: ["6333:6333", "6334:6334"]

  # ── LLM Serving ─────────────────────────────────────────
  ollama:
    image: ollama/ollama:latest
    ports: ["11434:11434"]
    volumes: ["ollama_data:/root/.ollama"]
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]

  infinity-embed:
    image: michaelf34/infinity:latest
    command: v2 --model-name-or-path BAAI/bge-m3 --port 7997
    ports: ["7997:7997"]

  # ── Application ─────────────────────────────────────────
  api:
    build: .
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000
    ports: ["8000:8000"]
    depends_on: [postgres, redis, qdrant, ollama, infinity-embed]
    env_file: .env

  mcp-server:
    build: .
    command: python -m app.mcp.server --transport sse --port 8001
    ports: ["8001:8001"]
    depends_on: [api]
    env_file: .env
```

---

*CLI & MCP Spec authored by Antigravity AI | Mall Agentic RAG System v1.0*
