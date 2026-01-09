"""
Event Types - Known event types for engines.

These event types are vertical-agnostic. The vertical name is in the envelope,
and the event_type indicates the action.
"""

from enum import Enum


class EventType(str, Enum):
    """
    Known event types for engines.

    Format: action_performed (e.g., quote_converted, sale_recorded)
    These are consistent across verticals.
    """

    # Quote/Order lifecycle events
    QUOTE_CREATED = "quote_created"
    QUOTE_CONVERTED = "quote_converted"
    SALE_RECORDED = "sale_recorded"
    ORDER_STATUS_CHANGED = "order_status_changed"

    # Stock events
    STOCK_UPDATED = "stock_updated"
    STOCK_RECEIVED = "stock_received"

    # Pricing events
    SUPPLIER_PRICE_REGISTERED = "supplier_price_registered"
    PRODUCT_PRICE_UPDATED = "product_price_updated"

    # Delivery events
    DELIVERY_STARTED = "delivery_started"
    DELIVERY_COMPLETED = "delivery_completed"

    def __str__(self) -> str:
        return self.value

