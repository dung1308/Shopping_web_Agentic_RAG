# 📘 00 — System Overview & Design Philosophy

> **Read this first.** This document explains what the system is, why it's built this way, and how all the pieces fit together conceptually.

---

## What This System Is

**Mall RAG** is an AI-powered assistant for a shopping mall, built with a modern agentic architecture. It serves two types of users simultaneously:

| User | Goal | Interface |
|------|------|-----------|
| **Shopper** | Ask questions, find products, discover deals | Chat UI / Web |
| **Admin** | Monitor data quality, manage store content, audit flags | Dashboard / Desktop GUI |

---

## The Three-Layer Design

The project is split into three folders, each with a clear responsibility:

```
┌─────────────────────────────────────────────────────┐
│  frontend/          What the user sees & touches    │
│  (web + desktop)    HTML pages, Python desktop GUI  │
└──────────────────────────┬──────────────────────────┘
                           │  HTTP / WebSocket / SSE
┌──────────────────────────▼──────────────────────────┐
│  bridge/            The connection layer             │
│  (api + mcp)        FastAPI routes, WebSocket,       │
│                     GraphQL, SSE streaming           │
└──────────────────────────┬──────────────────────────┘
                           │  Python function calls
┌──────────────────────────▼──────────────────────────┐
│  backend/           Pure business logic              │
│  (agents, db,       RAG pipeline, embeddings,        │
│   ingest, vector)   LLM calls, Docling extraction    │
└─────────────────────────────────────────────────────┘
```

**The key rule:** Data flows DOWN (frontend → bridge → backend) for requests, and UP (backend → bridge → frontend) for responses. The `frontend/` never imports from `backend/` directly. The `backend/` never knows the frontend exists.

---

## Why This Architecture?

### 1. Separation of Concerns
Each layer has one job. If you change the frontend from HTML to React, only `frontend/` changes. If you swap the API from REST to GraphQL, only `bridge/` changes. The `backend/` business logic stays untouched.

### 2. Testability
The `backend/` can be unit-tested without starting a web server. The `bridge/` can be integration-tested without running the ML models.

### 3. Scalability
In production, you can deploy `bridge/` on multiple containers behind a load balancer while `backend/` services run separately.

---

## Technology Decisions at a Glance

| Decision | Choice | Reason |
|----------|--------|--------|
| LLM orchestration | LangGraph | State machine — safe, debuggable agent routing |
| Vector DB | Qdrant | Best-in-class hybrid search (dense + sparse) |
| Database | Neon PostgreSQL | Serverless, scales to zero, HTTP-compatible |
| Embedding | BAAI/bge-m3 | Multilingual, 1024-dim, runs on CPU |
| API protocol | GraphQL + SSE + REST | See `04_bridge_guide.md` for why |
| Document extraction | Docling | CPU-safe, handles PDF/DOCX/images/HTML |
| Local LLM | Ollama + Phi-3.5 | Runs fully offline, no VRAM required |

---

## Quick Navigation

| What you want to understand | Read |
|-----------------------------|------|
| Full system diagram | `01_architecture.md` |
| Backend internals (RAG, agents) | `02_backend_guide.md` |
| Frontend pages & desktop app | `03_frontend_guide.md` |
| API: GraphQL vs REST vs SSE | `04_bridge_guide.md` |
| Document extraction pipeline | `05_extraction_guide.md` |
| All environment variables | `06_environment_setup.md` |
| Running tests, CLI commands | `07_development_guide.md` |
