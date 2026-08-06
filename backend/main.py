"""
app/main.py — FastAPI application entry point.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from backend.config import get_settings
from backend.db.session import init_db
from backend.cache.redis_client import init_redis, close_redis
from backend.vector.chroma_client import init_chroma
from backend.api.routers import user, admin, ingest
from backend.api.websocket import chat_ws_router

import logging

settings = get_settings()
logger = logging.getLogger("mall_rag")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle hooks with graceful dev degradation."""
    # Startup
    try:
        await init_db()
    except Exception as exc:
        logger.warning(f"PostgreSQL connection failed during startup: {exc}")
        if not settings.is_dev:
            raise

    try:
        await init_redis()
    except Exception as exc:
        logger.warning(f"Redis connection failed during startup: {exc}")
        if not settings.is_dev:
            raise

    try:
        await init_chroma()
    except Exception as exc:
        logger.warning(f"ChromaDB initialisation failed during startup: {exc}")
        if not settings.is_dev:
            raise

    yield

    # Shutdown
    try:
        await close_redis()
    except Exception as exc:
        logger.warning(f"Redis close error: {exc}")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Mall Agentic RAG API",
        description=(
            "Dual-view Agentic RAG system for shopping mall product discovery "
            "and admin data governance."
        ),
        version="1.0.0",
        docs_url="/docs" if settings.is_dev else None,
        redoc_url="/redoc" if settings.is_dev else None,
        lifespan=lifespan,
    )

    # ── Middleware ────────────────────────────────────────────────────────
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.is_dev else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routers ───────────────────────────────────────────────────────────
    app.include_router(user.router, prefix="/api/user", tags=["User"])
    app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
    app.include_router(ingest.router, prefix="/api/ingest", tags=["Ingest"])
    app.include_router(chat_ws_router, tags=["WebSocket"])

    # ── Health ────────────────────────────────────────────────────────────
    @app.get("/health", tags=["Health"])
    async def health() -> dict:
        return {"status": "ok", "env": settings.app_env}

    return app


app = create_app()

