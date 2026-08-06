"""
app/agents/retriever.py — Retriever Agent: hybrid dense + sparse search.
"""

from typing import Any

import httpx
from langchain_core.documents import Document

from app.agents.state import MallRAGState
from app.config import get_settings
from app.vector.chroma_client import search_vectors

settings = get_settings()


async def _embed(text: str) -> list[float]:
    """Call the local bge-m3 embedding endpoint."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{settings.embed_base_url}/embeddings",
            json={"input": [text], "model": settings.embed_model},
        )
        resp.raise_for_status()
        return resp.json()["data"][0]["embedding"]


def _build_filter(entities: dict[str, Any]) -> dict[str, Any]:
    """Convert extracted entities into a Qdrant metadata filter dict."""
    conditions: dict[str, Any] = {"is_active": True}

    if entities.get("category"):
        conditions["category"] = entities["category"]

    if entities.get("floor"):
        conditions["floor"] = entities["floor"]

    if entities.get("active_promo_only"):
        conditions["is_active_promo"] = True

    # Price range
    price_range: dict[str, float] = {}
    if entities.get("min_price_vnd"):
        price_range["gte"] = float(entities["min_price_vnd"])
    if entities.get("max_price_vnd"):
        price_range["lte"] = float(entities["max_price_vnd"])
    if price_range:
        conditions["price_vnd"] = price_range

    return conditions


async def retriever_node(state: MallRAGState) -> dict[str, Any]:
    """
    LangGraph node: performs hybrid semantic + metadata-filtered search.
    Updates: retrieved_docs.
    """
    query = state["user_query"]
    entities = state.get("extracted_entities", {})

    try:
        # 1. Dense vector search
        query_vector = await _embed(query)
        filter_conditions = _build_filter(entities)
        raw_results = await search_vectors(
            query_vector=query_vector,
            filter_conditions=filter_conditions,
            top_k=10,
        )

        # 2. Convert to LangChain Documents
        docs: list[Document] = []
        for r in raw_results:
            payload = r.get("payload", {})
            doc = Document(
                page_content=(
                    f"{payload.get('product_name', '')} — "
                    f"{payload.get('store_name', '')} — "
                    f"{payload.get('price_vnd', '')} VND"
                ),
                metadata={
                    **payload,
                    "_score": r["score"],
                    "_id": r["id"],
                },
            )
            docs.append(doc)

        return {"retrieved_docs": docs, "error": None}

    except Exception as exc:
        return {
            "retrieved_docs": [],
            "error": f"retriever_error: {exc}",
        }
