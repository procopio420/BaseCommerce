"""
Repository helpers for engine-owned tables.

Simple CRUD operations for engine tables.
All methods are tenant-scoped.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from engines_core.persistence.models import (
    EngineStockAlert,
    EngineReplenishmentSuggestion,
    EngineSalesSuggestion,
    EngineSupplierPriceAlert,
)
from engines_core.persistence.facts import EngineSalesFact, EngineStockFact


class EngineRepository:
    """Repository for engine-owned tables."""

    def __init__(self, db: Session, tenant_id: UUID, vertical: str = "materials"):
        self.db = db
        self.tenant_id = tenant_id
        self.vertical = vertical

    # --- Stock Alerts ---

    def upsert_stock_alert(
        self,
        product_id: UUID,
        alert_type: str,
        risk_level: str,
        current_stock: Decimal,
        minimum_stock: Decimal,
        days_until_rupture: int | None = None,
        explanation: str | None = None,
        payload: dict | None = None,
    ) -> EngineStockAlert:
        """Upsert stock alert (one active alert per product)."""
        existing = (
            self.db.query(EngineStockAlert)
            .filter(
                EngineStockAlert.tenant_id == self.tenant_id,
                EngineStockAlert.product_id == product_id,
                EngineStockAlert.status == "active",
            )
            .first()
        )

        if existing:
            existing.alert_type = alert_type
            existing.risk_level = risk_level
            existing.current_stock = str(current_stock)
            existing.minimum_stock = str(minimum_stock)
            existing.days_until_rupture = str(days_until_rupture) if days_until_rupture else None
            existing.explanation = explanation
            existing.payload = payload or {}
            existing.updated_at = datetime.utcnow()
            self.db.flush()
            return existing

        alert = EngineStockAlert(
            tenant_id=self.tenant_id,
            vertical=self.vertical,
            product_id=product_id,
            alert_type=alert_type,
            risk_level=risk_level,
            current_stock=str(current_stock),
            minimum_stock=str(minimum_stock),
            days_until_rupture=str(days_until_rupture) if days_until_rupture else None,
            explanation=explanation,
            payload=payload or {},
        )
        self.db.add(alert)
        self.db.flush()
        return alert

    def get_stock_alerts(
        self,
        status: str = "active",
        risk_level: str | None = None,
        product_ids: list[UUID] | None = None,
    ) -> list[EngineStockAlert]:
        """Get stock alerts with filters."""
        query = self.db.query(EngineStockAlert).filter(
            EngineStockAlert.tenant_id == self.tenant_id,
            EngineStockAlert.status == status,
        )

        if risk_level:
            query = query.filter(EngineStockAlert.risk_level == risk_level)

        if product_ids:
            query = query.filter(EngineStockAlert.product_id.in_(product_ids))

        return query.order_by(EngineStockAlert.created_at.desc()).all()

    # --- Sales Facts ---

    def record_sales_fact(
        self,
        event_id: UUID,
        order_id: UUID,
        product_id: UUID,
        quantity: Decimal,
        unit_price: Decimal,
        total_value: Decimal,
        occurred_at: datetime,
        client_id: UUID | None = None,
        payload: dict | None = None,
    ) -> EngineSalesFact | None:
        """Record a sales fact (idempotent by event_id)."""
        # Check for existing fact (idempotency)
        existing = (
            self.db.query(EngineSalesFact)
            .filter(EngineSalesFact.event_id == event_id)
            .first()
        )
        if existing:
            return None  # Already processed

        fact = EngineSalesFact(
            tenant_id=self.tenant_id,
            vertical=self.vertical,
            event_id=event_id,
            order_id=order_id,
            product_id=product_id,
            client_id=client_id,
            quantity=quantity,
            unit_price=unit_price,
            total_value=total_value,
            occurred_at=occurred_at,
            payload=payload or {},
        )
        self.db.add(fact)
        self.db.flush()
        return fact

    def get_product_sales_history(
        self,
        product_id: UUID,
        days: int = 90,
    ) -> list[EngineSalesFact]:
        """Get sales history for a product."""
        date_limit = datetime.utcnow() - timedelta(days=days)

        return (
            self.db.query(EngineSalesFact)
            .filter(
                EngineSalesFact.tenant_id == self.tenant_id,
                EngineSalesFact.product_id == product_id,
                EngineSalesFact.occurred_at >= date_limit,
            )
            .order_by(EngineSalesFact.occurred_at.desc())
            .all()
        )

    def get_average_daily_sales(
        self,
        product_id: UUID,
        days: int = 90,
    ) -> Decimal:
        """Calculate average daily sales for a product."""
        date_limit = datetime.utcnow() - timedelta(days=days)

        total_quantity = (
            self.db.query(func.sum(EngineSalesFact.quantity))
            .filter(
                EngineSalesFact.tenant_id == self.tenant_id,
                EngineSalesFact.product_id == product_id,
                EngineSalesFact.occurred_at >= date_limit,
            )
            .scalar()
        ) or Decimal("0")

        if days > 0:
            return Decimal(str(total_quantity)) / Decimal(str(days))
        return Decimal("0")

    # --- Stock Facts ---

    def record_stock_fact(
        self,
        event_id: UUID,
        product_id: UUID,
        movement_type: str,
        quantity_delta: Decimal,
        occurred_at: datetime,
        quantity_after: Decimal | None = None,
        reference_id: UUID | None = None,
        payload: dict | None = None,
    ) -> EngineStockFact | None:
        """Record a stock fact (idempotent by event_id)."""
        # Check for existing fact (idempotency)
        existing = (
            self.db.query(EngineStockFact)
            .filter(EngineStockFact.event_id == event_id)
            .first()
        )
        if existing:
            return None  # Already processed

        fact = EngineStockFact(
            tenant_id=self.tenant_id,
            vertical=self.vertical,
            event_id=event_id,
            product_id=product_id,
            movement_type=movement_type,
            quantity_delta=quantity_delta,
            quantity_after=quantity_after,
            occurred_at=occurred_at,
            reference_id=reference_id,
            payload=payload or {},
        )
        self.db.add(fact)
        self.db.flush()
        return fact

    def get_current_stock(self, product_id: UUID) -> Decimal:
        """Get current stock level from facts (last known quantity_after)."""
        latest_fact = (
            self.db.query(EngineStockFact)
            .filter(
                EngineStockFact.tenant_id == self.tenant_id,
                EngineStockFact.product_id == product_id,
                EngineStockFact.quantity_after.isnot(None),
            )
            .order_by(EngineStockFact.occurred_at.desc())
            .first()
        )

        if latest_fact and latest_fact.quantity_after:
            return Decimal(str(latest_fact.quantity_after))

        # Fallback: sum all deltas
        total_delta = (
            self.db.query(func.sum(EngineStockFact.quantity_delta))
            .filter(
                EngineStockFact.tenant_id == self.tenant_id,
                EngineStockFact.product_id == product_id,
            )
            .scalar()
        ) or Decimal("0")

        return Decimal(str(total_delta))

    # --- Sales Suggestions ---

    def upsert_sales_suggestion(
        self,
        suggestion_type: str,
        suggested_product_id: UUID,
        source_product_id: UUID | None = None,
        frequency: Decimal | None = None,
        priority: str = "media",
        explanation: str | None = None,
        payload: dict | None = None,
    ) -> EngineSalesSuggestion:
        """Upsert sales suggestion."""
        existing = (
            self.db.query(EngineSalesSuggestion)
            .filter(
                EngineSalesSuggestion.tenant_id == self.tenant_id,
                EngineSalesSuggestion.suggestion_type == suggestion_type,
                EngineSalesSuggestion.source_product_id == source_product_id,
                EngineSalesSuggestion.suggested_product_id == suggested_product_id,
                EngineSalesSuggestion.status == "active",
            )
            .first()
        )

        if existing:
            existing.frequency = str(frequency) if frequency else None
            existing.priority = priority
            existing.explanation = explanation
            existing.payload = payload or {}
            existing.updated_at = datetime.utcnow()
            self.db.flush()
            return existing

        suggestion = EngineSalesSuggestion(
            tenant_id=self.tenant_id,
            vertical=self.vertical,
            suggestion_type=suggestion_type,
            source_product_id=source_product_id,
            suggested_product_id=suggested_product_id,
            frequency=str(frequency) if frequency else None,
            priority=priority,
            explanation=explanation,
            payload=payload or {},
        )
        self.db.add(suggestion)
        self.db.flush()
        return suggestion

    def get_sales_suggestions(
        self,
        suggestion_type: str | None = None,
        source_product_id: UUID | None = None,
        status: str = "active",
    ) -> list[EngineSalesSuggestion]:
        """Get sales suggestions with filters."""
        query = self.db.query(EngineSalesSuggestion).filter(
            EngineSalesSuggestion.tenant_id == self.tenant_id,
            EngineSalesSuggestion.status == status,
        )

        if suggestion_type:
            query = query.filter(EngineSalesSuggestion.suggestion_type == suggestion_type)

        if source_product_id:
            query = query.filter(EngineSalesSuggestion.source_product_id == source_product_id)

        return query.order_by(EngineSalesSuggestion.priority).all()

