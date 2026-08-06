"""
app/agents/supervisor.py — Supervisor Agent: intent classification + entity extraction.
Routes state to the correct downstream pipeline node.
"""

import json
import re
from typing import Any

from langchain_openai import ChatOpenAI

from backend.agents.state import MallRAGState
from backend.config import get_settings

settings = get_settings()

_SYSTEM_PROMPT = """
You are the Supervisor of a shopping mall AI assistant.
Your job is to classify the user's intent and extract structured entities.

Possible intents:
- product_search: user is looking for a specific type of product
- store_info: user wants hours, location, or general info about a store
- navigation: user wants to know where something is in the mall (floor, unit)
- promotions: user asks about sales, discounts, or ongoing events
- general: small talk or unclassifiable

Respond ONLY with valid JSON in this exact shape:
{
  "intent": "<one of the intents above>",
  "entities": {
    "product_query": "<extracted product type or null>",
    "store_name": "<store name or null>",
    "category": "<fashion|food|electronics|beauty|kids|sports|other or null>",
    "max_price_vnd": <number or null>,
    "min_price_vnd": <number or null>,
    "floor": <integer or null>,
    "active_promo_only": <true|false>
  }
}
""".strip()


def _build_llm() -> ChatOpenAI:
    return ChatOpenAI(
        base_url=str(settings.llm_base_url),
        api_key=settings.llm_api_key,
        model=settings.llm_model,
        temperature=0.0,   # deterministic for classification
        max_tokens=512,
    )


async def supervisor_node(state: MallRAGState) -> dict[str, Any]:
    """
    LangGraph node: classifies user intent and extracts entities.
    Updates: intent, extracted_entities.
    """
    llm = _build_llm()

    try:
        response = await llm.ainvoke([
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": state["user_query"]},
        ])

        raw = response.content.strip()
        # Strip markdown fences if model wraps in ```json
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.DOTALL)
        parsed = json.loads(raw)

        return {
            "intent": parsed.get("intent", "general"),
            "extracted_entities": parsed.get("entities", {}),
            "error": None,
        }

    except Exception as exc:
        return {
            "intent": "general",
            "extracted_entities": {},
            "error": f"supervisor_error: {exc}",
        }


def route_after_supervisor(state: MallRAGState) -> str:
    """
    Conditional edge: determines next node after supervisor classification.
    Returns the name of the next node in the graph.
    """
    if state.get("error"):
        return "responder"

    intent = state.get("intent", "general")

    if intent in ("product_search", "promotions"):
        return "retriever"
    elif intent in ("store_info", "navigation"):
        return "retriever"
    elif intent == "scrape":
        return "scraper"
    elif intent == "admin_audit":
        return "validator"
    else:
        return "responder"   # general / fallback → direct LLM

