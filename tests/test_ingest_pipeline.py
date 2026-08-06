"""
tests/test_ingest_pipeline.py — Integration test for the ingestion pipeline.
Tests Scraper -> Validator -> Indexer flow end-to-end.
"""

import uuid
from decimal import Decimal

import pytest

from backend.db.models import StoreCategory
from backend.ingest.agents.scraper import scrape_store_products
from backend.ingest.agents.validator import validate_scraped_items
from backend.ingest.agents.indexer import index_validated_products


@pytest.mark.asyncio
async def test_full_ingestion_pipeline():
    job_id = str(uuid.uuid4())
    store_id = str(uuid.uuid4())
    store_url = "https://example-store.com/products"

    # Step 1: Scrape
    raw_items = await scrape_store_products(store_id=store_id, store_url=store_url)
    assert len(raw_items) > 0, "Scraper should return raw items"

    # Step 2: Validate
    val_results = await validate_scraped_items(job_id=job_id, store_id=store_id, raw_items=raw_items)
    assert len(val_results) == len(raw_items), "Validator should return result for each raw item"

    valid_products = [r.validated_product for r in val_results if r.is_valid and r.validated_product]
    assert len(valid_products) > 0, "Should have at least one valid product model"
    assert valid_products[0].price_vnd > Decimal("0")

    # Step 3: Index
    indexed_count = await index_validated_products(valid_products, store_name="Test Store", floor=2)
    assert indexed_count == len(valid_products), "Indexer should return count matching valid products"

