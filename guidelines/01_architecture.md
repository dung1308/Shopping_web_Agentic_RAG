# 📐 01 — Full Architecture Diagrams

---

## System Architecture (Top Level)

```
┌─────────────────────────────────────────────────────────────────────┐
│                         FRONTEND LAYER                              │
│                                                                     │
│  frontend/web/                    frontend/desktop/                 │
│  ┌────────────────────┐           ┌────────────────────┐           │
│  │  shopper_chat.html │           │  shopper_assistant  │           │
│  │  store_directory   │           │  admin_dashboard    │           │
│  │  admin_governance  │           │  catalog_manager    │           │
│  │  rag_debugger      │           │  scraper_pipeline   │           │
│  │  scraper_manager   │           │  vector_workbench   │           │
│  └────────┬───────────┘           └─────────┬──────────┘           │
└───────────┼───────────────────────────────────┼────────────────────┘
            │  HTTP / SSE / WebSocket           │  HTTP / Python
            ▼                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                          BRIDGE LAYER                               │
│                                                                     │
│  bridge/                                                            │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  FastAPI Application (bridge/main.py)                        │   │
│  │                                                              │   │
│  │  REST /api/user/*      → Product search, stores, promos     │   │
│  │  REST /api/admin/*     → Audit flags, overrides, jobs       │   │
│  │  REST /api/ingest/*    → Pipeline triggers, status          │   │
│  │  SSE  /api/chat/stream → AI token streaming                 │   │
│  │  WS   /ws/chat/*       → Legacy WebSocket (compatibility)   │   │
│  │  GQL  /graphql         → GraphQL (Strawberry, planned)      │   │
│  └─────────────────────────────────────────────────────────────┘   │
│  bridge/mcp/  → MCP tool bridge (stdio/SSE)                        │
└───────────────────────────────┬─────────────────────────────────────┘
                                │  Python imports
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         BACKEND LAYER                               │
│                                                                     │
│  backend/                                                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐ │
│  │   AGENTS     │  │   DATABASE   │  │    INGEST PIPELINE       │ │
│  │              │  │              │  │                          │ │
│  │  Supervisor  │  │  Neon        │  │  Playwright Extractor    │ │
│  │  Retriever   │  │  PostgreSQL  │  │  Docling Extractor       │ │
│  │  Responder   │  │  (Alembic    │  │  HybridChunker           │ │
│  │  mall_graph  │  │   migrations)│  │  LiteLLM Reader          │ │
│  └──────┬───────┘  └──────────────┘  └──────────────────────────┘ │
│         │                                                           │
│  ┌──────▼───────┐  ┌──────────────┐  ┌──────────────────────────┐ │
│  │   VECTOR     │  │    CACHE     │  │     LOCAL LLM            │ │
│  │              │  │              │  │                          │ │
│  │  Qdrant      │  │  Redis       │  │  Ollama + Phi-3.5        │ │
│  │  mall_products│ │  Sessions    │  │  (or Qwen2.5)            │ │
│  │  mall_docs   │  │  Query cache │  │  CPU-safe, no VRAM       │ │
│  └──────────────┘  └──────────────┘  └──────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
                                │
                   ┌────────────┴────────────┐
                   │                         │
          ┌────────▼───────┐        ┌────────▼───────┐
          │    models/     │        │   guidelines/  │
          │  Phi-3.5.gguf  │        │  Documentation │
          │  Modelfile     │        │  (this folder) │
          └────────────────┘        └────────────────┘
```

---

## LangGraph State Machine (RAG Pipeline)

