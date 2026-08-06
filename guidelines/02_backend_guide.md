# 🔵 02 — Backend Guide

> The `backend/` package is the brain. It contains all AI logic, database models, vector search, caching, and the document ingestion pipeline. It has **no knowledge of HTTP or frontends**.

---

## Package Map

```
backend/
├── config.py              ← All settings loaded from .env (Pydantic-Settings v2)
├── main.py                ← Legacy entry (now bridge/main.py is preferred)
│
├── agents/                ← LangGraph RAG pipeline
│   ├── state.py           ← MallRAGState: the shared data bag passed between nodes
│   ├── supervisor.py      ← Intent classifier: routes query to right agent
│   ├── retriever.py       ← Searches Qdrant, returns product matches
│   ├── responder.py       ← Calls local LLM, streams answer tokens
│   └── mall_graph.py      ← Assembles the StateGraph (wires all nodes)
│
├── db/                    ← Database layer
│   ├── models.py          ← SQLAlchemy 2.0 async ORM models
│   └── session.py         ← Async engine + session factory
│
├── cache/
│   └── redis_client.py    ← Async Redis helpers (get/set/delete/pattern)
│
├── vector/
│   └── qdrant_client.py   ← Qdrant: init, upsert, search, multi-collection
│
├── schemas/
│   └── validation.py      ← Pydantic AI strict validation models + AuditFlag
│
└── ingest/                ← Document ingestion pipeline
    ├── cli.py             ← Typer CLI (mall-ingest commands)
    ├── agents/
    │   ├── scraper.py         Playwright product scraper
    │   ├── validator.py       Pydantic AI validation agent
    │   ├── indexer.py         Embed + upsert to Qdrant
    │   └── document_ingester.py  Full Docling pipeline orchestrator
    ├── extractors/
    │   ├── docling_extractor.py   PDF/DOCX/HTML/image/JSON → Markdown
    │   ├── playwright_extractor.py JS page capture + XHR interception
    │   └── chunker.py             HybridChunker + SemanticChunker
    └── readers/
        ├── base_reader.py        ReadTask enum + ReadResult dataclass
        ├── provider_registry.py  OpenAI/Anthropic/Gemini/Local configs
        └── litellm_reader.py     Unified multi-provider LLM reader
```

---

## How the RAG Pipeline Works

When a shopper sends a question, it goes through this LangGraph state machine:

```
User query: "Where can I find a leather bag under 800k on Floor 2?"
     │
     ▼
[SUPERVISOR NODE]
  - Classifies intent (product_search / general_info / out_of_scope)
  - Sets state.intent + state.search_filters
     │
     ▼
[RETRIEVER NODE]
  - Builds bge-m3 embedding of the query
  - Searches Qdrant with filters: {floor: 2, price_vnd: {lte: 800000}, category: "fashion"}
  - Returns top-10 matching product chunks
     │
     ▼
[RESPONDER NODE]
  - Formats retrieved products as context
  - Calls local LLM (Phi-3.5 / Qwen2.5) with the context
  - Streams answer tokens back
     │
     ▼
Answer: "You can find leather bags at Zara on Floor 2, currently at 750,000 VND..."
```

---

## Key Concepts

### MallRAGState (state.py)
Think of this as a shared clipboard that every agent node reads from and writes to:

```python
class MallRAGState(TypedDict):
    query: str              # Original user question
    intent: str             # Classified intent
    search_filters: dict    # Price range, floor, category
    retrieved_docs: list    # Products found by Retriever
    answer: str             # Final streamed answer
    session_id: str         # Links to Redis session memory
```

### Two Qdrant Collections
- `mall_products` — structured product records (name, price, store, floor)
- `mall_documents` — rich document chunks (PDF pages, HTML sections, JSON data)

When a user asks a product question → searches `mall_products`.
When context needs deeper document knowledge → searches `mall_documents`.

### Embedding Model (bge-m3)
- Runs via **Infinity** server locally at `http://localhost:7997`
- 1024-dimensional multilingual vectors
- Supports Vietnamese, English, and mixed queries
- CPU-only by default (`EMBED_DEVICE=cpu`)

---

## Config System (config.py)

All settings come from `.env` via `Pydantic-Settings v2`. Access anywhere:

```python
from backend.config import get_settings
settings = get_settings()  # cached singleton

print(settings.llm_model)      # "phi3.5-local"
print(settings.embed_dim)      # 1024
print(settings.docling_device) # "cpu"
```

Full reference → `guidelines/06_environment_setup.md`
