"""Add engine-owned tables

Revision ID: 004
Revises: 003
Create Date: 2025-01-08

These tables are OWNED by engines, not by verticals.
Engines write to these tables via event processing.
Verticals only read from these tables via API.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Engine Stock Alerts
    op.create_table(
        "engine_stock_alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("vertical", sa.String(50), nullable=False, server_default="materials"),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("alert_type", sa.String(50), nullable=False),
        sa.Column("risk_level", sa.String(20), nullable=False),
        sa.Column("current_stock", sa.String(50), nullable=False),
        sa.Column("minimum_stock", sa.String(50), nullable=False),
        sa.Column("days_until_rupture", sa.String(20), nullable=True),
        sa.Column("explanation", sa.Text, nullable=True),
        sa.Column("payload", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("idx_stock_alerts_tenant_product", "engine_stock_alerts", ["tenant_id", "product_id"])
    op.create_index("idx_stock_alerts_tenant_status", "engine_stock_alerts", ["tenant_id", "status"])

    # Engine Replenishment Suggestions
    op.create_table(
        "engine_replenishment_suggestions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("vertical", sa.String(50), nullable=False, server_default="materials"),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("suggested_quantity", sa.String(50), nullable=False),
        sa.Column("current_stock", sa.String(50), nullable=False),
        sa.Column("minimum_stock", sa.String(50), nullable=False),
        sa.Column("maximum_stock", sa.String(50), nullable=False),
        sa.Column("priority", sa.String(20), nullable=False),
        sa.Column("explanation", sa.Text, nullable=True),
        sa.Column("payload", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("idx_replenishment_tenant_product", "engine_replenishment_suggestions", ["tenant_id", "product_id"])
    op.create_index("idx_replenishment_tenant_status", "engine_replenishment_suggestions", ["tenant_id", "status"])

    # Engine Sales Suggestions
    op.create_table(
        "engine_sales_suggestions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("vertical", sa.String(50), nullable=False, server_default="materials"),
        sa.Column("suggestion_type", sa.String(50), nullable=False),
        sa.Column("source_product_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("suggested_product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("frequency", sa.String(20), nullable=True),
        sa.Column("priority", sa.String(20), nullable=False),
        sa.Column("explanation", sa.Text, nullable=True),
        sa.Column("payload", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("idx_sales_suggestions_tenant_source", "engine_sales_suggestions", ["tenant_id", "source_product_id"])
    op.create_index("idx_sales_suggestions_tenant_type", "engine_sales_suggestions", ["tenant_id", "suggestion_type"])

    # Engine Supplier Price Alerts
    op.create_table(
        "engine_supplier_price_alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("vertical", sa.String(50), nullable=False, server_default="materials"),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("supplier_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("alert_type", sa.String(50), nullable=False),
        sa.Column("current_price", sa.String(50), nullable=False),
        sa.Column("reference_price", sa.String(50), nullable=True),
        sa.Column("price_change_percent", sa.String(20), nullable=True),
        sa.Column("explanation", sa.Text, nullable=True),
        sa.Column("payload", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("idx_supplier_alerts_tenant_product", "engine_supplier_price_alerts", ["tenant_id", "product_id"])
    op.create_index("idx_supplier_alerts_tenant_supplier", "engine_supplier_price_alerts", ["tenant_id", "supplier_id"])

    # Engine Delivery Routes
    op.create_table(
        "engine_delivery_routes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("vertical", sa.String(50), nullable=False, server_default="materials"),
        sa.Column("route_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("route_name", sa.String(200), nullable=True),
        sa.Column("total_orders", sa.String(10), nullable=False),
        sa.Column("total_distance_km", sa.String(20), nullable=True),
        sa.Column("estimated_duration_minutes", sa.String(20), nullable=True),
        sa.Column("order_ids", postgresql.JSONB, nullable=False),
        sa.Column("route_sequence", postgresql.JSONB, nullable=False),
        sa.Column("explanation", sa.Text, nullable=True),
        sa.Column("payload", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("status", sa.String(20), nullable=False, server_default="planned"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("idx_delivery_routes_tenant_date", "engine_delivery_routes", ["tenant_id", "route_date"])
    op.create_index("idx_delivery_routes_tenant_status", "engine_delivery_routes", ["tenant_id", "status"])

    # Engine Sales Facts (normalized event data)
    op.create_table(
        "engine_sales_facts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("vertical", sa.String(50), nullable=False, server_default="materials"),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("quantity", sa.Numeric(15, 4), nullable=False),
        sa.Column("unit_price", sa.Numeric(15, 4), nullable=False),
        sa.Column("total_value", sa.Numeric(15, 4), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column("payload", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("idx_sales_facts_tenant_product_date", "engine_sales_facts", ["tenant_id", "product_id", "occurred_at"])
    op.create_index("idx_sales_facts_tenant_client", "engine_sales_facts", ["tenant_id", "client_id"])
    op.create_index("idx_sales_facts_tenant_order", "engine_sales_facts", ["tenant_id", "order_id"])

    # Engine Stock Facts (normalized event data)
    op.create_table(
        "engine_stock_facts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("vertical", sa.String(50), nullable=False, server_default="materials"),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("movement_type", sa.String(20), nullable=False),
        sa.Column("quantity_delta", sa.Numeric(15, 4), nullable=False),
        sa.Column("quantity_after", sa.Numeric(15, 4), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column("reference_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("payload", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("idx_stock_facts_tenant_product_date", "engine_stock_facts", ["tenant_id", "product_id", "occurred_at"])
    op.create_index("idx_stock_facts_tenant_type", "engine_stock_facts", ["tenant_id", "movement_type"])


def downgrade() -> None:
    op.drop_table("engine_stock_facts")
    op.drop_table("engine_sales_facts")
    op.drop_table("engine_delivery_routes")
    op.drop_table("engine_supplier_price_alerts")
    op.drop_table("engine_sales_suggestions")
    op.drop_table("engine_replenishment_suggestions")
    op.drop_table("engine_stock_alerts")

