# 🛒 Dual-View Agentic RAG System — Shopping Mall PRD

> **Version**: 1.0 | **Date**: 2026-07-31 | **Status**: Draft for Review

---

## 1. Executive Summary

This document specifies the technical requirements for a **Dual-View Agentic RAG (Retrieval-Augmented Generation) System** tailored for a shopping mall environment. The system provides two distinct interfaces:

- **End-User View**: A conversational product discovery assistant powered by multi-agent reasoning.
- **Admin View**: A structured data governance dashboard for verifying extraction accuracy, price bounds, and date validity of scraped mall data.

The core tech stack is:
| Layer | Technology | Role |
|---|---|---|
| Agent Orchestration | **LangGraph** | State machine for multi-agent workflows |
| API Backend | **FastAPI** | REST + WebSocket server |
| Data Validation | **Pydantic AI** | Strict schema enforcement on scraped data |
| Vector Store | **Qdrant / Chroma** | Semantic retrieval of product & store data |
| LLM Provider | **Llama 3.1 / Qwen2.5** (local, fine-tuned) | Reasoning & generation backbone (self-hosted via Ollama or vLLM) |
| Database | **PostgreSQL + Redis** | Persistent store + caching layer |

---

## 2. Problem Statement

Shopping malls aggregate data from dozens of tenant stores — each with its own website, promotional calendar, and pricing format. This creates:

- **Fragmented discovery**: Shoppers cannot search across stores in natural language.
- **Data drift risk**: Scraped prices, hours, and promotions become stale or malformed.
- **No auditability**: Admins have no structured interface to verify extracted data quality.

---

## 3. Goals & Non-Goals

### Goals
- [x] Provide a conversational, intent-aware product discovery experience for end-users.
- [x] Provide an admin dashboard to audit scraped data with validation status, price bounds, and date checks.
- [x] Use LangGraph to orchestrate multi-agent pipelines for scraping, validation, and retrieval.
- [x] Use Pydantic AI to enforce strict schemas on all ingested external data.
- [x] Expose all functionality via a FastAPI backend (REST + WebSocket).

### Non-Goals
- [ ] E-commerce transactions or cart management (out of scope).
- [ ] Real-time inventory management.
- [ ] Mobile-native apps (web-first; PWA acceptable).

---

## 4. System Architecture

### 4.1 High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                          DUAL-VIEW FRONTEND                              │
│                                                                          │
│   ┌─────────────────────────┐      ┌──────────────────────────────────┐  │
│   │   END-USER VIEW         │      │   ADMIN VIEW                     │  │
│   │   (Chat Interface)      │      │   (Data Governance Dashboard)    │  │
│   │                         │      │                                  │  │
│   │  • Natural language Q&A │      │  • Extraction accuracy report    │  │
│   │  • Product cards        │      │  • Price bounds checker          │  │
│   │  • Store recommendations│      │  • Date/promo validation panel   │  │
│   │  • Map integration      │      │  • Manual override & re-trigger  │  │
│   └──────────┬──────────────┘      └────────────────┬─────────────────┘  │
└──────────────│─────────────────────────────────────│────────────────────┘
               │  WebSocket / REST                   │  REST / SSE
               ▼                                     ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                          FASTAPI BACKEND                                 │
