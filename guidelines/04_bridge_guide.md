# 🌉 04 — Bridge Guide: GraphQL vs REST vs SSE

> **This is the API lesson.** Read this to understand what each API protocol does, when to use each one, and how this system uses all three together.

---

## The Problem with "Just REST"

You know REST. A REST API looks like this:

```
GET  /api/products?floor=2&category=fashion   → returns ALL product fields
GET  /api/stores                              → returns ALL store fields
GET  /api/promotions                          → returns ALL promotion fields
```

The shopper page needs: `name, price, imageUrl, storeName`
The admin page needs: `name, price, category, auditFlags, scrapedAt, storeId`

With REST, **both pages get ALL fields** even when they only need a few. This is called **over-fetching**. And if a page needs data from 3 endpoints, it makes 3 HTTP requests — this is **under-fetching** (too many round trips).

---

## Solution: Three Protocols, Three Jobs

```
Frontend Client
     │
     ├── GraphQL  /graphql ──────────────→ "I want exactly these fields"
     │                                     Flexible queries for data
     │
     ├── SSE      /api/chat/stream ──────→ Server streams tokens to you
     │   (Server-Sent Events)             For AI response streaming
     │
     └── REST     /api/* ───────────────→ Simple actions
                                          File upload, health check, triggers
```

---

## 1. 📊 GraphQL — "Ask for exactly what you need"

### What is it?
GraphQL is a query language. Instead of the server deciding what data to send, **the client decides**. You send a query describing the shape of data you want, and get exactly that back. One endpoint: `/graphql`.

### Example

**Shopper page query:**
```graphql
query SearchProducts {
  searchProducts(query: "leather bag", floor: 2, maxPrice: 800000) {
    name
    price
    storeName
    imageUrl
    discount
  }
}
```

**Returns:**
```json
{
  "data": {
    "searchProducts": [
      { "name": "Leather Tote", "price": 750000, "storeName": "Zara", "imageUrl": "...", "discount": 10 }
    ]
  }
}
```

**Admin page query** (different fields, same endpoint):
```graphql
query GetAuditFlags {
  auditFlags(status: "pending") {
    id
    product { name price category }
    violationType
    severity
    createdAt
  }
}
```

### Key Concepts

| Concept | Meaning |
|---------|---------|
| **Query** | Read-only data fetch (like GET in REST) |
| **Mutation** | Write operation — create/update/delete (like POST/PUT/DELETE) |
| **Subscription** | Real-time stream (like WebSocket) |
| **Resolver** | The Python function that fetches data for a field |
| **Schema** | The contract — defines all available types and operations |
| **GraphiQL** | Browser playground at `/graphql` — test queries interactively |

### In Python with Strawberry + FastAPI

```python
# bridge/api/graphql.py

import strawberry
from strawberry.fastapi import GraphQLRouter
from backend.vector.qdrant_client import search_vectors

@strawberry.type
class Product:
    name: str
    price: float
    store_name: str
    image_url: str | None
    discount: float

@strawberry.type
class Query:
    @strawberry.field
    async def search_products(
        self,
        query: str,
        floor: int | None = None,
        max_price: float | None = None,
    ) -> list[Product]:
        # Call backend vector search
        results = await search_vectors(query, filters={"floor": floor})
        return [Product(**r["payload"]) for r in results]

schema = strawberry.Schema(query=Query)
graphql_app = GraphQLRouter(schema, graphiql=True)
```

**Mount in bridge/main.py:**
```python
app.include_router(graphql_app, prefix="/graphql")
```

**Test at:** `http://localhost:8000/graphql` — opens the GraphiQL browser playground.

### When to use GraphQL
✅ Multiple frontend views need different shapes of the same data
✅ You want to avoid N+1 HTTP calls from the frontend
✅ You want a self-documenting schema (introspection built-in)
✅ Admin dashboard with complex filtering

---

## 2. 📡 SSE — "Server streams tokens to you"

### What is it?
Server-Sent Events (SSE) is a one-way stream from **server → client** over plain HTTP. The server keeps the connection open and pushes data as it becomes available. This is **perfect for AI streaming** because the LLM generates tokens one-by-one.

### How it compares to WebSocket

| | SSE | WebSocket |
|--|-----|-----------|
| Direction | Server → Client only | Both directions |
| Protocol | Plain HTTP | Upgraded HTTP (WS://) |
| Auto-reconnect | ✅ Built in | ❌ Manual |
| Firewall safe | ✅ Yes | ⚠️ Sometimes blocked |
| HTTP/2 support | ✅ Multiplexed | ❌ Separate connection |
| Best for | AI token streaming | Live games, collaboration |

**Why does direction matter?**
When a user sends a chat message, they send ONE request. Then the server streams back 200+ tokens. That's one-way (server → client). SSE is designed exactly for this.

### SSE in FastAPI

```python
# bridge/api/routers/chat.py

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from backend.agents.responder import responder_stream

router = APIRouter()

@router.post("/api/chat/stream")
async def stream_chat(query: str, session_id: str):
    async def token_generator():
        async for token in responder_stream(query, session_id):
            # SSE format: "data: <content>\n\n"
            yield f"data: {token}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        token_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
```

**In the browser (JavaScript):**
```javascript
const source = new EventSource('/api/chat/stream?query=...');

source.onmessage = (event) => {
    if (event.data === '[DONE]') {
        source.close();
        return;
    }
    document.getElementById('answer').textContent += event.data;
};
```

### When to use SSE
✅ AI chat response streaming (tokens arrive one-by-one)
✅ Progress notifications (ingestion job progress)
✅ Live dashboard updates (one-way data feeds)

---

## 3. 🔗 REST — "Simple actions"

REST stays for things that are naturally request-response with no streaming and no complex data shaping needed.

### What we keep as REST

| Endpoint | Method | Why REST is fine |
|----------|--------|-----------------|
| `/api/ingest/file` | POST | File upload — multipart form |
| `/api/ingest/url` | POST | Simple trigger |
| `/health` | GET | One field response |
| `/api/admin/override` | POST | Simple action |

---

## Bridge Folder Structure

```
bridge/
├── main.py                  ← FastAPI app factory (wires everything together)
├── api/
│   ├── websocket.py         ← Legacy WebSocket chat (kept for compatibility)
│   ├── graphql.py           ← GraphQL schema + resolvers (Strawberry)
│   └── routers/
│       ├── user.py          ← Shopper REST endpoints
│       ├── admin.py         ← Admin REST endpoints
│       ├── ingest.py        ← Ingest trigger endpoints
│       └── chat.py          ← SSE streaming chat endpoint
└── mcp/
    └── server.py            ← MCP bridge (Model Context Protocol — tool use)
```

---

## Protocol Decision Tree

```
Do you need real-time streaming from server?
  YES → Is it bidirectional (both sides send simultaneously)?
          YES → WebSocket
          NO  → SSE ✅
  NO → Does the client need to choose specific fields?
          YES → GraphQL ✅
          NO  → Is it a file upload or simple trigger?
                  YES → REST ✅
                  NO  → GraphQL ✅ (better default)
```

---

## Install GraphQL Support

```bash
pip install strawberry-graphql[fastapi]
```

Full implementation of the GraphQL layer is planned as the next iteration after the current REST bridge is stable.
