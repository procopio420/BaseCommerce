"""
Stock Intelligence Engine

Computes stock alerts and replenishment suggestions based ONLY on
engine-owned facts tables. No vertical table access.
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from engines_core.contracts.envelope import EventEnvelope
from engines_core.persistence.repo import EngineRepository

logger = logging.getLogger(__name__)


class StockIntelligenceEngine:
    """
    Stock Intelligence Engine.

    Computes:
    - Stock alerts (rupture risk, excess)
    - Replenishment suggestions

    Based ONLY on engine_sales_facts and engine_stock_facts tables.
    """

    # Default parameters (can be overridden per tenant/product)
    DEFAULT_LEAD_TIME_DAYS = 7
    DEFAULT_SAFETY_STOCK_PERCENT = Decimal("20")

    def __init__(self, db: Session):
        self.db = db

    def process_sale_recorded(self, envelope: EventEnvelope) -> dict[str, Any]:
        """
        Process a sale_recorded event.

        1. Record stock facts (decrease stock for each item)
        2. Record sales facts (for history)
        3. Recompute alerts for affected products

        Args:
            envelope: Event envelope with full payload

        Returns:
            Processing result summary
        """
        tenant_id = envelope.tenant_id
        vertical = envelope.vertical
        payload = envelope.payload

        repo = EngineRepository(self.db, tenant_id, vertical)

        order_id = UUID(payload["order_id"])
        items = payload.get("items", [])
        delivered_at = datetime.fromisoformat(payload.get("delivered_at", envelope.occurred_at.isoformat()))
        client_id = UUID(payload["client_id"]) if payload.get("client_id") else None

        processed_items = 0
        alerts_created = 0

        for item in items:
            product_id = UUID(item["product_id"])
            quantity = Decimal(str(item["quantity"]))
            unit_price = Decimal(str(item.get("unit_price", 0)))
            total_value = Decimal(str(item.get("total_value", quantity * unit_price)))

            # Record sales fact (idempotent by event_id + product combination)
            # Use a derived event_id for each item
            from uuid import uuid5, NAMESPACE_DNS
            item_event_id = uuid5(envelope.event_id, str(product_id))

            sales_fact = repo.record_sales_fact(
                event_id=item_event_id,
                order_id=order_id,
                product_id=product_id,
                quantity=quantity,
                unit_price=unit_price,
                total_value=total_value,
                occurred_at=delivered_at,
                client_id=client_id,
                payload=item,
            )

            if sales_fact:
                # Record stock movement (decrease)
                current_stock = repo.get_current_stock(product_id)
                new_stock = current_stock - quantity
                if new_stock < 0:
                    new_stock = Decimal("0")

                stock_event_id = uuid5(envelope.event_id, f"stock_{product_id}")
                repo.record_stock_fact(
                    event_id=stock_event_id,
                    product_id=product_id,
                    movement_type="sale",
                    quantity_delta=-quantity,
                    quantity_after=new_stock,
                    occurred_at=delivered_at,
                    reference_id=order_id,
                    payload={"order_id": str(order_id), "quantity_sold": str(quantity)},
                )

                # Recompute alert for this product
                alert = self._compute_stock_alert(repo, product_id)
                if alert:
                    alerts_created += 1

                processed_items += 1

        self.db.commit()

        logger.info(
            f"Stock engine processed sale_recorded: order_id={order_id}",
            extra={
                "tenant_id": str(tenant_id),
                "order_id": str(order_id),
                "items_processed": processed_items,
                "alerts_created": alerts_created,
            },
        )

        return {
            "order_id": str(order_id),
            "items_processed": processed_items,
            "alerts_created": alerts_created,
        }

    def _compute_stock_alert(
        self,
        repo: EngineRepository,
        product_id: UUID,
    ) -> bool:
        """
        Compute stock alert for a product.

        Uses average daily sales from facts to determine risk.

        Returns:
            True if alert was created/updated
        """
        # Get current stock
        current_stock = repo.get_current_stock(product_id)

        # Get average daily sales (last 90 days)
        avg_daily_sales = repo.get_average_daily_sales(product_id, days=90)

        if avg_daily_sales <= 0:
            # No sales history, no alert needed
            return False

        # Calculate minimum stock (lead time + safety stock)
        lead_time = self.DEFAULT_LEAD_TIME_DAYS
        safety_percent = self.DEFAULT_SAFETY_STOCK_PERCENT

        min_stock = avg_daily_sales * Decimal(str(lead_time))
        min_stock = min_stock * (1 + safety_percent / 100)

        if current_stock >= min_stock:
            # Stock is sufficient, no alert
            return False

        # Calculate days until rupture
        days_until_rupture = None
        if avg_daily_sales > 0:
            days_until_rupture = int(current_stock / avg_daily_sales)

        # Determine risk level
        if days_until_rupture is not None and days_until_rupture <= 7:
            risk_level = "alto"
        elif days_until_rupture is not None and days_until_rupture <= 14:
            risk_level = "medio"
        else:
            risk_level = "baixo"

        explanation = (
            f"Estoque atual: {current_stock:.2f}, "
            f"Média de vendas: {avg_daily_sales:.2f}/dia, "
            f"Lead time: {lead_time} dias, "
            f"Estoque mínimo sugerido: {min_stock:.2f}"
        )
        if days_until_rupture is not None:
            explanation += f". Ruptura estimada em {days_until_rupture} dias."

        repo.upsert_stock_alert(
            product_id=product_id,
            alert_type="rupture",
            risk_level=risk_level,
            current_stock=current_stock,
            minimum_stock=min_stock,
            days_until_rupture=days_until_rupture,
            explanation=explanation,
            payload={
                "avg_daily_sales": str(avg_daily_sales),
                "lead_time_days": lead_time,
                "safety_stock_percent": str(safety_percent),
            },
        )

        return True

