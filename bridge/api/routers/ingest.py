"""
app/api/routers/ingest.py — Data ingestion / scrape trigger endpoints.
"""

import uuid
from typing import Any, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, AnyHttpUrl

router = APIRouter()


class ScrapeRequest(BaseModel):
    store_id: str
    store_url: AnyHttpUrl
    force_reindex: bool = False


from backend.ingest.agents.scraper import scrape_store_products
from backend.ingest.agents.validator import validate_scraped_items
from backend.ingest.agents.indexer import index_validated_products


async def _run_ingest_background(job_id: str, store_id: str, store_url: str):
    raw_items = await scrape_store_products(store_id, store_url)
    val_results = await validate_scraped_items(job_id, store_id, raw_items)
    valid_products = [r.validated_product for r in val_results if r.is_valid and r.validated_product]
    await index_validated_products(valid_products)


@router.post("/trigger", summary="Trigger a scrape job for a store")
async def trigger_scrape(
    req: ScrapeRequest,
    background_tasks: BackgroundTasks,
) -> dict[str, Any]:
    """
    Queues a scrape + validate + index pipeline for the given store.
    Returns the job_id immediately; monitor via /status/{job_id}.
    """
    job_id = str(uuid.uuid4())
    background_tasks.add_task(_run_ingest_background, job_id, req.store_id, str(req.store_url))
    return {
        "job_id": job_id,
        "store_id": req.store_id,
        "status": "queued",
        "message": f"Scrape job {job_id} queued. Monitor at /api/ingest/status/{job_id}",
    }


@router.get("/status/{job_id}", summary="Stream job status via SSE")
async def job_status_sse(job_id: str) -> StreamingResponse:
    """
    Server-Sent Events stream for real-time job status updates.
    Emits events: { status, items_scraped, items_failed, message }
    """
    async def event_stream():
        # TODO Phase 2: poll job status from DB/Redis and stream events
        yield f"data: {{\"job_id\": \"{job_id}\", \"status\": \"pending\"}}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/reindex", summary="Re-index validated products into ChromaDB")
async def reindex(
    store_id: Optional[str] = None,
    background_tasks: BackgroundTasks = BackgroundTasks(),
) -> dict[str, Any]:
    """Force re-embedding and re-indexing for one or all stores."""
    job_id = str(uuid.uuid4())
    return {
        "job_id": job_id,
        "scope": store_id or "all",
        "message": "Re-index job queued — implementation pending Phase 2",
    }

