"""
bridge/main.py — FastAPI application factory (the bridge layer).

This is the entry point for the web server. It wires together:
  - backend/* (business logic: agents, db, vector, cache, ingest)
  - bridge/api/* (REST routers + WebSocket)
  - bridge/mcp/* (MCP server)

Run with:
  uvicorn bridge.main:app --host 0.0.0.0 --port 8000
  # or via CLI entry point:
  mall-serve
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

import uvicorn
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.config import get_settings
from bridge.api.routers import admin, ingest, user
from bridge.api.websocket import router as ws_router

settings = get_settings()
logger = logging.getLogger("mall_rag.bridge")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle for the bridge server."""
    logger.info("Bridge starting up — initialising services...")

    # Initialise ChromaDB collections (products + documents)
    try:
        from backend.vector.chroma_client import init_chroma
        await init_chroma()
        logger.info("ChromaDB ready ✓")
    except Exception as exc:
        logger.warning(f"ChromaDB unavailable at startup: {exc}")

    # Initialise Redis connection
    try:
        from backend.cache.redis_client import get_redis
        await get_redis()
        logger.info("Redis ready ✓")
    except Exception as exc:
        logger.warning(f"Redis unavailable at startup: {exc}")

    yield

    logger.info("Bridge shutting down...")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Mall RAG — Bridge API",
        description=(
            "The bridge layer connecting backend AI agents to frontend clients. "
            "Exposes REST endpoints, WebSocket chat streaming, and MCP tools."
        ),
        version="2.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # CORS — allow all origins in dev
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.is_dev else ["https://your-domain.com"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── REST Routers ────────────────────────────────────────────────────────
    app.include_router(user.router,   prefix="/api/user",   tags=["Shopper"])
    app.include_router(admin.router,  prefix="/api/admin",  tags=["Admin"])
    app.include_router(ingest.router, prefix="/api/ingest", tags=["Ingest"])

    # ── WebSocket / SSE ─────────────────────────────────────────────────────
    app.include_router(ws_router, tags=["Streaming"])

    @app.get("/health", tags=["Health"])
    async def health():
        return {"status": "ok", "version": "2.0.0", "env": settings.app_env}

    # ── Static Web Frontend Pages ───────────────────────────────────────────
    web_dir = Path("web_frontend") if Path("web_frontend").exists() else Path("frontend/web")
    if web_dir.exists():
        app.mount("/", StaticFiles(directory=str(web_dir), html=True), name="static")

    return app


app = create_app()


def start():
    """Entry point for `mall-serve` CLI command."""
    uvicorn.run(
        "bridge.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.is_dev,
        log_level="info",
    )


if __name__ == "__main__":
    start()
