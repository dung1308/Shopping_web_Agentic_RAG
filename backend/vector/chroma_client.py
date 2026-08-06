"""
backend/vector/chroma_client.py — ChromaDB client + collection bootstrap.

Supports two modes (set via CHROMA_PATH / CHROMA_HOST in .env):
  ./chroma_data      — Embedded local mode, persists to a folder (default/dev)
  http://host:port   — HTTP client mode against a standalone Chroma server

ChromaDB is sync-only; all calls are wrapped with asyncio.to_thread()
to keep the FastAPI event loop non-blocking.
"""

import asyncio
import logging
from typing import Any

import chromadb
from chromadb import Collection
from chromadb.config import Settings as ChromaSettings

from backend.config import get_settings

settings = get_settings()
logger = logging.getLogger("mall_rag.chroma")

_client: chromadb.ClientAPI | None = None


def _make_client() -> chromadb.ClientAPI:
    """Create a ChromaDB client based on config."""
    host = getattr(settings, "chroma_host", "").strip()
    if host:
        # HTTP server mode
        port = getattr(settings, "chroma_port", 8200)
        return chromadb.HttpClient(host=host, port=port)
    else:
        # Embedded persistent mode (default)
        path = getattr(settings, "chroma_path", "./chroma_data")
        return chromadb.PersistentClient(
            path=path,
            settings=ChromaSettings(anonymized_telemetry=False),
        )


async def init_chroma() -> None:
    """Initialise ChromaDB client and ensure collections exist."""
    global _client
    _client = await asyncio.to_thread(_make_client)
    await _ensure_collection()
    await _ensure_documents_collection()
    logger.info("ChromaDB ready ✓")


def get_chroma() -> chromadb.ClientAPI:
    if _client is None:
        raise RuntimeError("ChromaDB not initialised. Call init_chroma() first.")
    return _client


# ── Backward-compat aliases for call sites that use the old names ──────────────
init_qdrant = init_chroma
get_qdrant = get_chroma


async def _ensure_collection() -> None:
    """Create the products collection if it doesn't exist."""
    collection_name = getattr(settings, "chroma_collection", "mall_products")

    def _create():
        client = get_chroma()
        client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    await asyncio.to_thread(_create)


async def _ensure_documents_collection() -> None:
    """Create the mall_documents collection for document chunks if it doesn't exist."""
    from backend.ingest.agents.document_ingester import DOCUMENTS_COLLECTION

    def _create():
        client = get_chroma()
        client.get_or_create_collection(
            name=DOCUMENTS_COLLECTION,
            metadata={"hnsw:space": "cosine"},
        )

    await asyncio.to_thread(_create)


def _get_collection(name: str) -> Collection:
    return get_chroma().get_collection(name=name)


async def upsert_vectors(
    points: list[dict[str, Any]],
    collection_name: str | None = None,
) -> None:
    """
    Upsert a list of points into a ChromaDB collection.
    Each point: { id, vector, payload }

    Args:
        points: List of {id, vector, payload} dicts
        collection_name: Target collection (defaults to chroma_collection from config)
    """
    target = collection_name or getattr(settings, "chroma_collection", "mall_products")

    ids = [str(p["id"]) for p in points]
    embeddings = [p["vector"] for p in points]
    metadatas = [
        # ChromaDB metadata values must be str | int | float | bool — filter None
        {k: v for k, v in p["payload"].items() if v is not None}
        for p in points
    ]

    def _upsert():
        col = get_chroma().get_or_create_collection(
            name=target,
            metadata={"hnsw:space": "cosine"},
        )
        col.upsert(ids=ids, embeddings=embeddings, metadatas=metadatas)

    await asyncio.to_thread(_upsert)


async def search_vectors(
    query_vector: list[float],
    filter_conditions: dict | None = None,
    top_k: int = 10,
    collection_name: str | None = None,
) -> list[dict[str, Any]]:
    """Dense vector search with optional metadata filter."""
    target = collection_name or getattr(settings, "chroma_collection", "mall_products")
    where = _build_where(filter_conditions) if filter_conditions else None

    def _query():
        col = get_chroma().get_or_create_collection(
            name=target,
            metadata={"hnsw:space": "cosine"},
        )
        kwargs: dict[str, Any] = {
            "query_embeddings": [query_vector],
            "n_results": top_k,
            "include": ["metadatas", "distances"],
        }
        if where:
            kwargs["where"] = where
        return col.query(**kwargs)

    results = await asyncio.to_thread(_query)

    output: list[dict[str, Any]] = []
    ids = results.get("ids", [[]])[0]
    distances = results.get("distances", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]

    for doc_id, dist, meta in zip(ids, distances, metadatas):
        # ChromaDB returns L2 distances for cosine space (after normalisation).
        # Convert to a similarity score in [0, 1] range: score = 1 - distance/2
        score = max(0.0, 1.0 - dist / 2.0)
        output.append({"id": doc_id, "score": score, "payload": meta or {}})

    return output


def _build_where(conditions: dict) -> dict | None:
    """Convert a flat filter dict into a ChromaDB `where` clause."""
    clauses: list[dict] = []

    for key, value in conditions.items():
        if isinstance(value, bool):
            clauses.append({key: {"$eq": value}})
        elif isinstance(value, str):
            clauses.append({key: {"$eq": value}})
        elif isinstance(value, (int, float)):
            clauses.append({key: {"$eq": value}})
        elif isinstance(value, dict):
            # Range filter: {"gte": x, "lte": y}
            range_clause: dict = {}
            if "gte" in value:
                range_clause["$gte"] = value["gte"]
            if "lte" in value:
                range_clause["$lte"] = value["lte"]
            if range_clause:
                clauses.append({key: range_clause})

    if not clauses:
        return None
    if len(clauses) == 1:
        return clauses[0]
    return {"$and": clauses}
