"""
backend/api/routers/diagnostics.py — Connection diagnostic REST endpoints.
Tests active connectivity to Neon PostgreSQL, Redis, OpenAI, Gemini, Anthropic, Ollama, ChromaDB, and Embedding Server.
"""

import asyncio
import time
import os
import httpx
from typing import Any, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from backend.config import get_settings

router = APIRouter()
settings = get_settings()

class LLMTestRequest(BaseModel):
    provider: str = Field(..., description="LLM provider: 'local', 'openai', 'gemini', 'anthropic'")
    prompt: str = Field("Hello! Reply with 'Connection successful' and a 1-sentence joke.", description="Prompt message")
    model: Optional[str] = Field(None, description="Optional model override")

class RedisTestRequest(BaseModel):
    key: str = Field("test_key", description="Redis key to set")
    value: str = Field("Hello from Mall Agentic RAG!", description="Value to store")

class SQLTestRequest(BaseModel):
    query: str = Field("SELECT version();", description="SQL query to execute")

# ── Health Checks ─────────────────────────────────────────────────────────────

async def _check_database() -> dict[str, Any]:
    start = time.perf_counter()
    db_url = str(settings.database_url)
    is_neon = "neon.tech" in db_url
    
    try:
        from backend.db.session import _get_engine
        engine = _get_engine()
        async with engine.connect() as conn:
            from sqlalchemy import text
            res = await conn.execute(text("SELECT version(), current_database(), current_user;"))
            row = res.fetchone()
            elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
            
            return {
                "status": "connected",
                "latency_ms": elapsed_ms,
                "provider": "Neon Cloud Database" if is_neon else "PostgreSQL",
                "details": {
                    "is_neon": is_neon,
                    "database": row[1] if row else "unknown",
                    "user": row[2] if row else "unknown",
                    "version_summary": str(row[0]).split(",")[0] if row else "unknown",
                },
                "fix_hint": None,
            }
    except Exception as exc:
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        return {
            "status": "failed",
            "latency_ms": elapsed_ms,
            "provider": "Neon Cloud Database" if is_neon else "PostgreSQL",
            "details": {"error": str(exc)},
            "fix_hint": "Check DATABASE_URL in .env. If using Neon, ensure password and sslmode=require (or ssl=require) are set.",
        }


async def _check_redis() -> dict[str, Any]:
    start = time.perf_counter()
    try:
        from backend.cache.redis_client import get_redis, init_redis
        try:
            r = get_redis()
        except RuntimeError:
            await init_redis()
            r = get_redis()

        pong = await r.ping()
        test_key = "diag:ping_test"
        await r.set(test_key, "ok", ex=10)
        val = await r.get(test_key)
        await r.delete(test_key)
        
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        info = await r.info("server")
        
        return {
            "status": "connected",
            "latency_ms": elapsed_ms,
            "provider": "Redis",
            "details": {
                "ping": pong,
                "redis_version": info.get("redis_version", "unknown"),
                "kv_test": val == "ok",
                "redis_url": str(settings.redis_url).split("@")[-1],  # hide auth
            },
            "fix_hint": None,
        }
    except Exception as exc:
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        return {
            "status": "failed",
            "latency_ms": elapsed_ms,
            "provider": "Redis",
            "details": {"error": str(exc)},
            "fix_hint": "Verify Redis is running (e.g. `docker run -p 6379:6379 redis`) and check REDIS_URL in .env.",
        }


async def _check_ollama() -> dict[str, Any]:
    start = time.perf_counter()
    base_url = str(settings.llm_base_url).rstrip("/")
    model = settings.llm_model
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{base_url}/models")
            elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
            if resp.status_code == 200:
                data = resp.json().get("data") or []
                available = [m.get("id") for m in data]
                has_configured = any(model in m for m in available)
                return {
                    "status": "connected" if has_configured else "warning",
                    "latency_ms": elapsed_ms,
                    "provider": "Local LLM (Ollama)",
                    "details": {
                        "base_url": base_url,
                        "configured_model": model,
                        "available_models": available,
                        "model_ready": has_configured,
                    },
                    "fix_hint": None if has_configured else f"Model '{model}' not found in Ollama models list. Run `ollama pull {model}`.",
                }
            else:
                return {
                    "status": "failed",
                    "latency_ms": elapsed_ms,
                    "provider": "Local LLM (Ollama)",
                    "details": {"http_code": resp.status_code},
                    "fix_hint": f"Ollama returned HTTP {resp.status_code}. Make sure Ollama server is running.",
                }
    except Exception as exc:
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        return {
            "status": "failed",
            "latency_ms": elapsed_ms,
            "provider": "Local LLM (Ollama)",
            "details": {"error": str(exc), "base_url": base_url},
            "fix_hint": f"Could not connect to Ollama at {base_url}. Ensure Ollama desktop app or 'ollama serve' is running.",
        }


