"""
app/db/models.py — SQLAlchemy async ORM models.
Mirrors the PostgreSQL schema defined in the PRD.
"""

import uuid
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Boolean, Column, DateTime, Enum, Float, ForeignKey,
    Integer, Numeric, String, Text, Date, Time, JSON,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.sql import func
import enum


# ── Enums ─────────────────────────────────────────────────────────────────

class UserRole(str, enum.Enum):
    admin = "admin"
    store_manager = "store_manager"
    data_auditor = "data_auditor"
    shopper = "shopper"
    guest = "guest"


class StoreCategory(str, enum.Enum):
    fashion = "fashion"
    food = "food"
    electronics = "electronics"
    beauty = "beauty"
    kids = "kids"
    sports = "sports"
    other = "other"


ProductCategory = StoreCategory  # same values


class JobStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    success = "success"
    partial = "partial"
    failed = "failed"


class FlagIssueType(str, enum.Enum):
    price_out_of_bounds = "price_out_of_bounds"
    invalid_date = "invalid_date"
    missing_field = "missing_field"
    schema_mismatch = "schema_mismatch"


class FlagSeverity(str, enum.Enum):
    warning = "warning"
    error = "error"
    critical = "critical"


# ── Base ──────────────────────────────────────────────────────────────────

class Base(DeclarativeBase):
    pass


# ── Tables ────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    user_id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.shopper, index=True)
    store_id = Column(PG_UUID(as_uuid=True), ForeignKey("stores.store_id"), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_login_at = Column(DateTime(timezone=True), nullable=True)

    store = relationship("Store", foreign_keys=[store_id])

class Store(Base):
    __tablename__ = "stores"

    store_id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, index=True)
    floor = Column(Integer, nullable=False)
    unit = Column(String(50))
    website_url = Column(Text)
    category = Column(Enum(StoreCategory), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    products = relationship("Product", back_populates="store", lazy="dynamic")
    scrape_jobs = relationship("ScrapeJob", back_populates="store", lazy="dynamic")
    hours = relationship("StoreHoursModel", back_populates="store", uselist=False)


class StoreHoursModel(Base):
    __tablename__ = "store_hours"

    hours_id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    store_id = Column(PG_UUID(as_uuid=True), ForeignKey("stores.store_id"), nullable=False)
    weekday_open = Column(Time, nullable=False)
    weekday_close = Column(Time, nullable=False)
    weekend_open = Column(Time, nullable=False)
    weekend_close = Column(Time, nullable=False)
    special_closures = Column(JSONB, default=list)

    store = relationship("Store", back_populates="hours")


class Product(Base):
    __tablename__ = "products"

    product_id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    store_id = Column(PG_UUID(as_uuid=True), ForeignKey("stores.store_id"), nullable=False, index=True)
    name = Column(String(300), nullable=False)
    price_vnd = Column(Numeric(15, 2), nullable=False)
    discount_pct = Column(Float)
    category = Column(Enum(StoreCategory), nullable=False, index=True)
    image_url = Column(Text)
    promo_start = Column(Date)
    promo_end = Column(Date)
    is_active = Column(Boolean, default=True, nullable=False)
    confidence_score = Column(Float)          # per-field extraction confidence avg
    last_scraped_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    store = relationship("Store", back_populates="products")


class ScrapeJob(Base):
    __tablename__ = "scrape_jobs"

    job_id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    store_id = Column(PG_UUID(as_uuid=True), ForeignKey("stores.store_id"), nullable=False, index=True)
    triggered_by = Column(String(100))         # "cron" | admin user id
    status = Column(Enum(JobStatus), default=JobStatus.pending, nullable=False)
    items_scraped = Column(Integer, default=0)
    items_failed = Column(Integer, default=0)
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    store = relationship("Store", back_populates="scrape_jobs")
    audit_flags = relationship("AuditFlagModel", back_populates="job", lazy="dynamic")


class AuditFlagModel(Base):
    __tablename__ = "audit_flags"

    flag_id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(PG_UUID(as_uuid=True), ForeignKey("scrape_jobs.job_id"), nullable=False, index=True)
    store_id = Column(PG_UUID(as_uuid=True), ForeignKey("stores.store_id"), nullable=False, index=True)
    product_name = Column(String(300))
    field = Column(String(100), nullable=False)
    raw_value = Column(JSONB)
    issue = Column(Enum(FlagIssueType), nullable=False)
    severity = Column(Enum(FlagSeverity), nullable=False)
    resolved = Column(Boolean, default=False, nullable=False)
    resolved_by = Column(String(100))
    resolved_at = Column(DateTime(timezone=True))
    resolution_note = Column(Text)
    corrected_value = Column(JSONB)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    job = relationship("ScrapeJob", back_populates="audit_flags")


class PriceBoundRule(Base):
    __tablename__ = "price_bound_rules"

    rule_id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    category = Column(Enum(StoreCategory), nullable=False, unique=True)
    min_price_vnd = Column(Numeric(15, 2), nullable=False)
    max_price_vnd = Column(Numeric(15, 2), nullable=False)
    updated_by = Column(String(100))
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())


class AdminAuditLog(Base):
    __tablename__ = "admin_audit_log"

    log_id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    admin_id = Column(String(100), nullable=False)
    action = Column(String(100), nullable=False)
    target_table = Column(String(100))
    target_id = Column(PG_UUID(as_uuid=True))
    old_value = Column(JSONB)
    new_value = Column(JSONB)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
