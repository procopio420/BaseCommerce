"""
Conversation State Management

Simple state machine for WhatsApp conversations.
Tracks conversation state and enables automation flows.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from messaging_whatsapp.persistence.models import (
    ConversationStatus,
    MessageDirection,
    WhatsAppConversation,
)
from messaging_whatsapp.persistence.repo import WhatsAppRepository

logger = logging.getLogger(__name__)


class ConversationState(str, Enum):
    """
    Conversation states for simple automation.

    States are used to track where the customer is in a flow.
    """

    # Initial states
    NEW = "new"  # New conversation
    IDLE = "idle"  # Waiting for customer

    # Active states
    AWAITING_RESPONSE = "awaiting_response"  # Waiting for customer reply
    PROCESSING = "processing"  # Bot is processing

    # Action states
    QUOTE_FLOW = "quote_flow"  # Customer wants a quote
    ORDER_STATUS_FLOW = "order_status_flow"  # Customer checking order
    HUMAN_REQUESTED = "human_requested"  # Customer wants human agent

    # Terminal states
    CLOSED = "closed"  # Conversation ended
    OPTED_OUT = "opted_out"  # Customer opted out


@dataclass
class ConversationContext:
    """Context data for a conversation."""

    conversation_id: UUID
    tenant_id: UUID
    customer_phone: str
    customer_name: str | None
    state: ConversationState
    last_message_at: datetime | None
    message_count: int
    assigned_user_id: UUID | None
    metadata: dict[str, Any]

    @property
    def is_active(self) -> bool:
        """Check if conversation is active."""
        return self.state not in (ConversationState.CLOSED, ConversationState.OPTED_OUT)

    @property
    def is_stale(self, hours: int = 24) -> bool:
        """Check if conversation is stale (no activity)."""
        if not self.last_message_at:
            return True
        return datetime.utcnow() - self.last_message_at > timedelta(hours=hours)


class ConversationManager:
    """
    Manages conversation state and transitions.

    Provides methods to:
    - Get or create conversations
    - Update conversation state
    - Record messages
    - Check if customer can receive messages
    """

    def __init__(self, db: Session):
        self.db = db
        self.repo = WhatsAppRepository(db)

    def get_or_create_conversation(
        self,
        tenant_id: UUID,
        customer_phone: str,
        customer_name: str | None = None,
    ) -> tuple[WhatsAppConversation, bool]:
        """
        Get or create a conversation.

        Args:
            tenant_id: Tenant ID
            customer_phone: Customer phone number (E.164)
            customer_name: Optional customer name

        Returns:
            Tuple of (conversation, is_new)
        """
        return self.repo.get_or_create_conversation(
            tenant_id=tenant_id,
            customer_phone=customer_phone,
            customer_name=customer_name,
        )

    def get_context(
        self,
        conversation: WhatsAppConversation,
    ) -> ConversationContext:
        """
        Get context object for a conversation.

        Args:
            conversation: Conversation model

        Returns:
            ConversationContext with relevant data
        """
        state = ConversationState(conversation.current_state or ConversationState.IDLE.value)

        return ConversationContext(
            conversation_id=conversation.id,
            tenant_id=conversation.tenant_id,
            customer_phone=conversation.customer_phone,
            customer_name=conversation.customer_name,
            state=state,
            last_message_at=conversation.last_message_at,
            message_count=int(conversation.message_count or "0"),
            assigned_user_id=conversation.assigned_user_id,
            metadata=conversation.context or {},
        )

    def update_state(
        self,
        conversation: WhatsAppConversation,
        new_state: ConversationState,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """
        Update conversation state.

        Args:
            conversation: Conversation to update
            new_state: New state
            metadata: Optional metadata to merge
        """
        old_state = conversation.current_state
        conversation.current_state = new_state.value
        conversation.updated_at = datetime.utcnow()

        if metadata:
            context = conversation.context or {}
            context.update(metadata)
            conversation.context = context

        logger.debug(
            f"Conversation state changed",
            extra={
                "conversation_id": str(conversation.id),
                "old_state": old_state,
                "new_state": new_state.value,
            },
        )

    def record_inbound_message(
        self,
        conversation: WhatsAppConversation,
        timestamp: datetime | None = None,
    ) -> None:
        """
        Record that an inbound message was received.

        Updates timestamps and counters.
        """
        self.repo.update_conversation_last_message(
            conversation,
            MessageDirection.INBOUND,
            timestamp,
        )

        # Reset to active if was closed
        if conversation.status == ConversationStatus.CLOSED.value:
            conversation.status = ConversationStatus.ACTIVE.value

    def record_outbound_message(
        self,
        conversation: WhatsAppConversation,
        timestamp: datetime | None = None,
    ) -> None:
        """
        Record that an outbound message was sent.

        Updates timestamps and counters.
        """
        self.repo.update_conversation_last_message(
            conversation,
            MessageDirection.OUTBOUND,
            timestamp,
        )

    def assign_to_user(
        self,
        conversation: WhatsAppConversation,
        user_id: UUID,
    ) -> None:
        """
        Assign conversation to a human agent.

        Args:
            conversation: Conversation to assign
            user_id: User ID to assign
        """
        conversation.assigned_user_id = user_id
        conversation.status = ConversationStatus.HUMAN_ASSIGNED.value
        self.update_state(conversation, ConversationState.HUMAN_REQUESTED)

    def close_conversation(
        self,
        conversation: WhatsAppConversation,
        reason: str | None = None,
    ) -> None:
        """
        Close a conversation.

        Args:
            conversation: Conversation to close
            reason: Optional reason for closing
        """
        conversation.status = ConversationStatus.CLOSED.value
        self.update_state(
            conversation,
            ConversationState.CLOSED,
            {"close_reason": reason} if reason else None,
        )

    def can_send_message(
        self,
        tenant_id: UUID,
        customer_phone: str,
    ) -> bool:
        """
        Check if we can send a message to this customer.

        Checks:
        - Customer has not opted out
        - Tenant has active binding

        Args:
            tenant_id: Tenant ID
            customer_phone: Customer phone

        Returns:
            True if message can be sent
        """
        # Check opt-out
        if self.repo.is_opted_out(tenant_id, customer_phone):
            logger.debug(f"Customer {customer_phone} has opted out")
            return False

        # Check tenant binding
        binding = self.repo.get_active_binding_for_tenant(tenant_id)
        if not binding:
            logger.debug(f"Tenant {tenant_id} has no active WhatsApp binding")
            return False

        return True

    def get_recent_conversations(
        self,
        tenant_id: UUID,
        status: ConversationStatus | None = None,
        limit: int = 50,
    ) -> list[WhatsAppConversation]:
        """
        Get recent conversations for a tenant.

        Args:
            tenant_id: Tenant ID
            status: Optional status filter
            limit: Maximum number to return

        Returns:
            List of conversations ordered by last message
        """
        return self.repo.list_conversations(tenant_id, status, limit)




