"""
app/api/routers/admin.py — Admin REST endpoints (JWT-protected).
"""

import csv
import io
from typing import Any, Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

router = APIRouter()


import logging
from backend.auth.rbac import require_roles, get_current_user

logger = logging.getLogger("mall_rag.admin")

# Real JWT Role-Based Access Control Dependency
require_admin = require_roles("admin", "data_auditor", "store_manager")


# ── Request / Response Schemas ─────────────────────────────────────────────

class FlagResolveRequest(BaseModel):
    corrected_value: Optional[Any] = None
    resolution_note: Optional[str] = None


class PriceBoundRuleRequest(BaseModel):
    category: str
    min_price_vnd: float = Field(gt=0)
    max_price_vnd: float = Field(gt=0)


# ── Job Endpoints ──────────────────────────────────────────────────────────

@router.get("/jobs", summary="List all scrape jobs")
async def list_jobs(
    store_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    _admin=Depends(require_admin),
) -> dict[str, Any]:
    """List all scrape jobs with status, counts, and timestamps."""
    return {"jobs": [], "message": "Endpoint ready — DB query pending Phase 5"}


@router.get("/jobs/{job_id}", summary="Get job detail")
async def get_job(job_id: str, _admin=Depends(require_admin)) -> dict[str, Any]:
    return {"job_id": job_id, "message": "Endpoint ready — DB query pending Phase 5"}


# ── Audit Flag Endpoints ───────────────────────────────────────────────────

@router.get("/flags", summary="List audit flags")
async def list_flags(
    store_id: Optional[str] = Query(None),
    severity: Optional[Literal["warning", "error", "critical"]] = Query(None),
    issue: Optional[str] = Query(None),
    resolved: Optional[bool] = Query(None),
    limit: int = Query(20, ge=1, le=200),
    _admin=Depends(require_admin),
) -> dict[str, Any]:
    """List data quality audit flags with optional filters."""
    return {"flags": [], "count": 0, "message": "Endpoint ready — DB query pending Phase 5"}


@router.patch("/flags/{flag_id}", summary="Resolve / override a flag")
async def resolve_flag(
    flag_id: str,
    body: FlagResolveRequest,
    _admin=Depends(require_admin),
) -> dict[str, Any]:
    """Mark an audit flag as resolved with an optional corrected value."""
    return {
        "flag_id": flag_id,
        "resolved": True,
        "message": "Endpoint ready — DB mutation pending Phase 5",
    }


@router.get("/flags/export", summary="Export flags as CSV")
async def export_flags(
    store_id: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    _admin=Depends(require_admin),
) -> StreamingResponse:
    """Download audit flags as a CSV file."""
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=["flag_id", "store_id", "product_name", "field", "issue", "severity", "raw_value", "created_at"],
    )
    writer.writeheader()
    # TODO Phase 5: fill from DB
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=audit_flags.csv"},
    )


# ── Price Bound Rules ──────────────────────────────────────────────────────

@router.get("/price-rules", summary="List price bound rules")
async def list_price_rules(_admin=Depends(require_admin)) -> dict[str, Any]:
    return {"rules": [], "message": "Endpoint ready — DB query pending Phase 5"}


@router.post("/price-rules", summary="Create price bound rule")
async def create_price_rule(
    body: PriceBoundRuleRequest,
    _admin=Depends(require_admin),
) -> dict[str, Any]:
    return {"message": "Endpoint ready — DB mutation pending Phase 5", "category": body.category}


@router.patch("/price-rules/{rule_id}", summary="Update price bound rule")
async def update_price_rule(
    rule_id: str,
    body: PriceBoundRuleRequest,
    _admin=Depends(require_admin),
) -> dict[str, Any]:
    return {"rule_id": rule_id, "message": "Endpoint ready — DB mutation pending Phase 5"}


# ── Reports ───────────────────────────────────────────────────────────────

@router.get("/reports/accuracy", summary="Extraction accuracy report")
async def accuracy_report(_admin=Depends(require_admin)) -> dict[str, Any]:
    """
    Returns overall extraction accuracy metrics:
    total scraped, % valid, % flagged, breakdown by issue type.
    """
    return {
        "total_scraped": 0,
        "valid_pct": 0.0,
        "flagged_pct": 0.0,
        "by_issue": {},
        "message": "Endpoint ready — aggregation pending Phase 5",
    }
