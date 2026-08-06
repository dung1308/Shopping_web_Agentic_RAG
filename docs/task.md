# 📋 Mall Agentic RAG — Task Tracker

## Phase 1: Infrastructure Setup
- [x] Create project directory structure
- [x] `pyproject.toml` + `requirements.txt`
- [x] `docker-compose.yml` (Postgres, Redis, Qdrant, Ollama, Infinity Embed)
- [x] `.env.example`
- [x] FastAPI app skeleton (`app/main.py`, `app/config.py`)
- [x] PostgreSQL models (SQLAlchemy async)
- [x] Alembic migration setup
- [x] Redis client utility
- [x] Qdrant client utility

## Phase 2: Scraper Agent + Pydantic AI Validators
- [x] Pydantic AI schemas (`ScrapedProduct`, `StoreHours`, `AuditFlag`, `PriceBoundRule`)
- [ ] Scraper Agent (Playwright-based crawler)
- [ ] Validator Agent (schema enforcement + audit flag generation)
- [ ] Indexer Agent (embedding + Qdrant upsert)
- [ ] Ingest CLI (`app/ingest/cli.py`)
- [ ] `/api/ingest/*` FastAPI router

## Phase 3: LangGraph Agent Graph
- [x] `MallRAGState` TypedDict
- [x] Supervisor Agent (intent classification)
- [x] Retriever Agent (hybrid search)
- [ ] Re-ranker (cross-encoder)
- [x] Responder Agent (LLM generation)
- [x] Full LangGraph StateGraph wiring

## Phase 4: User Chat API
- [x] `/api/user/*` FastAPI router
- [x] WebSocket `/ws/chat/{session_id}` (streaming)
- [ ] Session memory (Redis-backed)

## Phase 5: Admin Dashboard API
- [x] `/api/admin/*` FastAPI router
- [ ] Price bound rules CRUD (DB-backed)
- [ ] Audit flag review + override (DB-backed)
- [ ] CSV export endpoint
- [ ] SSE job status stream

## Phase 6: MCP Server
- [ ] `app/mcp/server.py` (stdio + SSE transports)
- [ ] All 8 MCP tool handlers
- [ ] `mcp_config.json`

## Phase 7: Testing & Verification
- [x] Pytest setup
- [x] Schema validation unit tests
- [ ] Agent pipeline integration test
- [ ] RAG recall smoke test
