"""
app/api/routers/user.py — End-user REST endpoints.
"""

import uuid
from typing import Any, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from app.agents.mall_graph import mall_graph
from app.agents.state import MallRAGState
from app.cache.redis_client import cache_get, cache_set
from app.config import get_settings

settings = get_settings()
router = APIRouter()


# ── Request / Response Schemas ─────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    session_id: Optional[str] = None


class ProductCard(BaseModel):
    product_id: Optional[str]
    product_name: Optional[str]
    store_name: Optional[str]
    floor: Optional[int]
    unit: Optional[str]
    price_vnd: Optional[float]
    discount_pct: Optional[float]
    image_url: Optional[str]
    is_active_promo: bool = False
    relevance_score: float = 0.0


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    product_cards: list[ProductCard] = []
    follow_up_questions: list[str] = []
    intent: str = "general"


# ── Endpoints ──────────────────────────────────────────────────────────────

@router.post("/chat", response_model=ChatResponse, summary="Send a chat message")
async def chat(req: ChatRequest) -> ChatResponse:
    """
    Non-streaming chat endpoint. Runs the full LangGraph pipeline
    and returns the complete response.
    """
    session_id = req.session_id or str(uuid.uuid4())

    initial_state: MallRAGState = {
        "session_id": session_id,
        "user_id": None,
        "intent": "general",
        "user_query": req.message,
        "extracted_entities": {},
        "retrieved_docs": [],
        "reranked_docs": [],
        "job_id": None,
        "validated_items": [],
        "audit_flags": [],
        "final_response": "",
        "product_cards": [],
        "follow_up_questions": [],
        "messages": [],
        "error": None,
    }

    result = await mall_graph.ainvoke(initial_state)

    return ChatResponse(
        session_id=session_id,
        answer=result.get("final_response", ""),
        product_cards=[ProductCard(**c) for c in result.get("product_cards", [])],
        follow_up_questions=result.get("follow_up_questions", []),
        intent=result.get("intent", "general"),
    )


@router.get("/search", summary="Direct product search with filters")
async def search_products(
    q: str = Query(..., min_length=1, description="Search query"),
    category: Optional[str] = Query(None),
    floor: Optional[int] = Query(None, ge=1, le=10),
    max_price: Optional[float] = Query(None, ge=0),
    min_price: Optional[float] = Query(None, ge=0),
    active_promo_only: bool = Query(False),
    top_k: int = Query(5, ge=1, le=20),
) -> dict[str, Any]:
    """Direct semantic product search with metadata filters."""
    from app.vector.chroma_client import search_vectors
    import httpx

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            f"{settings.embed_base_url}/embeddings",
            json={"input": [q], "model": settings.embed_model},
        )
        resp.raise_for_status()
        vector = resp.json()["data"][0]["embedding"]

    filters: dict[str, Any] = {"is_active": True}
    if category:
        filters["category"] = category
    if floor:
        filters["floor"] = floor
    if active_promo_only:
        filters["is_active_promo"] = True
    price_range: dict[str, float] = {}
    if min_price is not None:
        price_range["gte"] = min_price
    if max_price is not None:
        price_range["lte"] = max_price
    if price_range:
        filters["price_vnd"] = price_range

    results = await search_vectors(vector, filter_conditions=filters, top_k=top_k)
    return {"query": q, "results": results, "count": len(results)}


@router.get("/promotions", summary="List active promotions (date-validated)")
async def get_promotions(
    category: Optional[str] = Query(None),
    floor: Optional[int] = Query(None),
    limit: int = Query(10, ge=1, le=50),
) -> dict[str, Any]:
    """Returns all currently active, date-validated promotions."""
    # TODO: query PostgreSQL for products with active promo date range
    return {"promotions": [], "message": "Endpoint ready — DB query pending Phase 2"}


@router.get("/stores", summary="List all stores")
async def list_stores() -> dict[str, Any]:
    """Returns all mall stores with basic info."""
    return {"stores": [], "message": "Endpoint ready — DB query pending Phase 2"}


@router.get("/stores/{store_id}", summary="Get store detail")
async def get_store(store_id: str) -> dict[str, Any]:
    """Returns detailed info for a specific store."""
    return {"store_id": store_id, "message": "Endpoint ready — DB query pending Phase 2"}
