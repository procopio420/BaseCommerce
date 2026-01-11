"""
WhatsApp Repository

Repository pattern for WhatsApp engine database operations.
Provides CRUD operations and common queries for WhatsApp tables.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from messaging_whatsapp.persistence.models import (
    ConversationStatus,
    MessageDirection,
    MessageStatus,
    WhatsAppConversation,
    WhatsAppMessage,
    WhatsAppOptOut,
    WhatsAppTenantBinding,
)


class WhatsAppRepository:
    """Repository for WhatsApp engine database operations."""

    def __init__(self, db: Session):
        self.db = db

    # =========================================================================
    # Tenant Bindings
    # =========================================================================

    def get_binding_by_phone_number_id(self, phone_number_id: str) -> WhatsAppTenantBinding | None:
        """Get tenant binding by WhatsApp phone number ID."""
        return (
            self.db.query(WhatsAppTenantBinding)
            .filter(
                WhatsAppTenantBinding.phone_number_id == phone_number_id,
                WhatsAppTenantBinding.is_active == True,  # noqa: E712
            )
            .first()
        )

    def get_active_binding_for_tenant(self, tenant_id: UUID) -> WhatsAppTenantBinding | None:
        """Get the active binding for a tenant."""
        return (
            self.db.query(WhatsAppTenantBinding)
            .filter(
                WhatsAppTenantBinding.tenant_id == tenant_id,
                WhatsAppTenantBinding.is_active == True,  # noqa: E712
            )
            .first()
        )

    def get_all_bindings_for_tenant(self, tenant_id: UUID) -> list[WhatsAppTenantBinding]:
        """Get all bindings for a tenant."""
        return (
            self.db.query(WhatsAppTenantBinding)
            .filter(WhatsAppTenantBinding.tenant_id == tenant_id)
            .all()
        )

    def create_binding(
        self,
        tenant_id: UUID,
        phone_number_id: str,
        waba_id: str,
        display_number: str,
        provider: str = "meta",
        access_token_encrypted: str | None = None,
        webhook_verify_token: str | None = None,
        config: dict[str, Any] | None = None,
    ) -> WhatsAppTenantBinding:
        """Create a new tenant binding."""
        binding = WhatsAppTenantBinding(
            tenant_id=tenant_id,
            provider=provider,
            phone_number_id=phone_number_id,
            waba_id=waba_id,
            display_number=display_number,
            access_token_encrypted=access_token_encrypted,
            webhook_verify_token=webhook_verify_token,
            config=config or {},
        )
        self.db.add(binding)
        return binding

    # =========================================================================
    # Conversations
    # =========================================================================

    def get_conversation(self, tenant_id: UUID, customer_phone: str) -> WhatsAppConversation | None:
        """Get conversation by tenant and customer phone."""
        return (
            self.db.query(WhatsAppConversation)
            .filter(
                WhatsAppConversation.tenant_id == tenant_id,
                WhatsAppConversation.customer_phone == customer_phone,
            )
            .first()
        )

    def get_conversation_by_id(self, conversation_id: UUID) -> WhatsAppConversation | None:
        """Get conversation by ID."""
        return (
            self.db.query(WhatsAppConversation)
            .filter(WhatsAppConversation.id == conversation_id)
            .first()
        )

    def get_or_create_conversation(
        self,
        tenant_id: UUID,
        customer_phone: str,
        customer_name: str | None = None,
    ) -> tuple[WhatsAppConversation, bool]:
        """
        Get existing conversation or create a new one.

        Returns:
            Tuple of (conversation, created) where created is True if new.
        """
        conversation = self.get_conversation(tenant_id, customer_phone)
        if conversation:
            return conversation, False

        conversation = WhatsAppConversation(
            tenant_id=tenant_id,
            customer_phone=customer_phone,
            customer_name=customer_name,
            status=ConversationStatus.ACTIVE.value,
        )
        self.db.add(conversation)
        return conversation, True

    def update_conversation_last_message(
        self,
        conversation: WhatsAppConversation,
        direction: MessageDirection,
        timestamp: datetime | None = None,
    ) -> None:
        """Update conversation timestamps after a message."""
        now = timestamp or datetime.utcnow()
        conversation.last_message_at = now
        conversation.updated_at = now

        if direction == MessageDirection.INBOUND:
            conversation.last_inbound_at = now
        else:
            conversation.last_outbound_at = now

        # Increment message count
        current_count = int(conversation.message_count or "0")
        conversation.message_count = str(current_count + 1)

    def list_conversations(
        self,
        tenant_id: UUID,
        status: ConversationStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[WhatsAppConversation]:
        """List conversations for a tenant."""
        query = self.db.query(WhatsAppConversation).filter(
            WhatsAppConversation.tenant_id == tenant_id
        )

        if status:
            query = query.filter(WhatsAppConversation.status == status.value)

        return (
            query.order_by(WhatsAppConversation.last_message_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    # =========================================================================
    # Messages
    # =========================================================================

    def get_message_by_provider_id(self, provider_message_id: str) -> WhatsAppMessage | None:
        """Get message by provider message ID (for idempotency)."""
        return (
            self.db.query(WhatsAppMessage)
            .filter(WhatsAppMessage.provider_message_id == provider_message_id)
            .first()
        )

    def is_message_processed(self, provider_message_id: str) -> bool:
        """Check if a message has already been processed (idempotency)."""
        result = self.db.execute(
            text("SELECT 1 FROM whatsapp_messages WHERE provider_message_id = :id LIMIT 1"),
            {"id": provider_message_id},
        )
        return result.fetchone() is not None

    def create_message(
        self,
        tenant_id: UUID,
        conversation_id: UUID,
        direction: MessageDirection,
        message_type: str,
        content: str | None = None,
        content_json: dict[str, Any] | None = None,
        provider_message_id: str | None = None,
        status: MessageStatus = MessageStatus.PENDING,
        template_name: str | None = None,
        reply_to_message_id: str | None = None,
        triggered_by_event_id: UUID | None = None,
    ) -> WhatsAppMessage:
        """Create a new message record."""
        message = WhatsAppMessage(
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            direction=direction.value,
            message_type=message_type,
            content=content,
            content_json=content_json or {},
            provider_message_id=provider_message_id,
            status=status.value,
            template_name=template_name,
            reply_to_message_id=reply_to_message_id,
            triggered_by_event_id=triggered_by_event_id,
        )
        self.db.add(message)
        return message

    def update_message_status(
        self,
        message: WhatsAppMessage,
        status: MessageStatus,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> None:
        """Update message status."""
        message.status = status.value
        message.status_updated_at = datetime.utcnow()
        if error_code:
            message.error_code = error_code
        if error_message:
            message.error_message = error_message

    def update_message_provider_id(
        self,
        message: WhatsAppMessage,
        provider_message_id: str,
    ) -> None:
        """Set the provider message ID after sending."""
        message.provider_message_id = provider_message_id

    def get_recent_messages(
        self,
        conversation_id: UUID,
        limit: int = 20,
    ) -> list[WhatsAppMessage]:
        """Get recent messages for a conversation."""
        return (
            self.db.query(WhatsAppMessage)
            .filter(WhatsAppMessage.conversation_id == conversation_id)
            .order_by(WhatsAppMessage.created_at.desc())
            .limit(limit)
            .all()
        )

    # =========================================================================
    # Opt-outs
    # =========================================================================

    def is_opted_out(self, tenant_id: UUID, phone: str) -> bool:
        """Check if a phone number is opted out for this tenant."""
        result = self.db.execute(
            text("""
                SELECT 1 FROM whatsapp_optouts 
                WHERE tenant_id = :tenant_id 
                AND customer_phone = :phone 
                AND is_active = true 
                LIMIT 1
            """),
            {"tenant_id": tenant_id, "phone": phone},
        )
        return result.fetchone() is not None

    def get_optout(self, tenant_id: UUID, phone: str) -> WhatsAppOptOut | None:
        """Get opt-out record for a phone number."""
        return (
            self.db.query(WhatsAppOptOut)
            .filter(
                WhatsAppOptOut.tenant_id == tenant_id,
                WhatsAppOptOut.customer_phone == phone,
            )
            .first()
        )

    def create_optout(
        self,
        tenant_id: UUID,
        phone: str,
        reason: str,
        original_message_id: str | None = None,
    ) -> WhatsAppOptOut:
        """Create an opt-out record."""
        # Check if already exists (reactivate or create)
        existing = self.get_optout(tenant_id, phone)
        if existing:
            existing.is_active = True
            existing.reason = reason
            existing.original_message_id = original_message_id
            existing.updated_at = datetime.utcnow()
            return existing

        optout = WhatsAppOptOut(
            tenant_id=tenant_id,
            customer_phone=phone,
            reason=reason,
            original_message_id=original_message_id,
        )
        self.db.add(optout)
        return optout

    def remove_optout(self, tenant_id: UUID, phone: str) -> bool:
        """Remove opt-out (reactivate customer)."""
        optout = self.get_optout(tenant_id, phone)
        if optout and optout.is_active:
            optout.is_active = False
            optout.reactivated_at = datetime.utcnow()
            return True
        return False