async def _check_openai() -> dict[str, Any]:
    start = time.perf_counter()
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    
    if not api_key:
        return {
            "status": "not_configured",
            "latency_ms": 0,
            "provider": "OpenAI",
            "details": {"message": "OPENAI_API_KEY is missing in .env"},
            "fix_hint": "Add `OPENAI_API_KEY=sk-...` to your .env file to enable OpenAI models.",
        }
        
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                "https://api.openai.com/v1/models",
                headers={"Authorization": f"Bearer {api_key}"},
            )
            elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
            if resp.status_code == 200:
                models = [m["id"] for m in resp.json().get("data", [])[:10]]
                return {
                    "status": "connected",
                    "latency_ms": elapsed_ms,
                    "provider": "OpenAI",
                    "details": {
                        "api_key_status": "Valid",
                        "sample_models": models,
                    },
                    "fix_hint": None,
                }
            else:
                return {
                    "status": "failed",
                    "latency_ms": elapsed_ms,
                    "provider": "OpenAI",
                    "details": {"http_code": resp.status_code, "body": resp.text[:200]},
                    "fix_hint": "Invalid OPENAI_API_KEY or billing quota exceeded.",
                }
    except Exception as exc:
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        return {
            "status": "failed",
            "latency_ms": elapsed_ms,
            "provider": "OpenAI",
            "details": {"error": str(exc)},
            "fix_hint": "Network error reaching OpenAI API endpoint.",
        }


async def _check_gemini() -> dict[str, Any]:
    start = time.perf_counter()
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    
    if not api_key:
        return {
            "status": "not_configured",
            "latency_ms": 0,
            "provider": "Google Gemini",
            "details": {"message": "GEMINI_API_KEY is missing in .env"},
            "fix_hint": "Add `GEMINI_API_KEY=AIzaSy...` to your .env file to enable Gemini models.",
        }
        
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
            )
            elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
            if resp.status_code == 200:
                raw_models = resp.json().get("models", [])
                model_names = [m.get("name", "").replace("models/", "") for m in raw_models[:10]]
                return {
                    "status": "connected",
                    "latency_ms": elapsed_ms,
                    "provider": "Google Gemini",
                    "details": {
                        "api_key_status": "Valid",
                        "available_models": model_names,
                    },
                    "fix_hint": None,
                }
            else:
                return {
                    "status": "failed",
                    "latency_ms": elapsed_ms,
                    "provider": "Google Gemini",
                    "details": {"http_code": resp.status_code, "body": resp.text[:200]},
                    "fix_hint": "Invalid GEMINI_API_KEY or Gemini API disabled.",
                }
    except Exception as exc:
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        return {
            "status": "failed",
            "latency_ms": elapsed_ms,
            "provider": "Google Gemini",
            "details": {"error": str(exc)},
            "fix_hint": "Network error reaching Google Generative AI API.",
        }


async def _check_anthropic() -> dict[str, Any]:
    start = time.perf_counter()
    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    
    if not api_key:
        return {
            "status": "not_configured",
            "latency_ms": 0,
            "provider": "Anthropic Claude",
            "details": {"message": "ANTHROPIC_API_KEY is missing in .env"},
            "fix_hint": "Add `ANTHROPIC_API_KEY=sk-ant-...` to your .env file to enable Anthropic Claude.",
        }

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-3-5-sonnet-20241022",
                    "max_tokens": 1,
                    "messages": [{"role": "user", "content": "hi"}],
                },
            )
            elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
            if resp.status_code in (200, 400):
                return {
                    "status": "connected",
                    "latency_ms": elapsed_ms,
                    "provider": "Anthropic Claude",
                    "details": {
                        "api_key_status": "Valid",
                        "model": "claude-3-5-sonnet-20241022",
                    },
                    "fix_hint": None,
                }
            else:
                return {
                    "status": "failed",
                    "latency_ms": elapsed_ms,
                    "provider": "Anthropic Claude",
                    "details": {"http_code": resp.status_code, "body": resp.text[:200]},
                    "fix_hint": "Invalid ANTHROPIC_API_KEY or missing access.",
                }
    except Exception as exc:
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        return {
            "status": "failed",
            "latency_ms": elapsed_ms,
            "provider": "Anthropic Claude",
            "details": {"error": str(exc)},
            "fix_hint": "Network error reaching Anthropic API.",
        }