│                                                                          │
│   /api/user/*   (chat, search, recommend)                               │
│   /api/admin/*  (jobs, validations, overrides, reports)                 │
│   /api/ingest/* (scrape trigger, status, re-index)                      │
│   /ws/chat      (streaming agent responses)                              │
└──────────────────────────┬───────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                    LANGGRAPH AGENT ORCHESTRATION                         │
│                                                                          │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐                 │
│  │  SUPERVISOR  │──▶│  SCRAPER     │──▶│  VALIDATOR   │                 │
│  │  AGENT       │   │  AGENT       │   │  AGENT       │                 │
│  │              │   │  (per store) │   │  (Pydantic AI│                 │
│  └──────┬───────┘   └──────────────┘   └──────┬───────┘                 │
│         │                                      │                         │
│         ▼                                      ▼                         │
│  ┌──────────────┐                   ┌──────────────────┐                 │
│  │  RETRIEVAL   │                   │  INDEXER AGENT   │                 │
│  │  AGENT       │                   │  (Vector + SQL)  │                 │
│  │  (RAG)       │                   │                  │                 │
│  └──────┬───────┘                   └──────────────────┘                 │
│         │                                                                │
│         ▼                                                                │
│  ┌──────────────┐                                                        │
│  │  RESPONDER   │                                                        │
│  │  AGENT       │                                                        │
│  │  (LLM gen)   │                                                        │
│  └──────────────┘                                                        │
└──────────────────────────────────────────────────────────────────────────┘
                           │
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
   ┌────────────┐  ┌─────────────┐  ┌─────────────┐
   │ PostgreSQL │  │  Qdrant /   │  │   Redis     │
   │ (products, │  │  Chroma     │  │ (cache,     │
   │  stores,   │  │  (vectors)  │  │  sessions,  │
   │  jobs,     │  │             │  │  rate limit)│
   │  audit log)│  └─────────────┘  └─────────────┘
   └────────────┘
```

---

### 4.2 LangGraph State Machine

The agent graph is defined as a **StateGraph** with typed nodes and conditional edges.

```
                ┌─────────────┐
                │  START NODE │
                └──────┬──────┘
                       │
             ┌─────────▼──────────┐
             │  SUPERVISOR AGENT  │  ← Classifies intent:
             │  (Router)          │    "query" | "scrape" | "admin"
             └─────┬──────┬───────┘
                   │      │
        ┌──────────▼─┐  ┌─▼───────────────┐
        │  SCRAPE    │  │  QUERY PIPELINE  │
        │  PIPELINE  │  │                 │
        └──────┬─────┘  └────────┬────────┘
               │                 │
        ┌──────▼──────┐  ┌───────▼───────┐
        │ SCRAPER     │  │ RETRIEVER     │
        │ AGENT       │  │ AGENT         │
        │ (crawl,     │  │ (hybrid       │
        │  extract)   │  │  search)      │
        └──────┬──────┘  └───────┬───────┘
               │                 │
        ┌──────▼──────┐  ┌───────▼───────┐
        │ VALIDATOR   │  │ RE-RANKER     │
        │ AGENT       │  │ (cross-enc)   │
        │ (Pydantic AI│  │               │
        │  schemas)   │  └───────┬───────┘
        └──────┬──────┘          │
               │          ┌──────▼───────┐
        ┌──────▼──────┐   │ RESPONDER    │
        │ INDEXER     │   │ AGENT        │
        │ AGENT       │   │ (LLM + cit.) │
        │ (upsert)    │   └──────┬───────┘
        └─────────────┘          │
                          ┌──────▼───────┐
                          │  END NODE    │
                          └──────────────┘
```

**State Schema (TypedDict)**:
```python
class MallRAGState(TypedDict):
    session_id: str
    intent: Literal["query", "scrape", "admin_audit"]
    user_query: str
    retrieved_docs: list[Document]
    validated_items: list[ValidatedProduct]
    audit_flags: list[AuditFlag]
    final_response: str
    error: Optional[str]
```

---

### 4.3 Pydantic AI Data Schemas

All data ingested from web scraping passes through strict Pydantic AI validators before being stored.

```python
# Core product schema
class ScrapedProduct(BaseModel):
    model_config = ConfigDict(strict=True)

    store_id: UUID
    product_name: str = Field(min_length=1, max_length=300)
    price_vnd: Decimal = Field(gt=0, le=500_000_000)          # price bounds
    discount_pct: Optional[float] = Field(None, ge=0.0, le=1.0)
    promo_start: Optional[date]
    promo_end: Optional[date]
    category: ProductCategory                                   # Enum
    image_url: AnyHttpUrl
    scraped_at: datetime

    @model_validator(mode="after")
    def check_date_range(self) -> "ScrapedProduct":
        if self.promo_start and self.promo_end:
            if self.promo_end <= self.promo_start:
                raise ValueError("promo_end must be after promo_start")
            if (self.promo_end - self.promo_start).days > 365:
                raise ValueError("Promotion window exceeds 1 year — suspicious")
        return self

# Store operating hours schema
class StoreHours(BaseModel):
    model_config = ConfigDict(strict=True)

    store_id: UUID
    weekday_open: time
    weekday_close: time
    weekend_open: time
    weekend_close: time
    special_closures: list[date] = Field(default_factory=list)

    @model_validator(mode="after")
    def hours_sanity(self) -> "StoreHours":
        if self.weekday_close <= self.weekday_open:
            raise ValueError("Close time must be after open time")
        return self
```

**Audit Flags** are automatically generated when validation fails:
```python
class AuditFlag(BaseModel):
    flag_id: UUID
    store_id: UUID
    field: str
    issue: Literal["price_out_of_bounds", "invalid_date", "missing_field", "schema_mismatch"]
    raw_value: Any
    severity: Literal["warning", "error", "critical"]
    created_at: datetime
    resolved: bool = False
```

---

## 5. Core User Stories

### 5.1 End-User Stories

| ID | As a... | I want to... | So that... | Acceptance Criteria |
|---|---|---|---|---|
| **U-001** | Shopper | Ask in natural language "Where can I find a birthday cake under 200k?" | I discover relevant stores quickly | Agent returns ≥1 store with product match, price shown, floor map link included |
| **U-002** | Shopper | Filter results by floor, category, or open-now status | I don't waste time going to closed stores | Filter params are applied in vector search metadata; results respect current time |
| **U-003** | Shopper | See ongoing promotions and sale dates in results | I can plan my visit around deals | Promotion dates displayed and validated against current date |
| **U-004** | Shopper | Ask follow-up questions ("Are they open on Sunday?") | I get contextual answers without repeating myself | Agent maintains session memory across turns via Redis |
| **U-005** | Shopper | See product images and prices in chat results | Results feel rich and visual | Product cards rendered with image, name, price, store name, floor |
| **U-006** | Shopper | Get a mall map reference for the recommended store | I can navigate physically | Store floor/unit number returned with every recommendation |
| **U-007** | Shopper | Use voice or text to search | I can search hands-free | Speech-to-text input supported on frontend; text always supported |

---

### 5.2 Admin Stories

| ID | As an... | I want to... | So that... | Acceptance Criteria |
|---|---|---|---|---|
| **A-001** | Admin | View a list of all scrape jobs with status (success/failed/partial) | I know which stores have fresh data | Job dashboard shows store name, last scraped, status, item count |
| **A-002** | Admin | Review all audit flags for a given store | I can fix bad data before it reaches users | Flag list shows field, raw value, issue type, severity, timestamp |
| **A-003** | Admin | Verify that scraped prices fall within acceptable bounds (per category) | Corrupted prices (e.g., "999,999,999 VND" for a bun) are caught | Price bound rules configurable per category; violations flagged as "critical" |
| **A-004** | Admin | Check that promotion dates are logically valid | Expired or nonsensical promos don't show to users | Date validator marks promos as `expired`, `future`, `active`, or `invalid` |
| **A-005** | Admin | Manually override or correct a flagged data field | I can fix a bad extraction without re-scraping | Inline edit in admin UI; change logged in audit trail with admin user ID |
| **A-006** | Admin | Trigger a re-scrape for a specific store | I can refresh data on demand | Re-scrape job queued via API; status visible in real-time via SSE |
| **A-007** | Admin | Export the validation report as CSV | I can share issues with store tenants | Export endpoint returns filtered CSV of audit flags |
| **A-008** | Admin | Set price bounds per product category | Rules reflect real-world price ranges for this mall | Admin UI for CRUD on `PriceBoundRule` records, applied in Validator Agent |
| **A-009** | Admin | See a confidence score for each extracted field | I can prioritize which records need manual review | Validator Agent outputs per-field extraction confidence (0.0–1.0) |

---

## 6. Data Flow

### 6.1 Ingestion Pipeline (Scrape → Validate → Index)

```
Step 1: TRIGGER
  Admin clicks "Scrape" in UI, or cron job fires
  → POST /api/ingest/trigger { store_id, store_url }
         │
         ▼
Step 2: SUPERVISOR AGENT dispatches SCRAPER AGENT
  • Crawls store website (HTML/JS rendering via Playwright)
  • Extracts raw JSON: { name, price, dates, images, category }
         │
         ▼
Step 3: VALIDATOR AGENT (Pydantic AI)
  • Attempts to parse raw JSON into ScrapedProduct schema
  • On success → passes to Indexer Agent
  • On failure → creates AuditFlag records in PostgreSQL
              → sends SSE notification to Admin UI
         │
         ▼
Step 4: INDEXER AGENT
  • Upserts validated products into PostgreSQL
  • Generates embeddings (OpenAI / local model)
  • Upserts vectors into Qdrant with metadata:
      { store_id, category, price, floor, is_active_promo }
  • Invalidates Redis cache for affected stores
         │
         ▼
Step 5: COMPLETION
  • Job status updated: SUCCESS | PARTIAL (some flags) | FAILED
  • Admin dashboard reflects new data immediately
```

### 6.2 Query Pipeline (User Chat → RAG → Response)

```
Step 1: USER INPUT
  User types: "Find me leather bags under 800k near Floor 2"
  → POST /api/user/chat  or  WebSocket /ws/chat
         │
         ▼
Step 2: SUPERVISOR AGENT — Intent Classification
  • Classifies: product_search | store_info | navigation | general
  • Extracts entities: { category: "leather bag", max_price: 800000, floor: 2 }
         │
         ▼
Step 3: RETRIEVER AGENT — Hybrid Search
  a. Dense search: embed query → search Qdrant
     Filter: price_vnd ≤ 800000 AND floor = 2 AND is_valid = true
  b. Sparse search: BM25 keyword match (product_name, store_name)
  c. Merge + deduplicate → top 10 candidates
         │
         ▼
Step 4: RE-RANKER
  • Cross-encoder scores each candidate against original query
  • Returns top 3–5 results
         │
         ▼
Step 5: RESPONDER AGENT
  • Builds prompt with retrieved context + user query + session history
  • LLM generates structured response:
      { answer_text, product_cards: [...], follow_up_questions: [...] }
  • Streams tokens back via WebSocket
         │
         ▼
Step 6: FRONTEND RENDERING
  • Chat bubble with answer text
  • Product cards (image, name, price, store, floor)
  • Follow-up question chips
```

---

## 7. API Specification (FastAPI)

### 7.1 User Endpoints

| Method | Path | Description | Auth |
|---|---|---|---|
| `POST` | `/api/user/chat` | Send message, get agent response (non-streaming) | None |
| `WS` | `/ws/chat/{session_id}` | Streaming chat via WebSocket | Session token |
| `GET` | `/api/user/search` | Direct product search with filters | None |
| `GET` | `/api/user/stores` | List all stores with hours | None |
| `GET` | `/api/user/stores/{store_id}` | Store detail + products | None |
| `GET` | `/api/user/promotions` | Active promotions (date-validated) | None |

### 7.2 Admin Endpoints

| Method | Path | Description | Auth |
|---|---|---|---|
| `GET` | `/api/admin/jobs` | List all scrape jobs | Admin JWT |
| `GET` | `/api/admin/jobs/{job_id}` | Job detail + item counts | Admin JWT |
| `GET` | `/api/admin/flags` | List audit flags (filterable) | Admin JWT |
| `PATCH` | `/api/admin/flags/{flag_id}` | Resolve / override a flag | Admin JWT |
| `GET` | `/api/admin/flags/export` | Export flags as CSV | Admin JWT |
| `GET` | `/api/admin/price-rules` | List price bound rules | Admin JWT |
| `POST` | `/api/admin/price-rules` | Create price bound rule | Admin JWT |
| `PATCH` | `/api/admin/price-rules/{id}` | Update price bound rule | Admin JWT |
| `POST` | `/api/ingest/trigger` | Trigger scrape job for store | Admin JWT |
| `GET` | `/api/ingest/status/{job_id}` | Job status (SSE stream) | Admin JWT |
| `GET` | `/api/admin/reports/accuracy` | Overall extraction accuracy report | Admin JWT |

---

## 8. Database Schema (PostgreSQL)

### Core Tables

```sql
-- Stores
stores (store_id UUID PK, name TEXT, floor INT, unit TEXT, website_url TEXT,
        category store_category, created_at TIMESTAMPTZ)

-- Products (validated)
products (product_id UUID PK, store_id UUID FK, name TEXT, price_vnd DECIMAL,
          discount_pct FLOAT, category product_category, image_url TEXT,
          promo_start DATE, promo_end DATE, is_active BOOL,
          last_scraped_at TIMESTAMPTZ, confidence_score FLOAT)

-- Scrape Jobs
scrape_jobs (job_id UUID PK, store_id UUID FK, triggered_by TEXT,
             status job_status, items_scraped INT, items_failed INT,
             started_at TIMESTAMPTZ, completed_at TIMESTAMPTZ)

-- Audit Flags
audit_flags (flag_id UUID PK, job_id UUID FK, store_id UUID FK,
             product_name TEXT, field TEXT, raw_value JSONB,
             issue flag_issue_type, severity flag_severity,
             resolved BOOL DEFAULT FALSE, resolved_by TEXT,
             resolved_at TIMESTAMPTZ, created_at TIMESTAMPTZ)

-- Price Bound Rules
price_bound_rules (rule_id UUID PK, category product_category,
                   min_price_vnd DECIMAL, max_price_vnd DECIMAL,
                   updated_by TEXT, updated_at TIMESTAMPTZ)

-- Admin Audit Log
admin_audit_log (log_id UUID PK, admin_id TEXT, action TEXT,
                 target_table TEXT, target_id UUID, old_value JSONB,
                 new_value JSONB, created_at TIMESTAMPTZ)
```

---

## 9. Non-Functional Requirements

| Requirement | Target |
|---|---|
| **Chat Response Latency** | ≤ 3 seconds (P95) for first token via streaming |
| **Scrape Throughput** | ≥ 10 stores/hour (parallelized Scraper Agents) |
| **Validation Accuracy** | ≥ 95% of valid records pass schema without flag |
| **API Availability** | 99.5% uptime SLA |
| **Data Freshness** | Products re-scraped every 6 hours (cron) or on-demand |
| **Security** | Admin routes protected by JWT; role-based access (RBAC) |
| **Vector Index Recall** | ≥ 0.85 recall@10 on product search benchmark set |
| **Scalability** | Horizontal scaling of FastAPI workers; Redis-backed session store |

---

## 10. CLI & MCP Reference

A dedicated specification document covering all **developer CLI commands** and **Model Context Protocol (MCP) server definitions** is maintained separately:

→ **[cli_mcp_spec.md](file:///C:/Users/Admin/.gemini/antigravity-ide/brain/4eedaeb3-8936-48dd-849e-97219d523956/cli_mcp_spec.md)**

This file covers: model serving (Ollama / vLLM), fine-tuning workflows, vector DB management, agent graph inspection, and MCP server/tool registration.

---

## 11. Open Questions

> [!IMPORTANT]
> These must be answered before implementation begins.

1. **LLM Provider** ✅ *Resolved*: Local fine-tuned models — **Llama 3.1** and/or **Qwen2.5** — served via **Ollama** (dev) or **vLLM** (production). Embedding model should also be local (e.g., `bge-m3` for multilingual/Vietnamese support). See [`cli_mcp_spec.md`](file:///C:/Users/Admin/.gemini/antigravity-ide/brain/4eedaeb3-8936-48dd-849e-97219d523956/cli_mcp_spec.md) for model serving CLI commands and MCP server definitions.
2. **Scraping Consent**: Do all tenant stores permit automated scraping, or do any require partner API integration instead?
3. **Language Support**: Is the system Vietnamese-first, bilingual (VI/EN), or English-only?
4. **Authentication for End-Users**: Should the user view require login (e.g., for personalization), or remain fully anonymous?
5. **Mall Scope**: How many tenant stores are in scope for v1? (Affects scraping agent concurrency design.)
6. **Embedding Model** ✅ *Resolved*: Self-hosted `bge-m3` (multilingual, strong Vietnamese support), served alongside the local LLM.
7. **Admin SSO**: Should the admin panel integrate with an existing SSO (e.g., Google Workspace, Azure AD)?

---

## 12. Milestones

| Phase | Milestone | Duration |
|---|---|---|
| **Phase 1** | Infrastructure setup: FastAPI skeleton, DB schema, Docker compose | 1 week |
| **Phase 2** | Scraper Agent + Pydantic AI validators + audit flag system | 2 weeks |
| **Phase 3** | LangGraph agent graph: Supervisor, Retriever, Responder | 2 weeks |
| **Phase 4** | User chat UI + WebSocket streaming | 1 week |
| **Phase 5** | Admin dashboard: jobs, flags, price rules, reports | 2 weeks |
| **Phase 6** | Integration testing, RAG quality evaluation, perf tuning | 1 week |
| **Total** | | **~9 weeks** |

---

*PRD authored by Antigravity AI | Review requested*
