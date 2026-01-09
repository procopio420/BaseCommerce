"""Add Redis Streams support

Revision ID: 005
Revises: 004
Create Date: 2025-01-08

Adds:
- published_at column to event_outbox for relay tracking
- engine_processed_events table for idempotency
- Additional indexes for engine tables
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add published_at column to event_outbox for relay tracking
    op.add_column(
        "event_outbox",
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "idx_event_outbox_published",
        "event_outbox",
        ["published_at"],
        postgresql_where=sa.text("published_at IS NULL"),
    )

    # Create engine_processed_events table for idempotency
    op.create_table(
        "engine_processed_events",
        sa.Column("event_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("vertical", sa.String(50), nullable=False, server_default="materials"),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("result", postgresql.JSONB, nullable=True),
    )
    op.create_index(
        "idx_processed_events_tenant_date",
        "engine_processed_events",
        ["tenant_id", "processed_at"],
    )

    # Add missing indexes for engine tables (time-based queries and retention)
    op.create_index(
        "idx_stock_alerts_tenant_created",
        "engine_stock_alerts",
        ["tenant_id", "created_at"],
    )
    op.create_index(
        "idx_replenishment_tenant_created",
        "engine_replenishment_suggestions",
        ["tenant_id", "created_at"],
    )
    op.create_index(
        "idx_sales_suggestions_tenant_created",
        "engine_sales_suggestions",
        ["tenant_id", "created_at"],
    )
    op.create_index(
        "idx_supplier_alerts_tenant_created",
        "engine_supplier_price_alerts",
        ["tenant_id", "created_at"],
    )
    op.create_index(
        "idx_delivery_routes_tenant_created",
        "engine_delivery_routes",
        ["tenant_id", "created_at"],
    )
    op.create_index(
        "idx_sales_facts_tenant_created",
        "engine_sales_facts",
        ["tenant_id", "created_at"],
    )
    op.create_index(
        "idx_stock_facts_tenant_created",
        "engine_stock_facts",
        ["tenant_id", "created_at"],
    )


def downgrade() -> None:
    # Drop engine table indexes
    op.drop_index("idx_stock_facts_tenant_created", table_name="engine_stock_facts")
    op.drop_index("idx_sales_facts_tenant_created", table_name="engine_sales_facts")
    op.drop_index("idx_delivery_routes_tenant_created", table_name="engine_delivery_routes")
    op.drop_index("idx_supplier_alerts_tenant_created", table_name="engine_supplier_price_alerts")
    op.drop_index("idx_sales_suggestions_tenant_created", table_name="engine_sales_suggestions")
    op.drop_index("idx_replenishment_tenant_created", table_name="engine_replenishment_suggestions")
    op.drop_index("idx_stock_alerts_tenant_created", table_name="engine_stock_alerts")

    # Drop engine_processed_events
    op.drop_table("engine_processed_events")

    # Remove published_at from event_outbox
    op.drop_index("idx_event_outbox_published", table_name="event_outbox")
    op.drop_column("event_outbox", "published_at")

