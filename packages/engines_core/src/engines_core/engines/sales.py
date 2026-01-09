"""
Sales Intelligence Engine

Computes sales suggestions based ONLY on engine-owned facts tables.
No vertical table access.
"""

import logging
from collections import defaultdict
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid5

from sqlalchemy import func
from sqlalchemy.orm import Session

from engines_core.contracts.envelope import EventEnvelope
from engines_core.persistence.facts import EngineSalesFact
from engines_core.persistence.repo import EngineRepository

logger = logging.getLogger(__name__)


class SalesIntelligenceEngine:
    """
    Sales Intelligence Engine.

    Computes:
    - Complementary product suggestions
    - Purchase patterns

    Based ONLY on engine_sales_facts table.
    """

    def __init__(self, db: Session):
        self.db = db

    def process_sale_recorded(self, envelope: EventEnvelope) -> dict[str, Any]:
        """
        Process a sale_recorded event.

        1. Record sales facts (if not already done by stock engine)
        2. Update product association statistics
        3. Recompute suggestions for affected products

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

        # Extract product IDs from this order
        product_ids = [UUID(item["product_id"]) for item in items]

        if len(product_ids) < 2:
            # Need at least 2 products for associations
            return {
                "order_id": str(order_id),
                "products": len(product_ids),
                "suggestions_updated": 0,
            }

        # Record sales facts (idempotent)
        for item in items:
            product_id = UUID(item["product_id"])
            quantity = Decimal(str(item["quantity"]))
            unit_price = Decimal(str(item.get("unit_price", 0)))
            total_value = Decimal(str(item.get("total_value", quantity * unit_price)))

            item_event_id = uuid5(envelope.event_id, str(product_id))

            repo.record_sales_fact(
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

        # Recompute product associations for products in this order
        suggestions_updated = self._update_product_associations(repo, tenant_id, product_ids)

        self.db.commit()

        logger.info(
            f"Sales engine processed sale_recorded: order_id={order_id}",
            extra={
                "tenant_id": str(tenant_id),
                "order_id": str(order_id),
                "products": len(product_ids),
                "suggestions_updated": suggestions_updated,
            },
        )

        return {
            "order_id": str(order_id),
            "products": len(product_ids),
            "suggestions_updated": suggestions_updated,
        }

    def process_quote_converted(self, envelope: EventEnvelope) -> dict[str, Any]:
        """
        Process a quote_converted event.

        Records the conversion for future analysis.
        Actual suggestions are computed when sale is recorded (delivered).
        """
        tenant_id = envelope.tenant_id
        payload = envelope.payload

        order_id = payload.get("order_id")
        quote_id = payload.get("quote_id")

        logger.info(
            f"Sales engine processed quote_converted: quote_id={quote_id}",
            extra={
                "tenant_id": str(tenant_id),
                "quote_id": quote_id,
                "order_id": order_id,
            },
        )

        return {
            "quote_id": quote_id,
            "order_id": order_id,
            "status": "recorded",
        }

    def _update_product_associations(
        self,
        repo: EngineRepository,
        tenant_id: UUID,
        product_ids: list[UUID],
    ) -> int:
        """
        Update product association suggestions based on sales facts.

        For each product, find other products frequently bought together.

        Returns:
            Number of suggestions updated
        """
        date_limit = datetime.utcnow() - timedelta(days=90)
        suggestions_updated = 0

        for product_id in product_ids:
            # Find all orders containing this product (from facts)
            order_ids_with_product = (
                self.db.query(EngineSalesFact.order_id)
                .filter(
                    EngineSalesFact.tenant_id == tenant_id,
                    EngineSalesFact.product_id == product_id,
                    EngineSalesFact.occurred_at >= date_limit,
                )
                .distinct()
                .all()
            )

            order_ids = [o[0] for o in order_ids_with_product]

            if not order_ids:
                continue

            # Count co-occurrences with other products
            co_occurrences = defaultdict(int)

            for order_id in order_ids:
                # Get all products in this order
                other_products = (
                    self.db.query(EngineSalesFact.product_id)
                    .filter(
                        EngineSalesFact.tenant_id == tenant_id,
                        EngineSalesFact.order_id == order_id,
                        EngineSalesFact.product_id != product_id,
                    )
                    .distinct()
                    .all()
                )

                for (other_product_id,) in other_products:
                    co_occurrences[other_product_id] += 1

            total_orders = len(order_ids)

            # Create suggestions for products with frequency >= 20%
            for other_product_id, count in co_occurrences.items():
                frequency = (Decimal(str(count)) / Decimal(str(total_orders))) * Decimal("100")

                if frequency < Decimal("20"):
                    continue

                # Determine priority
                if frequency >= Decimal("70"):
                    priority = "alta"
                elif frequency >= Decimal("40"):
                    priority = "media"
                else:
                    priority = "baixa"

                explanation = f"{frequency:.0f}% dos pedidos com este produto também contêm o produto sugerido"

                repo.upsert_sales_suggestion(
                    suggestion_type="complementary",
                    source_product_id=product_id,
                    suggested_product_id=other_product_id,
                    frequency=frequency,
                    priority=priority,
                    explanation=explanation,
                    payload={
                        "total_orders": total_orders,
                        "co_occurrences": count,
                    },
                )
                suggestions_updated += 1

        return suggestions_updated

