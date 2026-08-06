# 🟡 03 — Frontend Guide

---

## Overview

The frontend has two flavours serving the same backend:

| | `frontend/web/` | `frontend/desktop/` |
|--|----------------|---------------------|
| Tech | HTML + Vanilla JS | Python (Tkinter) |
| Runs in | Browser | Native window |
| Users | Shoppers + Admins (browser) | Admins (local machine) |
| Talks to bridge via | `fetch()` / `EventSource` / `WebSocket` | `httpx` (HTTP) |

---

## Web Pages (`frontend/web/`)

### Pages Map

| File | Route | Who uses it |
|------|-------|-------------|
| `index.html` | `/` | Landing / navigation hub |
| `shopper_chat.html` | `/shopper` | Shoppers — AI chat assistant |
| `store_directory.html` | `/stores` | Shoppers — browse all stores |
| `admin_governance.html` | `/admin` | Admins — audit flags, overrides |
| `rag_debugger.html` | `/debug` | Developers — RAG pipeline debug |
| `scraper_manager.html` | `/scraper` | Admins — trigger + monitor scrapes |

### How `shopper_chat.html` Talks to the Bridge

```javascript
// Shopper sends a message
async function sendMessage(userText) {
    const source = new EventSource(
        `/api/chat/stream?query=${encodeURIComponent(userText)}&session_id=${sessionId}`
    );

    let answer = "";

    source.onmessage = (event) => {
        if (event.data === "[DONE]") {
            source.close();
            renderFinalAnswer(answer);
            return;
        }
        answer += event.data;
        updateStreamingBubble(answer);  // Updates in real-time
    };

    source.onerror = () => source.close();
}
```

### How Admin Pages Call REST

```javascript
// Fetch audit flags
const response = await fetch("/api/admin/audit-flags?status=pending");
const flags = await response.json();
renderFlagsTable(flags);

// Trigger a scrape job
await fetch("/api/ingest/trigger", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ store_id: "...", url: "https://store.com" })
});
```

---

## Desktop GUI (`frontend/desktop/`)

The desktop app is a Python Tkinter application for admins who prefer a native interface. It uses `httpx` to call the same bridge API.

### Entry Point
```bash
python frontend/desktop/main.py
```

### Modules

| File | Screen | Purpose |
|------|--------|---------|
| `main.py` | App shell | Tkinter window + tab navigation |
| `shopper_assistant.py` | Chat tab | Text chat interface to AI assistant |
| `admin_dashboard.py` | Admin tab | Audit flags, metrics overview |
| `catalog_manager.py` | Catalog tab | Browse/edit product catalog |
| `scraper_pipeline.py` | Scraper tab | Trigger and monitor ingest jobs |
| `vector_workbench.py` | Debug tab | Inspect Qdrant vectors, test searches |

### How Desktop Calls the Bridge

```python
# frontend/desktop/shopper_assistant.py
import httpx
import json

async def ask_question(query: str, session_id: str):
    """Stream AI response via SSE into the Tkinter text widget."""
    async with httpx.AsyncClient() as client:
        async with client.stream(
            "POST",
            "http://localhost:8000/api/chat/stream",
            params={"query": query, "session_id": session_id},
            timeout=60.0,
        ) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    token = line[6:]
                    if token == "[DONE]":
                        break
                    self.append_token(token)  # Updates Tkinter text widget
```

---

## Adding a New Web Page

1. Create `frontend/web/my_page.html`
2. Use the bridge API — all endpoints are documented at `http://localhost:8000/docs`
3. For data queries: use REST `fetch()` or (when GraphQL is enabled) the `/graphql` endpoint
4. For streaming: use `EventSource` pointing to an SSE endpoint

---

## Static File Serving

The `frontend/web/` HTML files are currently served as static files. In development, open them directly in the browser. For production, FastAPI can serve them:

```python
# bridge/main.py (add this)
from fastapi.staticfiles import StaticFiles
app.mount("/web", StaticFiles(directory="frontend/web", html=True), name="web")
```
