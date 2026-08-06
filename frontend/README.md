# 🟡 Frontend Module (`frontend/`)

The **frontend** provides dual user interfaces: a modern web application for shoppers/admins and a desktop Tkinter application for management.

---

## 📁 Directory Structure

- [`web/`](./web/) — Web pages built with semantic HTML5 and Vanilla CSS (Modern 2026 aesthetics):
  - [`index.html`](./web/index.html) — Landing page & portal entry.
  - [`shopper_chat.html`](./web/shopper_chat.html) — Conversational AI assistant with real-time SSE streaming.
  - [`store_directory.html`](./web/store_directory.html) — Interactive shopping mall store map & catalog directory.
  - [`admin_governance.html`](./web/admin_governance.html) — Data compliance & audit dashboard.
  - [`rag_debugger.html`](./web/rag_debugger.html) — Vector search & RAG pipeline inspection tool.
  - [`scraper_manager.html`](./web/scraper_manager.html) — Web scraper job status manager.
- [`desktop/`](./desktop/) — Python Tkinter Desktop GUI apps:
  - [`main.py`](./desktop/main.py) — Desktop application runner & tab notebook controller.
  - [`shopper_assistant.py`](./desktop/shopper_assistant.py) — Desktop AI chat interface.
  - [`admin_dashboard.py`](./desktop/admin_dashboard.py) — Desktop admin governance & system metrics.
  - [`scraper_pipeline.py`](./desktop/scraper_pipeline.py) — Scraper pipeline configuration GUI.
  - [`vector_workbench.py`](./desktop/vector_workbench.py) — ChromaDB hybrid search & dense vector inspector.
  - [`catalog_manager.py`](./desktop/catalog_manager.py) — Store product catalog manager.

---

## 🚀 Running Desktop GUI
```bash
python frontend/desktop/main.py
```

---

## 🔗 Related Resources
- Read frontend guidelines in [`../guidelines/03_frontend_guide.md`](../guidelines/03_frontend_guide.md)
