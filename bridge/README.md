# 🌉 Bridge Module (`bridge/`)

The **bridge** connects front-end clients (web pages, desktop apps, MCP agents) to the backend business logic and AI models.

---

## 📁 Directory Structure

- [`api/`](./api/) — API endpoints:
  - [`routers/user.py`](./api/routers/user.py) — Shopper REST endpoints (`/api/user/chat`, `/api/user/search`, `/api/user/stores`).
  - [`routers/admin.py`](./api/routers/admin.py) — Admin REST endpoints (`/api/admin/audit-flags`, `/api/admin/metrics`).
  - [`routers/ingest.py`](./api/routers/ingest.py) — Ingestion REST endpoints (`/api/ingest/trigger`, `/api/ingest/reindex`).
  - [`websocket.py`](./api/websocket.py) — Real-time WebSocket streaming route (`/ws/chat/{session_id}`).
- [`mcp/`](./mcp/) — Model Context Protocol tool definitions and transport server (stdio / SSE).
- [`main.py`](./main.py) — FastAPI application factory & CLI entry point (`mall-serve`).

---

## ⚡ Running the Bridge Server

```bash
# Via uvicorn directly:
uvicorn bridge.main:app --host 0.0.0.0 --port 8000 --reload

# Or via CLI entry point:
mall-serve
```

API docs will be available at: `http://localhost:8000/docs`.

---

## 🔗 Related Resources
- Read bridge guide in [`../guidelines/04_bridge_guide.md`](../guidelines/04_bridge_guide.md)
