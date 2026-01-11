"""
WhatsApp Event Types

Events published and consumed by the WhatsApp Messaging Engine.
"""

from enum import Enum


class WhatsAppEventType(str, Enum):
    """
    Event types for WhatsApp Messaging Engine.

    PUBLISHED by this engine:
    - INBOUND_RECEIVED: Customer sent a message
    - ACTION_REQUESTED: Customer requested an action (quote, status, human)
    - CUSTOMER_OPTED_OUT: Customer opted out of messages
    - DELIVERY_FAILED: Message delivery failed
    - DELIVERY_CONFIRMED: Message delivery confirmed

    CONSUMED by this engine (from verticals):
    - Uses existing EventType from engines_core (QUOTE_CREATED, ORDER_STATUS_CHANGED, etc)
    """

    # Events this engine PUBLISHES
    INBOUND_RECEIVED = "whatsapp_inbound_received"
    ACTION_REQUESTED = "whatsapp_action_requested"
    CUSTOMER_OPTED_OUT = "whatsapp_customer_opted_out"
    DELIVERY_FAILED = "whatsapp_delivery_failed"
    DELIVERY_CONFIRMED = "whatsapp_delivery_confirmed"

    # Internal events for outbound queue
    OUTBOUND_QUEUED = "whatsapp_outbound_queued"

    def __str__(self) -> str:
        return self.value


# Events from verticals that trigger WhatsApp notifications
VERTICAL_EVENTS_TO_NOTIFY = {
    "quote_created": "quote_created_template",
    "quote_sent": "quote_sent_template",
    "order_created": "order_created_template",
    "order_status_changed": "order_status_template",
    "delivery_started": "delivery_started_template",
    "delivery_completed": "delivery_completed_template",
}

