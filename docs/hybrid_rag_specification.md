# 🛒 Hybrid RAG Method Specification & Router Agent Architecture

## 1. Executive Summary

This document specifies the **Hybrid RAG (Retrieval-Augmented Generation)** strategy for the **Shopping Mall Agentic RAG System**. It divides retrieval, scraping, and reasoning tasks into two distinct buckets:
- **Local RAG Methods (Offline / In-House)**: Ultra-low latency, zero per-query API costs, strict privacy.
- **API-Based RAG Methods (Cloud / External)**: High-capacity external scraping, web-wide deal discovery, and cloud LLM fallback.

---

## 2. Hybrid RAG Method Comparison Matrix

| Component | Chosen Method / Tool | Type | Latency & Cost Impact | Trigger Condition (Local ➔ API Switch) |
| :--- | :--- | :--- | :--- | :--- |
| **Vector DB & Storage** | **Primary:** Local Qdrant / PostgreSQL (`pgvector`)<br>**Fallback:** External Search API | **Local** *(Primary)*<br>➔ **API** *(Fallback)* | **Local:** Low Latency (~10–30 ms), $0 API Cost.<br>**API:** Med Latency (~150–400 ms), ~$0.001 / query. | **1.** Similarity score $\le 0.65$ across top-k vector results.<br>**2.** Empty payload match for requested product category.<br>**3.** Local vector store service timeout (> 500 ms). |
| **Embedding Model** | **Primary:** Local `BAAI/bge-m3` or `bge-small-en-v1.5` via SentenceTransformers / Ollama<br>**Fallback:** OpenAI `text-embedding-3-small` | **Local** *(Primary)*<br>➔ **API** *(Fallback)* | **Local:** Fast (~15–35 ms batch), CPU/GPU bounded.<br>**API:** Med Latency (~100–250 ms), ~$0.02 / 1M tokens. | **1.** High-concurrency queue saturation (> 50 requests).<br>**2.** Local embedding service daemon offline/OOM.<br>**3.** Cross-lingual re-ranking edge cases requiring cloud APIs. |
| **Mall Directory & Spatial Search** | **Primary:** PostgreSQL Static Spatial Table & Redis Cache (layouts, store hours, floor plans)<br>**Fallback:** External Geolocation / Maps API | **Local** *(Primary)*<br>➔ **API** *(Fallback)* | **Local:** Sub-5 ms, $0 API Cost.<br>**API:** Med Latency (~200–500 ms), ~$0.005 / lookup. | **1.** Query requests off-site transit/navigation info.<br>**2.** Spatial lookup failure in internal floor plan DB.<br>**3.** Temporary external mall event location. |
| **Product & Deal Scraping** | **Primary:** In-House Playwright Chromium Scraper with `robots.txt` compliance<br>**Fallback:** Cloud Scraper API (Firecrawl / Tavily API) | **Local** *(Primary)*<br>➔ **API** *(Fallback)* | **Local:** Med-High Latency (~2–5 s/page), Heavy CPU/RAM, $0 API Cost.<br>**API:** Fast (~1–2 s), Managed proxies, ~$0.002–$0.01 / scrape. | **1.** Anti-bot block (Cloudflare 403 / CAPTCHA).<br>**2.** Dynamic SPA JavaScript render failure on Playwright.<br>**3.** Real-time web-wide deal hunting outside mall domain allowlist. |
| **Reasoning & Validation Engine** | **Primary:** Local Ollama / vLLM (Llama 3.1 8B / Qwen 2.5 7B) + Pydantic AI<br>**Fallback:** External LLM (GPT-4o / Claude 3.5 Sonnet / Gemini 1.5 Pro) | **Local** *(Primary)*<br>➔ **API** *(Fallback)* | **Local:** Variable Latency (~200–800 ms TTFT), $0 Token Cost.<br>**API:** Med Latency (~400–1200 ms), ~$0.0025–$0.01 / request. | **1.** Pydantic schema validation failure after 2 retries.<br>**2.** Multi-constraint admin audit reconciliation.<br>**3.** User requests deep comparative shopping analysis. |

---

## 3. Router Agent Implementation Logic

### Pydantic Schemas & LangGraph Routing Logic (`app/agents/hybrid_router.py`)

