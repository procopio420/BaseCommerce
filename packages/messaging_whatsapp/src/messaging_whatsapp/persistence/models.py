"""
WhatsApp Engine Database Models

Tables owned by the WhatsApp Messaging Engine.
These are independent from vertical tables.

Tables:
- whatsapp_tenant_bindings: Maps tenants to WhatsApp Business accounts
- whatsapp_conversations: Tracks conversation state with customers
- whatsapp_messages: Stores all inbound/outbound messages
- whatsapp_optouts: Tracks customers who opted out
"""

from datetime import datetime
from enum import Enum
from uuid import uuid4

from sqlalchemy import Boolean, Column, DateTime, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.declarative import declarative_base

WhatsAppBase = declarative_base()


class ConversationStatus(str, Enum):
    """Status of a WhatsApp conversation."""

    ACTIVE = "active"
    WAITING_RESPONSE = "waiting_response"
    HUMAN_ASSIGNED = "human_assigned"
    CLOSED = "closed"


class MessageDirection(str, Enum):
    """Direction of a WhatsApp message."""

    INBOUND = "in"
    OUTBOUND = "out"


class MessageStatus(str, Enum):
    """Status of a WhatsApp message."""

    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"


class WhatsAppModelMixin:
    """Common fields for all WhatsApp engine models."""

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class WhatsAppTenantBinding(WhatsAppBase, WhatsAppModelMixin):
    """
    Maps a tenant to a WhatsApp provider (Meta Cloud API or Evolution API).

    Each tenant can have multiple WhatsApp bindings.
    The phone_number_id (Meta) or instance_name (Evolution) is used to route incoming webhooks.
    """

    __tablename__ = "whatsapp_tenant_bindings"

    provider = Column(String(50), nullable=False, default="meta")  # meta, evolution, stub
    
    # Meta Cloud API fields
    phone_number_id = Column(String(100), nullable=True)  # From Meta API (nullable for Evolution)
    waba_id = Column(String(100), nullable=True)  # WhatsApp Business Account ID (nullable for Evolution)
    access_token_encrypted = Column(Text, nullable=True)  # Encrypted access token (Meta)
    webhook_verify_token = Column(String(100), nullable=True)  # For webhook verification (Meta)
    
    # Evolution API fields
    instance_name = Column(String(100), nullable=True)  # Evolution instance name
    api_key = Column(Text, nullable=True)  # Evolution API key (encrypted)
    api_url = Column(String(255), nullable=True)  # Evolution API base URL
    
    # Common fields
    display_number = Column(String(20), nullable=False)  # Human-readable number
    is_active = Column(Boolean, nullable=False, default=True)
    config = Column(JSONB, nullable=False, default=dict)  # Provider-specific config

    __table_args__ = (
        UniqueConstraint("phone_number_id", name="uq_whatsapp_bindings_phone_number_id"),
        UniqueConstraint("instance_name", name="uq_whatsapp_bindings_instance_name"),
        Index("idx_whatsapp_bindings_tenant_active", "tenant_id", "is_active"),
        Index("idx_whatsapp_bindings_provider", "provider"),
    )


class WhatsAppConversation(WhatsAppBase, WhatsAppModelMixin):
    """
    Tracks a conversation with a customer.

    A conversation is identified by tenant_id + customer_phone.
    Stores state machine information for automation.
    """

    __tablename__ = "whatsapp_conversations"

    customer_phone = Column(String(20), nullable=False)  # E.164 format
    customer_name = Column(String(255), nullable=True)  # From WhatsApp profile
    status = Column(String(20), nullable=False, default=ConversationStatus.ACTIVE.value)
    current_state = Column(String(50), nullable=True)  # State machine state
    assigned_user_id = Column(PGUUID(as_uuid=True), nullable=True)  # Human agent assigned
    last_message_at = Column(DateTime(timezone=True), nullable=True)
    last_inbound_at = Column(DateTime(timezone=True), nullable=True)
    last_outbound_at = Column(DateTime(timezone=True), nullable=True)
    message_count = Column(String(10), nullable=False, default="0")
    context = Column(JSONB, nullable=False, default=dict)  # Conversation context/metadata

    __table_args__ = (
        UniqueConstraint("tenant_id", "customer_phone", name="uq_whatsapp_conversations_tenant_phone"),
        Index("idx_whatsapp_conversations_tenant_status", "tenant_id", "status"),
        Index("idx_whatsapp_conversations_tenant_last_message", "tenant_id", "last_message_at"),
    )


class WhatsAppMessage(WhatsAppBase, WhatsAppModelMixin):
    """
    Stores all WhatsApp messages (inbound and outbound).

    Provider message IDs are used for idempotency.
    """

    __tablename__ = "whatsapp_messages"

    conversation_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)
    direction = Column(String(3), nullable=False)  # 'in' or 'out'
    provider_message_id = Column(String(100), nullable=True)  # From provider (for dedup)
    message_type = Column(String(20), nullable=False, default="text")
    content = Column(Text, nullable=True)  # Text content
    content_json = Column(JSONB, nullable=False, default=dict)  # Full message content
    status = Column(String(20), nullable=False, default=MessageStatus.PENDING.value)
    status_updated_at = Column(DateTime(timezone=True), nullable=True)
    error_code = Column(String(50), nullable=True)
    error_message = Column(Text, nullable=True)
    template_name = Column(String(100), nullable=True)  # For outbound templates
    reply_to_message_id = Column(String(100), nullable=True)  # Context for replies
    triggered_by_event_id = Column(PGUUID(as_uuid=True), nullable=True)  # Event that caused outbound

    __table_args__ = (
        UniqueConstraint("provider_message_id", name="uq_whatsapp_messages_provider_id"),
        Index("idx_whatsapp_messages_tenant_conversation", "tenant_id", "conversation_id"),
        Index("idx_whatsapp_messages_tenant_direction", "tenant_id", "direction"),
        Index("idx_whatsapp_messages_tenant_status", "tenant_id", "status"),
        Index("idx_whatsapp_messages_tenant_created", "tenant_id", "created_at"),
    )


class WhatsAppOptOut(WhatsAppBase, WhatsAppModelMixin):
    """
    Tracks customers who have opted out of WhatsApp messages.

    Once opted out, no messages should be sent to this phone number for this tenant.
    """

    __tablename__ = "whatsapp_optouts"

    customer_phone = Column(String(20), nullable=False)  # E.164 format
    reason = Column(String(50), nullable=False)  # Keyword used (STOP, SAIR, etc)
    original_message_id = Column(String(100), nullable=True)  # Message that triggered opt-out
    is_active = Column(Boolean, nullable=False, default=True)  # Can be reactivated
    reactivated_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("tenant_id", "customer_phone", name="uq_whatsapp_optouts_tenant_phone"),
        Index("idx_whatsapp_optouts_tenant_active", "tenant_id", "is_active"),
    )

