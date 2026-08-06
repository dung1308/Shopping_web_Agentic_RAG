# 📦 Application Module (`app/`)

This directory acts as a mirrored application package for legacy and standalone module compatibility alongside [`backend/`](../backend/).

---

## 📁 Directory Structure

- [`agents/`](./agents/) — LangGraph RAG pipeline agents (`supervisor.py`, `retriever.py`, `responder.py`, `mall_graph.py`).
- [`api/`](./api/) — REST & WebSocket API routers (`user.py`, `admin.py`, `ingest.py`, `websocket.py`).
- [`cache/`](./cache/) — Async Redis client.
- [`db/`](./db/) — SQLAlchemy async database session & models.
- [`ingest/`](./ingest/) — Document ingestion pipeline & Typer CLI.
- [`schemas/`](./schemas/) — Pydantic validation schemas.
- [`vector/`](./vector/) — ChromaDB client (`chroma_client.py`) & backward-compat forwarder (`qdrant_client.py`).
- [`config.py`](./config.py) — Settings configuration.
- [`main.py`](./main.py) — Application entry point.

---

## 🔗 Related Resources
- Core backend architecture: [`../backend/`](../backend/)
