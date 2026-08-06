"""
app/schemas/validation.py — Pydantic AI strict data validation schemas.
These are the canonical schemas for ALL data entering the system via scraping.
Validation failures generate AuditFlag records.
"""

import uuid
from datetime import date, datetime, time, timezone
from decimal import Decimal
from typing import Any, Optional, Literal

from pydantic import (
    AnyHttpUrl,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from backend.db.models import StoreCategory


# ── Scraped Product ────────────────────────────────────────────────────────

class ScrapedProduct(BaseModel):
    """
    Strict schema for a product extracted from a store website.
    All fields go through Pydantic validation before DB insertion.
    """
    model_config = ConfigDict(strict=True)

    store_id: uuid.UUID
    product_name: str = Field(min_length=1, max_length=300)
    price_vnd: Decimal = Field(gt=Decimal("0"), le=Decimal("500000000"))
    discount_pct: Optional[float] = Field(None, ge=0.0, le=1.0)
    promo_start: Optional[date] = None
    promo_end: Optional[date] = None
    category: StoreCategory
    image_url: Optional[AnyHttpUrl] = None
    scraped_at: datetime
    raw_source_url: Optional[AnyHttpUrl] = None
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0)

    @field_validator("store_id", mode="before")
    @classmethod
    def coerce_uuid(cls, v: Any) -> uuid.UUID:
        if isinstance(v, uuid.UUID):
            return v
        try:
            return uuid.UUID(str(v))
        except (ValueError, AttributeError) as exc:
            raise ValueError(f"Invalid UUID: {v}") from exc

    @field_validator("category", mode="before")
    @classmethod
    def coerce_category(cls, v: Any) -> StoreCategory:
        if isinstance(v, StoreCategory):
            return v
        try:
            return StoreCategory(str(v).lower())
        except Exception:
            return StoreCategory.other

    @field_validator("price_vnd", mode="before")
    @classmethod
    def coerce_price(cls, v: Any) -> Decimal:
        if isinstance(v, Decimal):
            return v
        if isinstance(v, (int, float)):
            return Decimal(str(v))
        if isinstance(v, str):
            clean = v.replace(",", "").replace(".", "").replace("VND", "").replace("đ", "").strip()
            return Decimal(clean)
        return Decimal("0")

    @field_validator("scraped_at", mode="before")
    @classmethod
    def coerce_datetime(cls, v: Any) -> datetime:
        if isinstance(v, datetime):
            return v
        if isinstance(v, str):
            return datetime.fromisoformat(v.replace("Z", "+00:00"))
        return datetime.now(timezone.utc)

    @field_validator("product_name", mode="before")
    @classmethod
    def strip_whitespace(cls, v: Any) -> str:
        if isinstance(v, str):
            return v.strip()
        return v

    @model_validator(mode="after")
    def check_date_range(self) -> "ScrapedProduct":
        if self.promo_start and self.promo_end:
            if self.promo_end <= self.promo_start:
                raise ValueError(
                    f"promo_end ({self.promo_end}) must be strictly after "
                    f"promo_start ({self.promo_start})"
                )
            delta = (self.promo_end - self.promo_start).days
            if delta > 365:
                raise ValueError(
                    f"Promotion window of {delta} days exceeds 1 year — likely a scraping error"
                )
        return self

    @model_validator(mode="after")
    def price_with_discount_sanity(self) -> "ScrapedProduct":
        if self.discount_pct is not None and self.discount_pct > 0.95:
            raise ValueError(
                f"Discount of {self.discount_pct * 100:.0f}% is suspiciously high (>95%)"
            )
        return self


# ── Store Operating Hours ──────────────────────────────────────────────────

class StoreHoursSchema(BaseModel):
    """Strict schema for store operating hours."""
    model_config = ConfigDict(strict=True)

    store_id: uuid.UUID
    weekday_open: time
    weekday_close: time
    weekend_open: time
    weekend_close: time
    special_closures: list[date] = Field(default_factory=list)

    @field_validator("store_id", mode="before")
    @classmethod
    def coerce_uuid(cls, v: Any) -> uuid.UUID:
        if isinstance(v, uuid.UUID):
            return v
        try:
            return uuid.UUID(str(v))
        except (ValueError, AttributeError) as exc:
            raise ValueError(f"Invalid UUID: {v}") from exc

    @model_validator(mode="after")
    def hours_sanity(self) -> "StoreHoursSchema":
        if self.weekday_close <= self.weekday_open:
            raise ValueError(
                f"weekday_close ({self.weekday_close}) must be after "
                f"weekday_open ({self.weekday_open})"
            )
        if self.weekend_close <= self.weekend_open:
            raise ValueError(
                f"weekend_close ({self.weekend_close}) must be after "
                f"weekend_open ({self.weekend_open})"
            )
        return self


# ── Audit Flag ────────────────────────────────────────────────────────────

class AuditFlag(BaseModel):
    """Represents a data quality issue detected during validation."""
    model_config = ConfigDict(strict=False)   # raw_value can be anything

    flag_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    job_id: uuid.UUID
    store_id: uuid.UUID
    product_name: Optional[str] = None
    field: str
    issue: Literal[
        "price_out_of_bounds",
        "invalid_date",
        "missing_field",
        "schema_mismatch",
    ]
    raw_value: Any
    severity: Literal["warning", "error", "critical"]
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    resolved: bool = False


# ── Price Bound Rule ──────────────────────────────────────────────────────

class PriceBoundRuleSchema(BaseModel):
    """Configurable price bounds per product category."""
    model_config = ConfigDict(strict=True)

    category: StoreCategory
    min_price_vnd: Decimal = Field(ge=Decimal("0"))
    max_price_vnd: Decimal = Field(gt=Decimal("0"))

    @model_validator(mode="after")
    def min_lt_max(self) -> "PriceBoundRuleSchema":
        if self.min_price_vnd >= self.max_price_vnd:
            raise ValueError("min_price_vnd must be less than max_price_vnd")
        return self


# ── Validation Result ─────────────────────────────────────────────────────

class ValidationResult(BaseModel):
    """Output of the Validator Agent for a single scraped item."""
    store_id: uuid.UUID
    job_id: uuid.UUID
    product_name: Optional[str]
    is_valid: bool
    validated_product: Optional[ScrapedProduct] = None
    flags: list[AuditFlag] = Field(default_factory=list)

    @property
    def has_critical_flags(self) -> bool:
        return any(f.severity == "critical" for f in self.flags)

