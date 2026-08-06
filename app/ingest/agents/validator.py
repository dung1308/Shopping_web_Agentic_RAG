"""
app/ingest/agents/validator.py — Validator Agent.
Validates scraped product data against strict Pydantic AI schemas.
Generates AuditFlag records for failed validations or price bound rule violations.
"""

import uuid
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AuditFlagModel, FlagIssueType, FlagSeverity, PriceBoundRule, StoreCategory
from app.schemas.validation import AuditFlag, ScrapedProduct, ValidationResult

logger = logging.getLogger("mall_rag.validator")


async def validate_scraped_items(
    job_id: str,
    store_id: str,
    raw_items: list[dict[str, Any]],
    db_session: Optional[AsyncSession] = None,
) -> list[ValidationResult]:
    """
    Validates a list of raw scraped items for a given job and store.
    Generates AuditFlag objects for validation errors or price rule violations.
    Persists audit flags to PostgreSQL if a DB session is provided.
    """
    results: list[ValidationResult] = []
    job_uuid = uuid.UUID(job_id) if isinstance(job_id, str) else job_id
    store_uuid = uuid.UUID(store_id) if isinstance(store_id, str) else store_id

    # Fetch price bound rules from DB if session is active
    price_rules: dict[StoreCategory, tuple[Decimal, Decimal]] = {}
    if db_session:
        try:
            stmt = select(PriceBoundRule)
            res = await db_session.execute(stmt)
            for rule in res.scalars().all():
                price_rules[rule.category] = (rule.min_price_vnd, rule.max_price_vnd)
        except Exception as exc:
            logger.warning(f"Could not load price bound rules from DB: {exc}")

    for raw in raw_items:
        flags: list[AuditFlag] = []
        product_name = raw.get("product_name")
        validated_product: Optional[ScrapedProduct] = None

        # Clean/parse price if string provided
        if "price_vnd" not in raw and "raw_price" in raw:
            raw_price_str = str(raw["raw_price"]).replace(",", "").replace(".", "").replace("VND", "").replace("đ", "").strip()
            try:
                raw["price_vnd"] = Decimal(raw_price_str)
            except Exception:
                raw["price_vnd"] = Decimal("0")

        # Inject mandatory store_id & scraped_at if missing
        raw_to_validate = dict(raw)
        raw_to_validate["store_id"] = str(store_uuid)
        if "scraped_at" not in raw_to_validate:
            raw_to_validate["scraped_at"] = datetime.now(timezone.utc)
        if "category" not in raw_to_validate:
            raw_to_validate["category"] = StoreCategory.other.value

        try:
            validated_product = ScrapedProduct(**raw_to_validate)

            # Check custom category price bounds if rules exist
            cat = validated_product.category
            if cat in price_rules:
                min_p, max_p = price_rules[cat]
                if validated_product.price_vnd < min_p or validated_product.price_vnd > max_p:
                    flag = AuditFlag(
                        job_id=job_uuid,
                        store_id=store_uuid,
                        product_name=validated_product.product_name,
                        field="price_vnd",
                        issue="price_out_of_bounds",
                        raw_value=float(validated_product.price_vnd),
                        severity="error" if validated_product.price_vnd > max_p * 2 else "warning",
                    )
                    flags.append(flag)

        except ValidationError as val_err:
            for err in val_err.errors():
                loc_field = str(err["loc"][0]) if err["loc"] else "unknown"
                msg = err["msg"]
                issue_type: FlagIssueType = "schema_mismatch"
                if "date" in msg.lower():
                    issue_type = "invalid_date"
                elif "greater than" in msg.lower() or "bounds" in msg.lower():
                    issue_type = "price_out_of_bounds"

                flag = AuditFlag(
                    job_id=job_uuid,
                    store_id=store_uuid,
                    product_name=product_name,
                    field=loc_field,
                    issue=issue_type,
                    raw_value=raw.get(loc_field),
                    severity="error",
                )
                flags.append(flag)

        is_valid = (validated_product is not None) and (not any(f.severity == "critical" for f in flags))
        
        # Persist audit flags to DB if session provided
        if db_session and flags:
            for f in flags:
                db_flag = AuditFlagModel(
                    flag_id=f.flag_id,
                    job_id=f.job_id,
                    store_id=f.store_id,
                    product_name=f.product_name,
                    field=f.field,
                    raw_value=f.raw_value,
                    issue=f.issue,
                    severity=f.severity,
                    resolved=False,
                )
                db_session.add(db_flag)
            try:
                await db_session.flush()
            except Exception as exc:
                logger.error(f"Failed to persist audit flags to DB: {exc}")

        results.append(
            ValidationResult(
                store_id=store_uuid,
                job_id=job_uuid,
                product_name=product_name,
                is_valid=is_valid,
                validated_product=validated_product if is_valid else None,
                flags=flags,
            )
        )

    logger.info(f"Validated {len(raw_items)} items for store {store_id}: {sum(1 for r in results if r.is_valid)} valid")
    return results
