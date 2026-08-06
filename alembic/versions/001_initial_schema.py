"""initial schema

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-07-31 16:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enum types
    store_category = postgresql.ENUM(
        'fashion', 'food', 'electronics', 'beauty', 'kids', 'sports', 'other',
        name='storecategory', create_type=False
    )
    job_status = postgresql.ENUM(
        'pending', 'running', 'success', 'partial', 'failed',
        name='jobstatus', create_type=False
    )
    flag_issue_type = postgresql.ENUM(
        'price_out_of_bounds', 'invalid_date', 'missing_field', 'schema_mismatch',
        name='flagissuetype', create_type=False
    )
    flag_severity = postgresql.ENUM(
        'warning', 'error', 'critical',
        name='flagseverity', create_type=False
    )

    store_category.create(op.get_bind(), checkfirst=True)
    job_status.create(op.get_bind(), checkfirst=True)
    flag_issue_type.create(op.get_bind(), checkfirst=True)
    flag_severity.create(op.get_bind(), checkfirst=True)

    # 1. stores
    op.create_table(
        'stores',
        sa.Column('store_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False, index=True),
        sa.Column('floor', sa.Integer(), nullable=False),
        sa.Column('unit', sa.String(50), nullable=True),
        sa.Column('website_url', sa.Text(), nullable=True),
        sa.Column('category', store_category, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )

    # 2. store_hours
    op.create_table(
        'store_hours',
        sa.Column('hours_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('store_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('stores.store_id'), nullable=False),
        sa.Column('weekday_open', sa.Time(), nullable=False),
        sa.Column('weekday_close', sa.Time(), nullable=False),
        sa.Column('weekend_open', sa.Time(), nullable=False),
        sa.Column('weekend_close', sa.Time(), nullable=False),
        sa.Column('special_closures', postgresql.JSONB(), nullable=True),
    )

    # 3. products
    op.create_table(
        'products',
        sa.Column('product_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('store_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('stores.store_id'), nullable=False, index=True),
        sa.Column('name', sa.String(300), nullable=False),
        sa.Column('price_vnd', sa.Numeric(15, 2), nullable=False),
        sa.Column('discount_pct', sa.Float(), nullable=True),
        sa.Column('category', store_category, nullable=False, index=True),
        sa.Column('image_url', sa.Text(), nullable=True),
        sa.Column('promo_start', sa.Date(), nullable=True),
        sa.Column('promo_end', sa.Date(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('last_scraped_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )

    # 4. scrape_jobs
    op.create_table(
        'scrape_jobs',
        sa.Column('job_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('store_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('stores.store_id'), nullable=False, index=True),
        sa.Column('triggered_by', sa.String(100), nullable=True),
        sa.Column('status', job_status, server_default='pending', nullable=False),
        sa.Column('items_scraped', sa.Integer(), server_default='0'),
        sa.Column('items_failed', sa.Integer(), server_default='0'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )

    # 5. audit_flags
    op.create_table(
        'audit_flags',
        sa.Column('flag_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('job_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('scrape_jobs.job_id'), nullable=False, index=True),
        sa.Column('store_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('stores.store_id'), nullable=False, index=True),
        sa.Column('product_name', sa.String(300), nullable=True),
        sa.Column('field', sa.String(100), nullable=False),
        sa.Column('raw_value', postgresql.JSONB(), nullable=True),
        sa.Column('issue', flag_issue_type, nullable=False),
        sa.Column('severity', flag_severity, nullable=False),
        sa.Column('resolved', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('resolved_by', sa.String(100), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolution_note', sa.Text(), nullable=True),
        sa.Column('corrected_value', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )

    # 6. price_bound_rules
    op.create_table(
        'price_bound_rules',
        sa.Column('rule_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('category', store_category, nullable=False, unique=True),
        sa.Column('min_price_vnd', sa.Numeric(15, 2), nullable=False),
        sa.Column('max_price_vnd', sa.Numeric(15, 2), nullable=False),
        sa.Column('updated_by', sa.String(100), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )

    # 7. admin_audit_log
    op.create_table(
        'admin_audit_log',
        sa.Column('log_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('admin_id', sa.String(100), nullable=False),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('target_table', sa.String(100), nullable=True),
        sa.Column('target_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('old_value', postgresql.JSONB(), nullable=True),
        sa.Column('new_value', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )


def downgrade() -> None:
    op.drop_table('admin_audit_log')
    op.drop_table('price_bound_rules')
    op.drop_table('audit_flags')
    op.drop_table('scrape_jobs')
    op.drop_table('products')
    op.drop_table('store_hours')
    op.drop_table('stores')
