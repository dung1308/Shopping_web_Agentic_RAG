# 🧪 Pytest Suite (`tests/`)

Automated unit and integration test suite covering schemas, extractors, readers, and ingestion agents.

---

## 📁 Test Modules

- [`test_schemas.py`](./test_schemas.py) — Validates Pydantic AI models and product audit compliance logic.
- [`test_extractors.py`](./test_extractors.py) — Unit tests for the Docling document extractor, Playwright HTML extractor, and Hierarchical Chunker.
- [`test_readers.py`](./test_readers.py) — Tests LiteLLM multi-provider document reader and fallback behaviors.
- [`test_ingest_pipeline.py`](./test_ingest_pipeline.py) — Integration tests for document ingestion, validation, and vector indexing.

---

## 🚀 Running Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_schemas.py -v
```
