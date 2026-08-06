"""
app/agents/mall_graph.py — LangGraph StateGraph wiring: assembles all agent nodes.
"""

from langgraph.graph import END, START, StateGraph

from backend.agents.state import MallRAGState
from backend.agents.supervisor import route_after_supervisor, supervisor_node
from backend.agents.retriever import retriever_node
from backend.agents.responder import responder_node


async def _noop_scraper(state: MallRAGState) -> dict:
    """Placeholder: full scraper agent is in app/ingest/agents/scraper.py"""
    return {"error": "Scraper agent invoked from graph — trigger via /api/ingest instead"}


async def _noop_validator(state: MallRAGState) -> dict:
    """Placeholder: validator is in app/ingest/agents/validator.py"""
    return {"error": None}


def build_graph() -> StateGraph:
    """Construct and compile the mall RAG LangGraph StateGraph."""
    graph = StateGraph(MallRAGState)

    # ── Add nodes ─────────────────────────────────────────────────────────
    graph.add_node("supervisor", supervisor_node)
    graph.add_node("retriever", retriever_node)
    graph.add_node("scraper", _noop_scraper)
    graph.add_node("validator", _noop_validator)
    graph.add_node("responder", responder_node)

    # ── Entry point ───────────────────────────────────────────────────────
    graph.add_edge(START, "supervisor")

    # ── Conditional routing after supervisor ──────────────────────────────
    graph.add_conditional_edges(
        "supervisor",
        route_after_supervisor,
        {
            "retriever": "retriever",
            "scraper": "scraper",
            "validator": "validator",
            "responder": "responder",
        },
    )

    # ── Retriever always flows to responder ───────────────────────────────
    graph.add_edge("retriever", "responder")

    # ── Scraper / validator end the pipeline (async jobs) ─────────────────
    graph.add_edge("scraper", END)
    graph.add_edge("validator", END)

    # ── Responder ends the graph ──────────────────────────────────────────
    graph.add_edge("responder", END)

    return graph.compile()


# Compiled graph singleton (import this in routers)
mall_graph = build_graph()