```python
"""
app/agents/hybrid_router.py — Local-First with API Fallback Router Agent.

Routing Workflow:
1. Step 1 (Local Check): Query local Vector DB for stored directories, products, or floor maps.
2. Step 2 (Evaluation): If vector similarity score > 0.85 AND data age < 7 days, return local result directly.
3. Step 3 (API Escalation): If local data missing, low confidence, or query demands live pricing, escalate to external Web Scraping / Search API.
4. Step 4 (Admin Logging): Log decision (LOCAL_DB vs EXTERNAL_API) into AdminAuditLog schema.
"""

from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Annotated, Any, Optional
from pydantic import BaseModel, Field
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages

# ----------------------------------------------------------------------------
# 1. Pydantic Schemas & Data Models
# ----------------------------------------------------------------------------

class RetrievalSource(str, Enum):
    LOCAL_DB = "LOCAL_DB"
    EXTERNAL_API = "EXTERNAL_API"


class VectorSearchResult(BaseModel):
    """Payload format returned from local Vector DB query."""
    document_id: str
    content: str
    similarity_score: float = Field(..., ge=0.0, le=1.0)
    created_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def age_in_days(self) -> float:
        """Calculate age of document in fractional days."""
        now = datetime.now(timezone.utc)
        doc_time = self.created_at if self.created_at.tzinfo else self.created_at.replace(tzinfo=timezone.utc)
        return (now - doc_time).total_seconds() / 86400.0


class AdminAuditLog(BaseModel):
    """Schema for audit logging retrieval source and routing rationale."""
    log_id: str
    session_id: str
    user_query: str
    retrieval_source: RetrievalSource
    similarity_score: Optional[float] = None
    data_age_days: Optional[float] = None
    escalation_reason: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ----------------------------------------------------------------------------
# 2. LangGraph State Model
# ----------------------------------------------------------------------------

class HybridRAGState(TypedDict):
    session_id: str
    user_query: str
    local_search_result: Optional[dict[str, Any]]
    retrieval_source: Optional[RetrievalSource]
    similarity_score: float
    data_age_days: float
    escalation_reason: Optional[str]
    retrieved_context: str
    audit_logs: list[dict[str, Any]]
    messages: Annotated[list, add_messages]


# ----------------------------------------------------------------------------
# 3. Keyphrase Detector for Explicit Live Requests
# ----------------------------------------------------------------------------

LIVE_PRICING_KEYWORDS = [
    "right now", "live pricing", "real time", "flash sale", 
    "today discount", "where to buy cheap", "current deal"
]

def is_explicit_live_query(query: str) -> bool:
    q_lower = query.lower()
    return any(kw in q_lower for kw in LIVE_PRICING_KEYWORDS)


# ----------------------------------------------------------------------------
# 4. Router Agent Evaluation Node (Steps 1, 2, 3 & 4)
# ----------------------------------------------------------------------------

async def router_evaluation_node(state: HybridRAGState) -> dict[str, Any]:
    user_query = state["user_query"]
    session_id = state.get("session_id", "anon_session")
    local_data = state.get("local_search_result")

    source = RetrievalSource.LOCAL_DB
    escalation_reason = None
    score = 0.0
    age_days = 999.0

    if local_data:
        res = VectorSearchResult(**local_data)
        score = res.similarity_score
        age_days = res.age_in_days

        is_high_confidence = score > 0.85
        is_fresh = age_days < 7.0
        is_live_req = is_explicit_live_query(user_query)

        if is_live_req:
            source = RetrievalSource.EXTERNAL_API
            escalation_reason = "Explicit live pricing request detected in query."
        elif not is_high_confidence:
            source = RetrievalSource.EXTERNAL_API
            escalation_reason = f"Low similarity score ({score:.2f} <= 0.85 threshold)."
        elif not is_fresh:
            source = RetrievalSource.EXTERNAL_API
            escalation_reason = f"Stale local context ({age_days:.1f} days old >= 7.0 threshold)."
    else:
        source = RetrievalSource.EXTERNAL_API
        escalation_reason = "No local Vector DB result found."

    audit_entry = AdminAuditLog(
        log_id=f"log_{int(datetime.now(timezone.utc).timestamp())}",
        session_id=session_id,
        user_query=user_query,
        retrieval_source=source,
        similarity_score=score,
        data_age_days=age_days,
        escalation_reason=escalation_reason
    )

    return {
        "retrieval_source": source,
        "similarity_score": score,
        "data_age_days": age_days,
        "escalation_reason": escalation_reason,
        "audit_logs": [audit_entry.model_dump()],
    }


# ----------------------------------------------------------------------------
# 5. Conditional Edge Router
# ----------------------------------------------------------------------------

def route_by_retrieval_source(state: HybridRAGState) -> str:
    """Conditional Edge function driving graph flow."""
    if state.get("retrieval_source") == RetrievalSource.LOCAL_DB:
        return "local_retriever"
    return "api_scraper"
```

---

## 4. Verification Matrix

| Test Case | Inputs | Expected `retrieval_source` | Reason |
| :--- | :--- | :--- | :--- |
| **Case 1: Fresh Local Data** | Query: "Floor 2 restrooms", Score: 0.94, Age: 1 day | `LOCAL_DB` | Passes score (>0.85) & freshness (<7d). |
| **Case 2: Stale Local Data** | Query: "Shoe sale", Score: 0.91, Age: 12 days | `EXTERNAL_API` | Fails freshness (12d >= 7d). |
| **Case 3: Low Confidence** | Query: "Obscure item", Score: 0.62, Age: 2 days | `EXTERNAL_API` | Fails confidence score (0.62 <= 0.85). |
| **Case 4: Live Query** | Query: "where to buy a cheap handkerchief right now", Score: 0.95, Age: 0.5 days | `EXTERNAL_API` | Triggered by live keyphrase 'right now'. |
