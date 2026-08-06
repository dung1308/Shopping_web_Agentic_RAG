"""
tests/test_schemas.py — Unit tests for Pydantic AI validation schemas.
Run with: pytest tests/test_schemas.py -v
"""

import uuid
from datetime import date, datetime, time, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from backend.db.models import StoreCategory
from backend.schemas.validation import (
    AuditFlag,
    PriceBoundRuleSchema,
    ScrapedProduct,
    StoreHoursSchema,
)


def make_valid_product(**overrides) -> dict:
    base = {
        "store_id": str(uuid.uuid4()),
        "product_name": "Túi da nữ chính hãng",
        "price_vnd": Decimal("450000"),
        "discount_pct": 0.1,
        "promo_start": date(2026, 8, 1),
        "promo_end": date(2026, 8, 31),
        "category": StoreCategory.fashion,
        "image_url": "https://example.com/bag.jpg",
        "scraped_at": datetime.now(timezone.utc),
        "confidence_score": 0.95,
    }
    base.update(overrides)
    return base


# ── ScrapedProduct ─────────────────────────────────────────────────────────

class TestScrapedProduct:
    def test_valid_product_passes(self):
        p = ScrapedProduct(**make_valid_product())
        assert p.product_name == "Túi da nữ chính hãng"
        assert p.price_vnd == Decimal("450000")

    def test_price_zero_fails(self):
        with pytest.raises(ValidationError, match="greater than 0"):
            ScrapedProduct(**make_valid_product(price_vnd=Decimal("0")))

    def test_price_too_high_fails(self):
        with pytest.raises(ValidationError):
            ScrapedProduct(**make_valid_product(price_vnd=Decimal("600000000")))

    def test_promo_end_before_start_fails(self):
        with pytest.raises(ValidationError, match="strictly after"):
            ScrapedProduct(**make_valid_product(
                promo_start=date(2026, 8, 31),
                promo_end=date(2026, 8, 1),
            ))

    def test_promo_window_over_one_year_fails(self):
        with pytest.raises(ValidationError, match="1 year"):
            ScrapedProduct(**make_valid_product(
                promo_start=date(2025, 1, 1),
                promo_end=date(2027, 2, 1),
            ))

    def test_discount_over_95pct_fails(self):
        with pytest.raises(ValidationError, match="suspiciously high"):
            ScrapedProduct(**make_valid_product(discount_pct=0.97))

    def test_empty_product_name_fails(self):
        with pytest.raises(ValidationError):
            ScrapedProduct(**make_valid_product(product_name=""))

    def test_whitespace_stripped_from_name(self):
        p = ScrapedProduct(**make_valid_product(product_name="  Áo khoác  "))
        assert p.product_name == "Áo khoác"

    def test_no_promo_dates_is_valid(self):
        p = ScrapedProduct(**make_valid_product(promo_start=None, promo_end=None))
        assert p.promo_start is None


# ── StoreHoursSchema ───────────────────────────────────────────────────────

class TestStoreHoursSchema:
    def test_valid_hours_passes(self):
        h = StoreHoursSchema(
            store_id=str(uuid.uuid4()),
            weekday_open=time(9, 0),
            weekday_close=time(22, 0),
            weekend_open=time(9, 0),
            weekend_close=time(23, 0),
        )
        assert h.weekday_open < h.weekday_close

    def test_close_before_open_fails(self):
        with pytest.raises(ValidationError, match="after"):
            StoreHoursSchema(
                store_id=str(uuid.uuid4()),
                weekday_open=time(22, 0),
                weekday_close=time(9, 0),
                weekend_open=time(9, 0),
                weekend_close=time(23, 0),
            )


# ── PriceBoundRuleSchema ───────────────────────────────────────────────────

class TestPriceBoundRuleSchema:
    def test_valid_rule_passes(self):
        r = PriceBoundRuleSchema(
            category=StoreCategory.food,
            min_price_vnd=Decimal("10000"),
            max_price_vnd=Decimal("500000"),
        )
        assert r.max_price_vnd > r.min_price_vnd

    def test_min_gte_max_fails(self):
        with pytest.raises(ValidationError, match="less than"):
            PriceBoundRuleSchema(
                category=StoreCategory.food,
                min_price_vnd=Decimal("500000"),
                max_price_vnd=Decimal("100000"),
            )

