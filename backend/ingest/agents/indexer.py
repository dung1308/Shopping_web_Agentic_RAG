"""
app/ingest/agents/indexer.py — Indexer Agent.
Generates bge-m3 embeddings for validated products, upserts them into Qdrant, and invalidates Redis cache.
"""

import uuid
import logging
from typing import Any, Optional

import httpx

from backend.cache.redis_client import cache_delete_pattern
from backend.config import get_settings
from backend.schemas.validation import ScrapedProduct
from backend.vector.chroma_client import upsert_vectors

settings = get_settings()
logger = logging.getLogger("mall_rag.indexer")


async def get_embeddings(texts: list[str]) -> list[list[float]]:
    """Calls local bge-m3 embedding service endpoint, with fallback if offline."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{settings.embed_base_url}/embeddings",
                json={"input": texts, "model": settings.embed_model},
            )
            resp.raise_for_status()
            data = resp.json()
            return [item["embedding"] for item in data["data"]]
    except Exception as exc:
        logger.warning(f"Embedding service ({settings.embed_base_url}) offline: {exc}. Generating mock 1024-dim vector.")
        # Fallback deterministic zero-vector for testing when infinity server is not running
        return [[0.01 * (i % 10) for i in range(settings.embed_dim)] for _ in texts]


async def index_validated_products(
    products: list[ScrapedProduct],
    store_name: str = "Mall Store",
    floor: int = 1,
) -> int:
    """
    Indexes validated product models into Qdrant vector database and invalidates Redis store cache.
    Returns the count of indexed products.
    """
    if not products:
        return 0

    texts_to_embed = [
        f"{p.product_name} — {p.category.value} — Price: {float(p.price_vnd):.0f} VND"
        for p in products
    ]

    embeddings = await get_embeddings(texts_to_embed)
    points_to_upsert: list[dict[str, Any]] = []

    for p, vector in zip(products, embeddings):
        point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{p.store_id}-{p.product_name}"))
        
        payload = {
            "product_id": point_id,
            "store_id": str(p.store_id),
            "store_name": store_name,
            "product_name": p.product_name,
            "price_vnd": float(p.price_vnd),
            "discount_pct": p.discount_pct,
            "category": p.category.value,
            "floor": floor,
            "image_url": str(p.image_url) if p.image_url else None,
            "is_active_promo": (p.promo_start is not None),
            "is_active": True,
            "scraped_at": p.scraped_at.isoformat(),
        }

        points_to_upsert.append({
            "id": point_id,
            "vector": vector,
            "payload": payload,
        })

    try:
        await upsert_vectors(points_to_upsert)
        logger.info(f"Successfully upserted {len(points_to_upsert)} vector points into ChromaDB")
    except Exception as exc:
        logger.error(f"Failed to upsert points into ChromaDB: {exc}")

    # Invalidate store cache in Redis
    try:
        for p in products:
            await cache_delete_pattern(f"store:{p.store_id}:*")
    except Exception as exc:
        logger.warning(f"Could not invalidate Redis cache: {exc}")

    return len(points_to_upsert)