```
                    ┌────────────────────────────────┐
                    │         START                  │
                    │  user_query + session_id        │
                    └────────────────┬───────────────┘
                                     │
                                     ▼
                    ┌────────────────────────────────┐
                    │       SUPERVISOR NODE           │
                    │                                │
                    │  • Classifies intent           │
                    │  • product_search              │
                    │  • general_info                │
                    │  • out_of_scope                │
                    │  • Extracts filters            │
                    │    (floor, price, category)    │
                    └────────────────┬───────────────┘
                                     │
                       ┌─────────────┼─────────────┐
                       │             │             │
               product_search   general_info  out_of_scope
                       │             │             │
                       ▼             ▼             ▼
              ┌──────────────┐  ┌──────────┐  ┌──────────┐
              │  RETRIEVER   │  │RESPONDER │  │  END     │
              │              │  │(direct)  │  │(polite   │
              │ • bge-m3     │  └────┬─────┘  │ decline) │
              │   embedding  │       │        └──────────┘
              │ • Qdrant     │       │
              │   search     │       │
              │ • Top-10     │       │
              │   products   │       │
              └──────┬───────┘       │
                     │               │
                     ▼               ▼
              ┌────────────────────────────────┐
              │         RESPONDER NODE         │
              │                               │
              │  • Formats context string     │
              │  • Calls Phi-3.5 via Ollama   │
              │  • Streams tokens to bridge   │
              └────────────────┬──────────────┘
                               │
                               ▼
                          ┌─────────┐
                          │   END   │
                          │ Streamed│
                          │ answer  │
                          └─────────┘
```

---

## Document Ingestion Pipeline

```
Input: URL / File Path / Raw bytes
          │
          ▼
┌─────────────────────────┐
│   FORMAT DETECTION      │
│  .pdf .docx .html .json │
│  .txt .png .jpg .webp   │
└────────────┬────────────┘
             │
     ┌───────┴────────┐
     │                │
  HTML/JS URL      Local file
     │                │
     ▼                ▼
┌──────────┐    ┌───────────────┐
│Playwright│    │    Docling    │
│          │    │ DocumentConv  │
│ Renders  │    │               │
│ JS page  │    │ PDF → Markdown│
│ Captures │    │ DOCX → Markdown│
│ XHR JSON │    │ Image → OCR  │
└────┬─────┘    └──────┬────────┘
     │                 │
     └────────┬────────┘
              │  ExtractedDocument
              ▼
┌─────────────────────────┐
│   CHUNKER               │
│                         │
│  HybridChunker (Docling)│
│  → heading-aware splits │
│  → ≤512 tokens/chunk    │
│  → 64 token overlap     │
│                         │
│  SemanticChunker (fallback)
│  → regex heading split  │
└────────────┬────────────┘
             │  List[Chunk]
             ▼
┌─────────────────────────┐  Optional
│   LITELLM READER        │◄─────────
│                         │  LLM_READER_PROVIDER=
│  SUMMARIZE              │  local / openai /
│  EXTRACT_STRUCTURED     │  anthropic / gemini
│  ENRICH                 │
│  QA                     │
└────────────┬────────────┘
             │  Enriched chunks
             ▼
┌─────────────────────────┐
│   EMBEDDER              │
│                         │
│  bge-m3 via Infinity    │
│  1024-dim vectors       │
│  CPU-safe               │
└────────────┬────────────┘
             │  Vectors
             ▼
┌─────────────────────────┐
│   QDRANT UPSERT         │
│                         │
│  mall_documents         │
│  collection             │
│  + rich payload         │
│  (source, page, heading)│
└─────────────────────────┘
```

---

## Data Flow: Shopper Chat

```
User types: "Áo khoác da dưới 1 triệu ở tầng 3?"
     │
     │  POST /api/chat/stream
     │  { "query": "...", "session_id": "abc123" }
     ▼
[bridge/api/routers/chat.py]
  StreamingResponse → SSE
     │
     │  Python call
     ▼
[backend/agents/mall_graph.py]  ← LangGraph compiled graph
     │
     ├─ supervisor_node()       ← intent: product_search, floor: 3, max_price: 1M
     ├─ retriever_node()        ← bge-m3 query → Qdrant search → 10 products
     └─ responder_node()        ← Phi-3.5 generates answer, yields tokens
          │
          │  yield "Tại" yield "cửa" yield "hàng" ...
          ▼
[SSE stream → browser]
     │
     ▼
Browser appends each token to chat bubble in real-time
```
