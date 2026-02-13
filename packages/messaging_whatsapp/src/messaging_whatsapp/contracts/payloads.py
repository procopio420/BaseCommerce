"""
WhatsApp Payload Models

Pydantic models for all WhatsApp event payloads.
These are used in Redis Stream messages and for validation.
"""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class MessageType(str, Enum):
    """Types of WhatsApp messages."""

    TEXT = "text"
    IMAGE = "image"
    DOCUMENT = "document"
    AUDIO = "audio"
    VIDEO = "video"
    STICKER = "sticker"
    LOCATION = "location"
    CONTACTS = "contacts"
    INTERACTIVE = "interactive"
    BUTTON = "button"
    TEMPLATE = "template"
    UNKNOWN = "unknown"


class ActionIntent(str, Enum):
    """Intents detected from customer messages or button clicks."""

    CREATE_QUOTE = "create_quote"
    ORDER_STATUS = "order_status"
    TALK_TO_HUMAN = "talk_to_human"
    OPT_OUT = "opt_out"
    UNKNOWN = "unknown"


class DeliveryStatus(str, Enum):
    """WhatsApp message delivery status."""

    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"


class InboundMessagePayload(BaseModel):
    """
    Payload for WHATSAPP_INBOUND_RECEIVED event.

    Contains all information about an incoming WhatsApp message.
    """

    from_phone: str = Field(..., description="Customer phone number (E.164 format)")
    to_phone: str = Field(..., description="Business phone number (E.164 format)")
    phone_number_id: str = Field(..., description="WhatsApp Business phone number ID")
    waba_id: str = Field(..., description="WhatsApp Business Account ID")
    message_id: str = Field(..., description="Provider message ID")
    message_type: MessageType = Field(..., description="Type of message")
    text: str | None = Field(None, description="Text content (for text messages)")
    media_url: str | None = Field(None, description="Media URL (for media messages)")
    media_mime_type: str | None = Field(None, description="Media MIME type")
    caption: str | None = Field(None, description="Media caption")
    timestamp: datetime = Field(..., description="Message timestamp from provider")
    context_message_id: str | None = Field(None, description="Replied-to message ID")
    raw_payload: dict[str, Any] = Field(default_factory=dict, description="Raw provider payload")

    # Resolved context (filled by engine after tenant resolution)
    conversation_id: UUID | None = Field(None, description="Conversation ID in our system")
    customer_name: str | None = Field(None, description="Customer name from WhatsApp profile")


class OutboundMessagePayload(BaseModel):
    """
    Payload for WHATSAPP_OUTBOUND_QUEUED event.

    Contains all information needed to send a WhatsApp message.
    """

    to_phone: str = Field(..., description="Recipient phone number (E.164 format)")
    message_type: MessageType = Field(default=MessageType.TEXT, description="Type of message")

    # For text messages
    text: str | None = Field(None, description="Text content")

    # For template messages
    template_name: str | None = Field(None, description="Template name")
    template_language: str = Field(default="pt_BR", description="Template language code")
    template_variables: dict[str, str] = Field(default_factory=dict, description="Template variables")

    # For interactive messages (buttons)
    buttons: list[dict[str, str]] | None = Field(None, description="Interactive buttons")

    # Reply context
    reply_to_message_id: str | None = Field(None, description="Message ID to reply to")

    # Metadata
    conversation_id: UUID | None = Field(None, description="Conversation ID")
    triggered_by_event_id: UUID | None = Field(None, description="Event that triggered this message")
    priority: str = Field(default="normal", description="Message priority (normal, high)")


class ActionRequestedPayload(BaseModel):
    """
    Payload for WHATSAPP_ACTION_REQUESTED event.

    Published when customer requests a specific action (via button or keyword).
    """

    intent: ActionIntent = Field(..., description="Detected intent")
    from_phone: str = Field(..., description="Customer phone number")
    conversation_id: UUID | None = Field(None, description="Conversation ID")
    original_message_id: str = Field(..., description="Message that triggered the action")
    original_text: str | None = Field(None, description="Original message text")

    # Context that may help the vertical handle the request
    context: dict[str, Any] = Field(default_factory=dict, description="Additional context")


class DeliveryStatusPayload(BaseModel):
    """
    Payload for WHATSAPP_DELIVERY_* events.

    Contains delivery status information from the provider.
    """

    provider_message_id: str = Field(..., description="Provider message ID")
    our_message_id: UUID | None = Field(None, description="Our internal message ID")
    status: DeliveryStatus = Field(..., description="Delivery status")
    timestamp: datetime = Field(..., description="Status timestamp")
    recipient_phone: str = Field(..., description="Recipient phone number")
    error_code: str | None = Field(None, description="Error code (if failed)")
    error_message: str | None = Field(None, description="Error message (if failed)")
    conversation_id: UUID | None = Field(None, description="Conversation ID")


class OptOutPayload(BaseModel):
    """
    Payload for WHATSAPP_CUSTOMER_OPTED_OUT event.

    Published when customer opts out of WhatsApp messages.
    """

    phone: str = Field(..., description="Customer phone number")
    reason: str = Field(..., description="Opt-out reason/keyword used")
    original_message_id: str = Field(..., description="Message that triggered opt-out")
    timestamp: datetime = Field(..., description="Opt-out timestamp")
    conversation_id: UUID | None = Field(None, description="Conversation ID")




