"""
app/agents/state.py — LangGraph shared state schema for the mall RAG graph.
"""

from typing import Annotated, Any, Literal, Optional
from uuid import UUID

from langchain_core.documents import Document
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

from backend.schemas.validation import AuditFlag, ValidationResult


class MallRAGState(TypedDict):
    """
    Shared state flowing through the LangGraph StateGraph.
    Each agent reads and writes to this dict; edges are driven
    by the 'intent' and 'error' fields.
    """

    # ── Session ────────────────────────────────────────────────────────────
    session_id: str
    user_id: Optional[str]               # None for anonymous users

    # ── Routing ────────────────────────────────────────────────────────────
    intent: Literal[
        "product_search",
        "store_info",
        "navigation",
        "promotions",
        "scrape",
        "admin_audit",
        "general",
    ]

    # ── User Input ─────────────────────────────────────────────────────────
    user_query: str
    extracted_entities: dict[str, Any]   # price, category, floor, etc.

    # ── Retrieval ──────────────────────────────────────────────────────────
    retrieved_docs: list[Document]
    reranked_docs: list[Document]

    # ── Scrape / Ingest ────────────────────────────────────────────────────
    job_id: Optional[str]
    validated_items: list[ValidationResult]
    audit_flags: list[AuditFlag]

    # ── Generation ─────────────────────────────────────────────────────────
    final_response: str
    product_cards: list[dict[str, Any]]
    follow_up_questions: list[str]

    # ── Conversation history (append-only via LangGraph reducer) ───────────
    messages: Annotated[list, add_messages]

    # ── Error handling ─────────────────────────────────────────────────────
    error: Optional[str]