async def _check_chroma() -> dict[str, Any]:
    start = time.perf_counter()
    try:
        from backend.vector.chroma_client import get_chroma, init_chroma
        try:
            client = get_chroma()
        except RuntimeError:
            await init_chroma()
            client = get_chroma()

        collections = await asyncio.to_thread(client.list_collections)
        col_info = []
        for c in collections:
            count = await asyncio.to_thread(c.count)
            col_info.append({"name": c.name, "count": count})
            
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        return {
            "status": "connected",
            "latency_ms": elapsed_ms,
            "provider": "ChromaDB Vector Store",
            "details": {
                "mode": "HTTP Client" if getattr(settings, "chroma_host", "") else "Embedded Persistent",
                "path_or_host": getattr(settings, "chroma_host", "") or getattr(settings, "chroma_path", "./chroma_data"),
                "collections": col_info,
            },
            "fix_hint": None,
        }
    except Exception as exc:
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        return {
            "status": "failed",
            "latency_ms": elapsed_ms,
            "provider": "ChromaDB Vector Store",
            "details": {"error": str(exc)},
            "fix_hint": "Check CHROMA_PATH or CHROMA_HOST settings in .env.",
        }


async def _check_embedding() -> dict[str, Any]:
    start = time.perf_counter()
    base_url = str(settings.embed_base_url).rstrip("/")
    model = settings.embed_model
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{base_url}/health")
            elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
            if resp.status_code == 200:
                return {
                    "status": "connected",
                    "latency_ms": elapsed_ms,
                    "provider": f"Embedding Server ({model})",
                    "details": {
                        "base_url": base_url,
                        "model": model,
                        "dim": settings.embed_dim,
                    },
                    "fix_hint": None,
                }
            else:
                return {
                    "status": "failed",
                    "latency_ms": elapsed_ms,
                    "provider": f"Embedding Server ({model})",
                    "details": {"http_code": resp.status_code},
                    "fix_hint": f"Infinity embedding server at {base_url} returned HTTP {resp.status_code}.",
                }
    except Exception as exc:
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        return {
            "status": "failed",
            "latency_ms": elapsed_ms,
            "provider": f"Embedding Server ({model})",
            "details": {"error": str(exc), "base_url": base_url},
            "fix_hint": f"Could not reach Infinity embedding server at {base_url}. (You can launch it via Infinity CLI or Docker).",
        }


# ── Main Diagnostics Endpoint ─────────────────────────────────────────────

@router.get("/check-all", summary="Run comprehensive connection diagnostics across all configured services")
async def check_all_connections() -> dict[str, Any]:
    """
    Executes concurrent diagnostic probes against Neon/Postgres DB, Redis,
    Local Ollama LLM, OpenAI, Google Gemini, Anthropic Claude, ChromaDB, and Embedding Server.
    """
    db_res, redis_res, ollama_res, openai_res, gemini_res, anthropic_res, chroma_res, embed_res = await asyncio.gather(
        _check_database(),
        _check_redis(),
        _check_ollama(),
        _check_openai(),
        _check_gemini(),
        _check_anthropic(),
        _check_chroma(),
        _check_embedding(),
    )

    services = {
        "neon_postgres": db_res,
        "redis": redis_res,
        "ollama_local": ollama_res,
        "openai": openai_res,
        "gemini": gemini_res,
        "anthropic": anthropic_res,
        "chromadb": chroma_res,
        "embedding_server": embed_res,
    }

    statuses = [s["status"] for s in services.values()]
    if all(st in ("connected", "not_configured") for st in statuses):
        overall = "healthy"
    elif any(st == "connected" for st in statuses):
        overall = "degraded"
    else:
        overall = "unhealthy"

    return {
        "overall_status": overall,
        "timestamp": time.time(),
        "services": services,
    }


# ── Interactive Sandboxes ──────────────────────────────────────────────────

