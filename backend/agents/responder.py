"""
app/agents/responder.py — Responder Agent: LLM generation with retrieved context.
Supports both streaming (WebSocket) and batch (REST) response modes.
"""

import json
from typing import Any, AsyncIterator

from langchain_core.documents import Document
from langchain_openai import ChatOpenAI

from backend.agents.state import MallRAGState
from backend.config import get_settings

settings = get_settings()

_SYSTEM_PROMPT = """
You are MallBot, a helpful shopping assistant for a Vietnamese shopping mall.
Answer in the same language the user used (Vietnamese or English).
Be concise, friendly, and specific. Always mention the store name and floor when recommending products.

When you have product data, format your response to include:
1. A short answer to the user's question
2. Specific product/store recommendations with prices

If you don't have relevant data, say so honestly and suggest the user visit the information desk.
"""


def _build_llm(streaming: bool = False) -> ChatOpenAI:
    return ChatOpenAI(
        base_url=str(settings.llm_base_url),
        api_key=settings.llm_api_key,
        model=settings.llm_model,
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens,
        streaming=streaming,
    )


def _format_context(docs: list[Document]) -> str:
    if not docs:
        return "No specific product data found for this query."

    lines = ["### Available Products:\n"]
    for i, doc in enumerate(docs[:5], 1):
        m = doc.metadata
        lines.append(
            f"{i}. **{m.get('product_name', 'Unknown')}** — "
            f"Store: {m.get('store_name', '?')} (Floor {m.get('floor', '?')}) — "
            f"Price: {int(m.get('price_vnd', 0)):,} VND"
            + (f" (Sale: {int(m.get('discount_pct', 0)*100)}% off)" if m.get('discount_pct') else "")
        )
    return "\n".join(lines)


def _extract_product_cards(docs: list[Document]) -> list[dict[str, Any]]:
    cards = []
    for doc in docs[:5]:
        m = doc.metadata
        cards.append({
            "product_id": m.get("product_id"),
            "product_name": m.get("product_name"),
            "store_name": m.get("store_name"),
            "store_id": m.get("store_id"),
            "floor": m.get("floor"),
            "unit": m.get("unit"),
            "price_vnd": m.get("price_vnd"),
            "discount_pct": m.get("discount_pct"),
            "image_url": m.get("image_url"),
            "is_active_promo": m.get("is_active_promo", False),
            "relevance_score": round(m.get("_score", 0.0), 4),
        })
    return cards


async def responder_node(state: MallRAGState) -> dict[str, Any]:
    """
    LangGraph node: generates a natural language response using LLM + retrieved docs.
    Updates: final_response, product_cards, follow_up_questions.
    """
    llm = _build_llm(streaming=False)
    reranked = state.get("reranked_docs") or state.get("retrieved_docs", [])
    context = _format_context(reranked)

    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
    ]

    # Inject conversation history (last 6 turns)
    for msg in state.get("messages", [])[-6:]:
        if hasattr(msg, "type"):
            role = "assistant" if msg.type == "ai" else "user"
            messages.append({"role": role, "content": msg.content})

    messages.append({
        "role": "user",
        "content": (
            f"User query: {state['user_query']}\n\n"
            f"{context}\n\n"
            "Please answer the user's query based on the product data above. "
            "Also suggest 2-3 natural follow-up questions the user might ask."
            "Return a JSON object: {\"answer\": \"...\", \"follow_ups\": [\"...\", ...]}"
        ),
    })

    try:
        import re
        response = await llm.ainvoke(messages)
        raw = response.content.strip()
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.DOTALL)

        parsed = json.loads(raw)
        answer = parsed.get("answer", raw)
        follow_ups = parsed.get("follow_ups", [])
    except Exception:
        answer = raw if 'raw' in dir() else "I'm having trouble processing your request right now."
        follow_ups = []

    return {
        "final_response": answer,
        "product_cards": _extract_product_cards(reranked),
        "follow_up_questions": follow_ups[:3],
        "error": None,
    }


async def responder_stream(state: MallRAGState) -> AsyncIterator[str]:
    """
    Streaming variant: yields token chunks for WebSocket delivery.
    Does NOT update state — call responder_node for state update.
    """
    llm = _build_llm(streaming=True)
    reranked = state.get("reranked_docs") or state.get("retrieved_docs", [])
    context = _format_context(reranked)

    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"User query: {state['user_query']}\n\n{context}",
        },
    ]

    async for chunk in llm.astream(messages):
        if chunk.content:
            yield chunk.content

