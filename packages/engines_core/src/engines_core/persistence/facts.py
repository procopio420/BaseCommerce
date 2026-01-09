"""
Engine facts tables - normalized event-derived data.

Facts are populated from events and provide a data boundary between
verticals and engines. Engines operate ONLY on facts tables, never
querying vertical tables directly.

This creates true data independence:
- Events arrive with full payload
- Facts are extracted and stored
- Engine computations use facts only
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, DateTime, Index, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from engines_core.persistence.models import EngineBase, EngineModelMixin


class EngineSalesFact(EngineBase, EngineModelMixin):
    """
    Sales facts derived from sale_recorded events.

    Each row represents a product sold in a delivery.
    Used by:
    - Stock Intelligence (consumption history)
    - Sales Intelligence (purchase patterns, complementary products)
    """

    __tablename__ = "engine_sales_facts"

    order_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)
    product_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)
    client_id = Column(PGUUID(as_uuid=True), nullable=True, index=True)
    quantity = Column(Numeric(15, 4), nullable=False)
    unit_price = Column(Numeric(15, 4), nullable=False)
    total_value = Column(Numeric(15, 4), nullable=False)
    occurred_at = Column(DateTime(timezone=True), nullable=False)
    event_id = Column(PGUUID(as_uuid=True), nullable=False, unique=True)  # Idempotency key
    payload = Column(JSONB, nullable=False, default=dict)

    __table_args__ = (
        Index("idx_sales_facts_tenant_product_date", "tenant_id", "product_id", "occurred_at"),
        Index("idx_sales_facts_tenant_client", "tenant_id", "client_id"),
        Index("idx_sales_facts_tenant_order", "tenant_id", "order_id"),
    )


class EngineStockFact(EngineBase, EngineModelMixin):
    """
    Stock facts derived from stock_updated and sale_recorded events.

    Each row represents a stock movement (in/out/adjustment).
    Used by:
    - Stock Intelligence (current stock, movement history)
    """

    __tablename__ = "engine_stock_facts"

    product_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)
    movement_type = Column(String(20), nullable=False)  # "sale", "received", "adjustment"
    quantity_delta = Column(Numeric(15, 4), nullable=False)  # Positive=in, Negative=out
    quantity_after = Column(Numeric(15, 4), nullable=True)  # Current stock after movement
    occurred_at = Column(DateTime(timezone=True), nullable=False)
    event_id = Column(PGUUID(as_uuid=True), nullable=False, unique=True)  # Idempotency key
    reference_id = Column(PGUUID(as_uuid=True), nullable=True)  # order_id, receipt_id, etc.
    payload = Column(JSONB, nullable=False, default=dict)

    __table_args__ = (
        Index("idx_stock_facts_tenant_product_date", "tenant_id", "product_id", "occurred_at"),
        Index("idx_stock_facts_tenant_type", "tenant_id", "movement_type"),
    )

