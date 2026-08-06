# 🧪 07 — Development Guide

> Everything for day-to-day development: testing, CLI, running the server, adding new features.

---

## Running the Server

```bash
# Start the bridge (FastAPI)
uvicorn bridge.main:app --host 127.0.0.1 --port 8000 --reload

# Or use the CLI entry point (after pip install -e .)
mall-serve

# Open API docs in browser:
# http://127.0.0.1:8000/docs       ← REST (Swagger UI)
# http://127.0.0.1:8000/redoc      ← REST (ReDoc)
# http://127.0.0.1:8000/graphql    ← GraphQL playground (when enabled)
```

---

## Database Migrations (Alembic)

```bash
# Apply all migrations
python -m alembic upgrade head

# Create a new migration after changing backend/db/models.py
python -m alembic revision --autogenerate -m "add_column_xyz"

# Roll back one step
python -m alembic downgrade -1

# See migration history
python -m alembic history
```

---

## CLI Commands

### Ingestion

```bash
# Ingest a local PDF (CPU, local LLM)
mall-ingest ingest-file \
    --file catalog.pdf \
    --store-id "550e8400-e29b-41d4-a716-446655440000" \
    --store-name "Zara" \
    --floor 2

# Ingest with structured extraction via Gemini
mall-ingest ingest-file \
    --file products.pdf \
    --store-id <uuid> \
    --provider gemini \
    --task extract_structured

# Capture a JS-rendered web page
mall-ingest ingest-url \
    --url "https://shop.example.com/products" \
    --store-id <uuid> \
    --mode auto

# Ingest DOCX and enrich metadata
mall-ingest ingest-file \
    --file manual.docx \
    --store-id <uuid> \
    --provider local \
    --task enrich

# Skip LLM, fastest
mall-ingest ingest-file --file data.json --store-id <uuid> --provider none

# List available providers
mall-ingest list-providers-cmd
```

### Scrape pipeline

```bash
# Full scrape → validate → index pipeline
mall-ingest pipeline \
    --store-id <uuid> \
    --url "https://store.com" \
    --store-name "Nike" \
    --floor 1
```

### Model utilities

```bash
# Download bge-m3 model weights
python scripts/download_model.py

# Check LLM connection
python scripts/check_llm_connection.py
```

---

## Running Tests

```bash
# Full test suite
python -m pytest tests/ -v

# Only extractor tests
python -m pytest tests/test_extractors.py -v

# Only reader tests
python -m pytest tests/test_readers.py -v

# Only schema/validation tests
python -m pytest tests/test_schemas.py -v

# Show test coverage
python -m pytest tests/ --cov=backend --cov-report=term-missing

# Run fast (skip slow integration tests)
python -m pytest tests/ -v -m "not slow"
```

Expected output:
```
33 passed in 0.52s
```

---

## Project Structure at a Glance

```
portfolio/
├── guidelines/          ← READ FIRST — all documentation
├── frontend/
│   ├── web/             ← HTML + JS pages (browser)
│   └── desktop/         ← Python Tkinter GUI
├── bridge/              ← FastAPI app (HTTP connection layer)
│   ├── main.py          ← Server entry point
│   ├── api/routers/     ← REST routes
│   └── mcp/             ← MCP tools
├── backend/             ← Business logic (no HTTP knowledge)
│   ├── config.py
│   ├── agents/          ← LangGraph RAG pipeline
│   ├── db/              ← SQLAlchemy models
│   ├── cache/           ← Redis
│   ├── vector/          ← Qdrant client
│   ├── schemas/         ← Pydantic validation
│   └── ingest/          ← Docling + Playwright pipeline
├── alembic/             ← DB migrations
├── models/              ← Local LLM weights (Phi-3.5.gguf)
├── scripts/             ← Utility scripts
├── tests/               ← Pytest suite
├── docker-compose.yml
├── pyproject.toml
└── .env
```

---

## Adding a New Feature

### New backend capability (e.g., product recommender)
1. Add business logic in `backend/agents/recommender.py`
2. Write tests in `tests/test_recommender.py`
3. Run tests: `pytest tests/test_recommender.py -v`

### New API endpoint (e.g., GET /api/user/recommendations)
1. Add route in `bridge/api/routers/user.py`
2. Call your backend function from the route handler
3. Test via `http://localhost:8000/docs`

### New GraphQL query (when GraphQL is enabled)
1. Add a resolver method to `bridge/api/graphql.py`
2. Test via `http://localhost:8000/graphql` (GraphiQL playground)

### New database table
1. Add model to `backend/db/models.py`
2. Run: `python -m alembic revision --autogenerate -m "add_table"`
3. Run: `python -m alembic upgrade head`

### New ingest format
1. Add handler in `backend/ingest/extractors/docling_extractor.py`
2. Add test in `tests/test_extractors.py`

---

## Code Style

```bash
# Lint + format check (Ruff)
python -m ruff check .
python -m ruff format .

# Type check (mypy — optional)
python -m mypy backend/ --ignore-missing-imports
```

---

## Docker

```bash
# Start all services (Qdrant, Redis, Infinity)
docker-compose up -d

# View logs
docker-compose logs -f

# Stop everything
docker-compose down

# Rebuild after dependency changes
docker-compose build --no-cache
```