@router.post("/test-llm", summary="Interactive LLM inference sandbox")
async def test_llm_inference(req: LLMTestRequest) -> dict[str, Any]:
    """Test live completion against specified LLM provider."""
    start = time.perf_counter()
    provider = req.provider.lower()
    
    if provider == "local":
        base_url = str(settings.llm_base_url).rstrip("/")
        model = req.model or settings.llm_model
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{base_url}/chat/completions",
                    json={
                        "model": model,
                        "messages": [{"role": "user", "content": req.prompt}],
                        "max_tokens": 150,
                    },
                )
                elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
                if resp.status_code == 200:
                    reply = resp.json()["choices"][0]["message"]["content"]
                    return {"success": True, "provider": "Local Ollama", "model": model, "latency_ms": elapsed_ms, "reply": reply}
                else:
                    return {"success": False, "provider": "Local Ollama", "latency_ms": elapsed_ms, "error": f"HTTP {resp.status_code}: {resp.text}"}
        except Exception as exc:
            return {"success": False, "provider": "Local Ollama", "error": str(exc)}

    elif provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise HTTPException(status_code=400, detail="OPENAI_API_KEY is not set in .env")
        model = req.model or "gpt-4o-mini"
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={
                        "model": model,
                        "messages": [{"role": "user", "content": req.prompt}],
                        "max_tokens": 150,
                    },
                )
                elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
                if resp.status_code == 200:
                    reply = resp.json()["choices"][0]["message"]["content"]
                    return {"success": True, "provider": "OpenAI", "model": model, "latency_ms": elapsed_ms, "reply": reply}
                else:
                    return {"success": False, "provider": "OpenAI", "latency_ms": elapsed_ms, "error": resp.text}
        except Exception as exc:
            return {"success": False, "provider": "OpenAI", "error": str(exc)}

    elif provider == "gemini":
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        if not api_key:
            raise HTTPException(status_code=400, detail="GEMINI_API_KEY is not set in .env")
        model = req.model or "gemini-1.5-flash"
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}",
                    json={
                        "contents": [{"parts": [{"text": req.prompt}]}]
                    },
                )
                elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
                if resp.status_code == 200:
                    candidates = resp.json().get("candidates", [])
                    reply = candidates[0]["content"]["parts"][0]["text"] if candidates else "No content returned."
                    return {"success": True, "provider": "Google Gemini", "model": model, "latency_ms": elapsed_ms, "reply": reply}
                else:
                    return {"success": False, "provider": "Google Gemini", "latency_ms": elapsed_ms, "error": resp.text}
        except Exception as exc:
            return {"success": False, "provider": "Google Gemini", "error": str(exc)}

    elif provider == "anthropic":
        api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
        if not api_key:
            raise HTTPException(status_code=400, detail="ANTHROPIC_API_KEY is not set in .env")
        model = req.model or "claude-3-5-sonnet-20241022"
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json={
                        "model": model,
                        "max_tokens": 150,
                        "messages": [{"role": "user", "content": req.prompt}],
                    },
                )
                elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
                if resp.status_code == 200:
                    content = resp.json().get("content", [])
                    reply = content[0]["text"] if content else ""
                    return {"success": True, "provider": "Anthropic Claude", "model": model, "latency_ms": elapsed_ms, "reply": reply}
                else:
                    return {"success": False, "provider": "Anthropic Claude", "latency_ms": elapsed_ms, "error": resp.text}
        except Exception as exc:
            return {"success": False, "provider": "Anthropic Claude", "error": str(exc)}

    else:
        raise HTTPException(status_code=400, detail=f"Unsupported provider: '{provider}'")


@router.post("/test-db", summary="Interactive Neon / Postgres SQL sandbox")
async def test_db_query(req: SQLTestRequest) -> dict[str, Any]:
    """Executes a SQL query against configured database."""
    start = time.perf_counter()
    query = req.query.strip()
    if not query.lower().startswith(("select", "show", "explain")):
        raise HTTPException(status_code=400, detail="Only read-only queries (SELECT, SHOW, EXPLAIN) allowed in diagnostic test endpoint.")

    try:
        engine = _get_engine()
        async with engine.connect() as conn:
            from sqlalchemy import text
            res = await conn.execute(text(query))
            rows = [dict(row._mapping) for row in res.fetchall()[:20]]
            elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
            return {
                "success": True,
                "latency_ms": elapsed_ms,
                "row_count": len(rows),
                "rows": rows,
            }
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@router.post("/test-redis", summary="Interactive Redis set/get test sandbox")
async def test_redis_kv(req: RedisTestRequest) -> dict[str, Any]:
    """Test storing and retrieving a key in Redis."""
    start = time.perf_counter()
    try:
        try:
            r = get_redis()
        except RuntimeError:
            await init_redis()
            r = get_redis()

        full_key = f"diag:{req.key}"
        await r.set(full_key, req.value, ex=60)
        retrieved = await r.get(full_key)
        ttl = await r.ttl(full_key)
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        return {
            "success": True,
            "latency_ms": elapsed_ms,
            "key": full_key,
            "stored_value": req.value,
            "retrieved_value": retrieved,
            "match": req.value == retrieved,
            "ttl_remaining_seconds": ttl,
        }
    except Exception as exc:
        return {"success": False, "error": str(exc)}
