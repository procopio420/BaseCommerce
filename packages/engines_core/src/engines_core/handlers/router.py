"""
Event Router - Routes events to appropriate engines.

This is the main entry point for event processing.
Maps event_type to engine processing methods.
"""

import logging
from typing import Any

from sqlalchemy.orm import Session

from engines_core.contracts.envelope import EventEnvelope
from engines_core.contracts.types import EventType
from engines_core.engines.stock import StockIntelligenceEngine
from engines_core.engines.sales import SalesIntelligenceEngine

logger = logging.getLogger(__name__)


class EventRouter:
    """
    Routes events to appropriate engines.

    Each event type can be processed by multiple engines.
    All processing is done within a single database transaction.
    """

    def __init__(self, db: Session):
        self.db = db
        self.stock_engine = StockIntelligenceEngine(db)
        self.sales_engine = SalesIntelligenceEngine(db)

    def handle(self, envelope: EventEnvelope) -> dict[str, Any]:
        """
        Handle an event by routing to appropriate engines.

        Args:
            envelope: Event envelope with payload

        Returns:
            Combined results from all engines that processed the event
        """
        event_type = envelope.event_type
        results = {"event_id": str(envelope.event_id), "event_type": event_type, "engines": {}}

        try:
            if event_type == EventType.SALE_RECORDED or event_type == "sale_recorded":
                # Stock engine: decrease stock, create alerts
                stock_result = self.stock_engine.process_sale_recorded(envelope)
                results["engines"]["stock"] = stock_result

                # Sales engine: record facts, update suggestions
                sales_result = self.sales_engine.process_sale_recorded(envelope)
                results["engines"]["sales"] = sales_result

            elif event_type == EventType.QUOTE_CONVERTED or event_type == "quote_converted":
                # Sales engine: record conversion
                sales_result = self.sales_engine.process_quote_converted(envelope)
                results["engines"]["sales"] = sales_result

            elif event_type == EventType.ORDER_STATUS_CHANGED or event_type == "order_status_changed":
                # Log status change, future: delivery engine
                logger.info(
                    f"Order status changed: {envelope.payload.get('order_id')}",
                    extra={
                        "tenant_id": str(envelope.tenant_id),
                        "old_status": envelope.payload.get("old_status"),
                        "new_status": envelope.payload.get("new_status"),
                    },
                )
                results["engines"]["delivery"] = {"status": "logged"}

            elif event_type == EventType.STOCK_UPDATED or event_type == "stock_updated":
                # Future: handle stock updates (receipts, adjustments)
                logger.info(f"Stock updated event received")
                results["engines"]["stock"] = {"status": "logged"}

            else:
                logger.warning(f"Unknown event type: {event_type}")
                results["warning"] = f"No handlers for event type: {event_type}"

            results["status"] = "success"

        except Exception as e:
            logger.error(
                f"Error processing event {envelope.event_id}",
                extra={
                    "event_id": str(envelope.event_id),
                    "event_type": event_type,
                    "error": str(e),
                },
                exc_info=True,
            )
            results["status"] = "error"
            results["error"] = str(e)
            raise

        return results


def handle_event(db: Session, envelope: EventEnvelope) -> dict[str, Any]:
    """
    Convenience function to handle an event.

    Args:
        db: Database session
        envelope: Event envelope

    Returns:
        Processing results
    """
    router = EventRouter(db)
    return router.handle(envelope)

