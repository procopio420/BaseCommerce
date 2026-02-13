"""
Inbound Message Handler

Processes incoming WhatsApp messages:
1. Parses webhook payload
2. Resolves tenant
3. Gets or creates conversation
4. Persists message
5. Runs automation (detect intent, auto-reply)
6. Publishes events
"""

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

import redis
from sqlalchemy.orm import Session

from messaging_whatsapp.contracts.envelope import WhatsAppEnvelope
from messaging_whatsapp.contracts.event_types import WhatsAppEventType
from messaging_whatsapp.contracts.payloads import ActionIntent, InboundMessagePayload, MessageType
from messaging_whatsapp.persistence.models import MessageDirection, MessageStatus
from messaging_whatsapp.persistence.repo import WhatsAppRepository
from messaging_whatsapp.providers.base import DeliveryStatus as ProviderDeliveryStatus
from messaging_whatsapp.providers.base import InboundMessage
from messaging_whatsapp.routing.conversation import ConversationManager, ConversationState
from messaging_whatsapp.routing.tenant_resolver import TenantResolver
from messaging_whatsapp.service.automation import AutomationEngine, AutoReplyType
from messaging_whatsapp.streams.producer import WhatsAppStreamProducer

logger = logging.getLogger(__name__)


class InboundHandler:
    """
    Handles incoming WhatsApp messages.

    Responsibilities:
    - Persist messages to database
    - Manage conversation state
    - Run automation (opt-out, intent detection)
    - Queue auto-replies
    - Publish events for verticais
    """

    def __init__(
        self,
        db: Session,
        redis_client: redis.Redis,
        automation: AutomationEngine | None = None,
    ):
        self.db = db
        self.redis = redis_client
        self.repo = WhatsAppRepository(db)
        self.tenant_resolver = TenantResolver(db)
        self.conversation_manager = ConversationManager(db)
        self.producer = WhatsAppStreamProducer(redis_client)
        self.automation = automation or AutomationEngine()

    def handle_envelope(self, envelope: WhatsAppEnvelope) -> dict[str, Any]:
        """
        Process an inbound message envelope from the stream.

        Args:
            envelope: WhatsApp envelope from stream

        Returns:
            Processing result dict
        """
        payload = envelope.payload
        tenant_id = envelope.tenant_id

        # Check idempotency
        provider_message_id = payload.get("message_id")
        if provider_message_id and self.repo.is_message_processed(provider_message_id):
            logger.debug(f"Message {provider_message_id} already processed, skipping")
            return {
                "status": "skipped",
                "reason": "already_processed",
                "message_id": provider_message_id,
            }

        # Build InboundMessage from payload
        message = self._payload_to_inbound_message(payload)

        return self.process_message(tenant_id, message, envelope.correlation_id)

    def process_message(
        self,
        tenant_id: UUID,
        message: InboundMessage,
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Process a single inbound message.

        Args:
            tenant_id: Resolved tenant ID
            message: Parsed inbound message
            correlation_id: Optional correlation ID for tracing

        Returns:
            Processing result dict
        """
        result: dict[str, Any] = {
            "message_id": message.message_id,
            "from": message.from_phone,
            "status": "processed",
        }

        try:
            # Get or create conversation
            conversation, is_new = self.conversation_manager.get_or_create_conversation(
                tenant_id=tenant_id,
                customer_phone=message.from_phone,
                customer_name=message.contact_name,
            )

            # Record the inbound message
            self.conversation_manager.record_inbound_message(
                conversation,
                message.timestamp,
            )

            # Persist message
            db_message = self.repo.create_message(
                tenant_id=tenant_id,
                conversation_id=conversation.id,
                direction=MessageDirection.INBOUND,
                message_type=message.message_type.value,
                content=message.text,
                content_json=message.raw_payload,
                provider_message_id=message.message_id,
                status=MessageStatus.DELIVERED,  # Inbound = already delivered
            )

            # Run automation detection
            detection = self.automation.detect(
                text=message.text,
                button_payload=message.button_payload,
            )

            result["detection"] = {
                "is_optout": detection.is_optout,
                "intent": detection.intent.value if detection.intent else None,
            }

            # Handle opt-out
            if detection.is_optout:
                self._handle_optout(
                    tenant_id=tenant_id,
                    phone=message.from_phone,
                    reason=detection.optout_keyword or "unknown",
                    message_id=message.message_id,
                    correlation_id=correlation_id,
                )
                self.conversation_manager.update_state(
                    conversation, ConversationState.OPTED_OUT
                )
                result["action"] = "opted_out"

            # Handle intent
            elif detection.intent:
                self._handle_intent(
                    tenant_id=tenant_id,
                    intent=detection.intent,
                    from_phone=message.from_phone,
                    conversation_id=conversation.id,
                    message_id=message.message_id,
                    text=message.text,
                    correlation_id=correlation_id,
                )

                if detection.intent == ActionIntent.TALK_TO_HUMAN:
                    self.conversation_manager.update_state(
                        conversation, ConversationState.HUMAN_REQUESTED
                    )
                else:
                    self.conversation_manager.update_state(
                        conversation, ConversationState.PROCESSING
                    )

                result["action"] = f"intent_{detection.intent.value}"

            # Determine auto-reply
            auto_reply_type = self.automation.should_auto_reply(
                is_new_conversation=is_new,
                detection=detection,
            )

            if auto_reply_type:
                self._queue_auto_reply(
                    tenant_id=tenant_id,
                    to_phone=message.from_phone,
                    reply_type=auto_reply_type,
                    reply_to_message_id=message.message_id,
                    correlation_id=correlation_id,
                )
                result["auto_reply"] = auto_reply_type.value

            # Commit all changes
            self.db.commit()

            # Publish inbound event for verticais
            self._publish_inbound_event(
                tenant_id=tenant_id,
                message=message,
                conversation_id=conversation.id,
                correlation_id=correlation_id,
            )

            result["conversation_id"] = str(conversation.id)
            result["is_new_conversation"] = is_new

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to process inbound message: {e}", exc_info=True)
            result["status"] = "failed"
            result["error"] = str(e)

        return result

    def handle_delivery_status(
        self,
        tenant_id: UUID,
        status: ProviderDeliveryStatus,
    ) -> dict[str, Any]:
        """
        Handle a delivery status update.

        Args:
            tenant_id: Tenant ID
            status: Delivery status from provider

        Returns:
            Processing result
        """
        # Find the message
        message = self.repo.get_message_by_provider_id(status.message_id)
        if not message:
            logger.debug(f"No message found for provider ID: {status.message_id}")
            return {"status": "skipped", "reason": "message_not_found"}

        # Map status
        status_map = {
            "sent": MessageStatus.SENT,
            "delivered": MessageStatus.DELIVERED,
            "read": MessageStatus.READ,
            "failed": MessageStatus.FAILED,
        }
        new_status = status_map.get(status.status, MessageStatus.SENT)

        # Update message
        self.repo.update_message_status(
            message,
            new_status,
            error_code=status.error_code,
            error_message=status.error_message,
        )

        self.db.commit()

        # Publish delivery event if failed
        if new_status == MessageStatus.FAILED:
            self.producer.publish_delivery_status(
                tenant_id=tenant_id,
                event_type=WhatsAppEventType.DELIVERY_FAILED,
                payload={
                    "provider_message_id": status.message_id,
                    "our_message_id": str(message.id),
                    "error_code": status.error_code,
                    "error_message": status.error_message,
                },
            )

        return {
            "status": "updated",
            "message_id": str(message.id),
            "new_status": new_status.value,
        }

    def _handle_optout(
        self,
        tenant_id: UUID,
        phone: str,
        reason: str,
        message_id: str,
        correlation_id: str | None,
    ) -> None:
        """Handle opt-out request."""
        self.repo.create_optout(
            tenant_id=tenant_id,
            phone=phone,
            reason=reason,
            original_message_id=message_id,
        )

        # Publish opt-out event
        self.producer.publish_optout(
            tenant_id=tenant_id,
            phone=phone,
            reason=reason,
            original_message_id=message_id,
            correlation_id=correlation_id,
        )

    def _handle_intent(
        self,
        tenant_id: UUID,
        intent: ActionIntent,
        from_phone: str,
        conversation_id: UUID,
        message_id: str,
        text: str | None,
        correlation_id: str | None,
    ) -> None:
        """Handle detected intent."""
        self.producer.publish_action_requested(
            tenant_id=tenant_id,
            intent=intent.value,
            from_phone=from_phone,
            original_message_id=message_id,
            context={
                "conversation_id": str(conversation_id),
                "original_text": text,
            },
            correlation_id=correlation_id,
        )

    def _queue_auto_reply(
        self,
        tenant_id: UUID,
        to_phone: str,
        reply_type: AutoReplyType,
        reply_to_message_id: str | None,
        correlation_id: str | None,
    ) -> None:
        """Queue an auto-reply message."""
        auto_reply = self.automation.get_auto_reply(
            reply_type,
            with_buttons=reply_type in (AutoReplyType.WELCOME, AutoReplyType.RECEIVED),
        )

        payload = {
            "to_phone": to_phone,
            "text": auto_reply.text,
            "message_type": "text" if not auto_reply.buttons else "interactive",
            "buttons": auto_reply.buttons,
            "reply_to_message_id": reply_to_message_id,
            "auto_reply_type": reply_type.value,
        }

        self.producer.publish_outbound(
            tenant_id=tenant_id,
            payload=payload,
            correlation_id=correlation_id,
        )

    def _publish_inbound_event(
        self,
        tenant_id: UUID,
        message: InboundMessage,
        conversation_id: UUID,
        correlation_id: str | None,
    ) -> None:
        """Publish WHATSAPP_INBOUND_RECEIVED event."""
        payload = InboundMessagePayload(
            from_phone=message.from_phone,
            to_phone=message.to_phone,
            phone_number_id=message.phone_number_id,
            waba_id=message.waba_id,
            message_id=message.message_id,
            message_type=MessageType(message.message_type.value),
            text=message.text,
            media_url=message.media_url,
            caption=message.caption,
            timestamp=message.timestamp,
            context_message_id=message.context_message_id,
            conversation_id=conversation_id,
            customer_name=message.contact_name,
            raw_payload=message.raw_payload,
        )

        # Publish to main events stream
        envelope = WhatsAppEnvelope.create(
            event_type=WhatsAppEventType.INBOUND_RECEIVED.value,
            tenant_id=tenant_id,
            payload=payload.model_dump(mode="json"),
            correlation_id=correlation_id,
        )

        self.redis.xadd(
            "events:materials",
            envelope.to_stream_data(),
            maxlen=100000,
            approximate=True,
        )

    def _payload_to_inbound_message(self, payload: dict[str, Any]) -> InboundMessage:
        """Convert stream payload to InboundMessage."""
        from messaging_whatsapp.providers.base import MessageType as ProviderMessageType

        msg_type_str = payload.get("message_type", "text")
        try:
            msg_type = ProviderMessageType(msg_type_str)
        except ValueError:
            msg_type = ProviderMessageType.UNKNOWN

        timestamp = payload.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        elif not timestamp:
            timestamp = datetime.utcnow()

        return InboundMessage(
            message_id=payload.get("message_id", ""),
            from_phone=payload.get("from_phone", ""),
            to_phone=payload.get("to_phone", ""),
            phone_number_id=payload.get("phone_number_id", ""),
            waba_id=payload.get("waba_id", ""),
            message_type=msg_type,
            timestamp=timestamp,
            text=payload.get("text"),
            caption=payload.get("caption"),
            media_id=payload.get("media_id"),
            media_url=payload.get("media_url"),
            context_message_id=payload.get("context_message_id"),
            contact_name=payload.get("customer_name"),
            button_payload=payload.get("button_payload"),
            button_text=payload.get("button_text"),
            raw_payload=payload.get("raw_payload", {}),
        )




