"""
app/api/websocket.py — WebSocket endpoint for streaming chat responses.
"""

import json
import uuid
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.agents.mall_graph import mall_graph
from backend.agents.responder import responder_stream
from backend.agents.state import MallRAGState
from backend.agents.supervisor import supervisor_node
from backend.agents.retriever import retriever_node

chat_ws_router = APIRouter()
router = chat_ws_router


@chat_ws_router.websocket("/ws/chat/{session_id}")
async def websocket_chat(websocket: WebSocket, session_id: str) -> None:
    """
    Streaming chat WebSocket.
    Protocol:
      Client → server: { "message": "user text" }
      Server → client (streamed tokens): { "type": "token", "content": "..." }
      Server → client (final): { "type": "done", "product_cards": [...], "follow_ups": [...] }
      Server → client (error): { "type": "error", "detail": "..." }
    """
    await websocket.accept()

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
                user_message = data.get("message", "").strip()
                if not user_message:
                    await websocket.send_json({"type": "error", "detail": "Empty message"})
                    continue
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "detail": "Invalid JSON"})
                continue

            # Build initial state
            state: MallRAGState = {
                "session_id": session_id,
                "user_id": None,
                "intent": "general",
                "user_query": user_message,
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

            # Step 1: Supervisor (intent + entities)
            supervisor_result = await supervisor_node(state)
            state.update(supervisor_result)

            # Step 2: Retriever (if search intent)
            if state["intent"] in ("product_search", "promotions", "store_info", "navigation"):
                retriever_result = await retriever_node(state)
                state.update(retriever_result)

            # Step 3: Stream responder tokens
            try:
                async for token in responder_stream(state):
                    await websocket.send_json({"type": "token", "content": token})
            except Exception as stream_err:
                await websocket.send_json({
                    "type": "error",
                    "detail": f"Streaming error: {stream_err}",
                })
                continue

            # Step 4: Send product cards + follow-ups
            from backend.agents.responder import _extract_product_cards
            product_cards = _extract_product_cards(
                state.get("reranked_docs") or state.get("retrieved_docs", [])
            )
            await websocket.send_json({
                "type": "done",
                "product_cards": product_cards,
                "follow_ups": state.get("follow_up_questions", []),
                "intent": state.get("intent", "general"),
            })

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        try:
            await websocket.send_json({"type": "error", "detail": str(exc)})
        except Exception:
            pass

