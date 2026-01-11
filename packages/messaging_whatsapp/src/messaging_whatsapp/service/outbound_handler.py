"""
Outbound Message Handler

Processes outbound WhatsApp messages:
1. Receives message from stream
2. Loads tenant binding and access token
3. Sends message via provider
4. Updates message status
5. Publishes delivery events
"""

import logging
import os
from typing import Any
from uuid import UUID

import redis
from sqlalchemy.orm import Session

from messaging_whatsapp.contracts.envelope import WhatsAppEnvelope
from messaging_whatsapp.contracts.event_types import WhatsAppEventType
from messaging_whatsapp.persistence.models import MessageDirection, MessageStatus
from messaging_whatsapp.persistence.repo import WhatsAppRepository
from messaging_whatsapp.providers.base import ProviderResponse, WhatsAppProvider
from messaging_whatsapp.providers.meta_cloud import MetaCloudWhatsAppProvider
from messaging_whatsapp.providers.stub import StubWhatsAppProvider
from messaging_whatsapp.routing.conversation import ConversationManager
from messaging_whatsapp.routing.tenant_resolver import TenantResolver
from messaging_whatsapp.streams.producer import WhatsAppStreamProducer

logger = logging.getLogger(__name__)

# Maximum retries before sending to DLQ
MAX_RETRIES = 3


def get_provider(provider_type: str | None = None) -> WhatsAppProvider:
    """
    Get the appropriate WhatsApp provider.

    Uses WHATSAPP_PROVIDER env var if provider_type not specified.
    """
    provider_type = provider_type or os.getenv("WHATSAPP_PROVIDER", "stub")

    if provider_type == "meta":
        return MetaCloudWhatsAppProvider()
    else:
        return StubWhatsAppProvider()


class OutboundHandler:
    """
    Handles outbound WhatsApp messages.

    Responsibilities:
    - Send messages via provider
    - Track delivery status
    - Handle retries and DLQ
    """

    def __init__(
        self,
        db: Session,
        redis_client: redis.Redis,
        provider: WhatsAppProvider | None = None,
        encryption_key: str | None = None,
    ):
        self.db = db
        self.redis = redis_client
        self.repo = WhatsAppRepository(db)
        self.tenant_resolver = TenantResolver(db)
        self.conversation_manager = ConversationManager(db)
        self.producer = WhatsAppStreamProducer(redis_client)
        self.provider = provider or get_provider()
        self.encryption_key = encryption_key or os.getenv("WHATSAPP_ENCRYPTION_KEY")

    async def handle_envelope(self, envelope: WhatsAppEnvelope) -> dict[str, Any]:
        """
        Process an outbound message envelope from the stream.

        Args:
            envelope: WhatsApp envelope from stream

        Returns:
            Processing result dict
        """
        payload = envelope.payload
        tenant_id = envelope.tenant_id
        retry_count = envelope.metadata.get("retry_count", 0)

        try:
            result = await self.send_message(
                tenant_id=tenant_id,
                payload=payload,
                correlation_id=envelope.correlation_id,
            )

            if result.get("status") == "sent":
                return result

            # Handle failure
            if retry_count < MAX_RETRIES:
                # Will be retried by PEL reclaim
                logger.warning(
                    f"Message send failed, will retry",
                    extra={
                        "event_id": str(envelope.event_id),
                        "retry_count": retry_count,
                        "error": result.get("error"),
                    },
                )
                return {**result, "will_retry": True}
            else:
                # Send to DLQ
                self.producer.publish_to_dlq(
                    envelope,
                    error=result.get("error", "Unknown error"),
                    retry_count=retry_count,
                )
                logger.error(
                    f"Message sent to DLQ after {MAX_RETRIES} retries",
                    extra={"event_id": str(envelope.event_id)},
                )
                return {**result, "sent_to_dlq": True}

        except Exception as e:
            logger.error(f"Failed to process outbound message: {e}", exc_info=True)
            return {"status": "failed", "error": str(e)}

    async def send_message(
        self,
        tenant_id: UUID,
        payload: dict[str, Any],
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Send a message via the provider.

        Args:
            tenant_id: Tenant ID
            payload: Message payload
            correlation_id: Correlation ID for tracing

        Returns:
            Result dict with status and message_id
        """
        to_phone = payload.get("to_phone")
        if not to_phone:
            return {"status": "failed", "error": "Missing to_phone"}

        # Check if customer can receive messages
        if not self.conversation_manager.can_send_message(tenant_id, to_phone):
            return {"status": "blocked", "reason": "opted_out_or_no_binding"}

        # Get tenant binding
        binding = self.tenant_resolver.get_binding_for_tenant(tenant_id)
        if not binding:
            return {"status": "failed", "error": "No active binding for tenant"}

        # Get access token
        access_token = self.tenant_resolver.get_access_token(binding, self.encryption_key)
        if not access_token:
            return {"status": "failed", "error": "No access token configured"}

        # Get or create conversation
        conversation, _ = self.conversation_manager.get_or_create_conversation(
            tenant_id=tenant_id,
            customer_phone=to_phone,
        )

        # Create message record (pending)
        db_message = self.repo.create_message(
            tenant_id=tenant_id,
            conversation_id=conversation.id,
            direction=MessageDirection.OUTBOUND,
            message_type=payload.get("message_type", "text"),
            content=payload.get("text"),
            content_json=payload,
            status=MessageStatus.PENDING,
            template_name=payload.get("template_name"),
            reply_to_message_id=payload.get("reply_to_message_id"),
            triggered_by_event_id=(
                UUID(payload["triggered_by_event_id"])
                if payload.get("triggered_by_event_id")
                else None
            ),
        )

        self.db.commit()

        # Send via provider
        response: ProviderResponse

        message_type = payload.get("message_type", "text")

        try:
            if message_type == "template":
                response = await self.provider.send_template(
                    phone_number_id=binding.phone_number_id,
                    access_token=access_token,
                    to=to_phone,
                    template_name=payload.get("template_name", ""),
                    language_code=payload.get("template_language", "pt_BR"),
                    components=payload.get("template_components"),
                )

            elif message_type == "interactive" and payload.get("buttons"):
                response = await self.provider.send_interactive(
                    phone_number_id=binding.phone_number_id,
                    access_token=access_token,
                    to=to_phone,
                    body_text=payload.get("text", ""),
                    buttons=payload.get("buttons", []),
                    header_text=payload.get("header_text"),
                    footer_text=payload.get("footer_text"),
                    reply_to=payload.get("reply_to_message_id"),
                )

            else:
                # Text message
                response = await self.provider.send_text(
                    phone_number_id=binding.phone_number_id,
                    access_token=access_token,
                    to=to_phone,
                    text=payload.get("text", ""),
                    reply_to=payload.get("reply_to_message_id"),
                )

        except Exception as e:
            logger.error(f"Provider error: {e}", exc_info=True)
            response = ProviderResponse(
                success=False,
                error_code="PROVIDER_ERROR",
                error_message=str(e),
            )

        # Update message with result
        if response.success:
            self.repo.update_message_provider_id(db_message, response.message_id or "")
            self.repo.update_message_status(db_message, MessageStatus.SENT)

            # Update conversation
            self.conversation_manager.record_outbound_message(conversation)

            self.db.commit()

            logger.info(
                f"Message sent successfully",
                extra={
                    "to": to_phone,
                    "message_id": response.message_id,
                    "type": message_type,
                },
            )

            return {
                "status": "sent",
                "message_id": str(db_message.id),
                "provider_message_id": response.message_id,
            }

        else:
            self.repo.update_message_status(
                db_message,
                MessageStatus.FAILED,
                error_code=response.error_code,
                error_message=response.error_message,
            )

            self.db.commit()

            # Publish failure event
            self.producer.publish_delivery_status(
                tenant_id=tenant_id,
                event_type=WhatsAppEventType.DELIVERY_FAILED,
                payload={
                    "our_message_id": str(db_message.id),
                    "to_phone": to_phone,
                    "error_code": response.error_code,
                    "error_message": response.error_message,
                },
                correlation_id=correlation_id,
            )

            logger.warning(
                f"Message send failed",
                extra={
                    "to": to_phone,
                    "error_code": response.error_code,
                    "error_message": response.error_message,
                },
            )

            return {
                "status": "failed",
                "message_id": str(db_message.id),
                "error": response.error_message,
                "error_code": response.error_code,
            }

    async def handle_vertical_event(
        self,
        envelope: WhatsAppEnvelope,
    ) -> dict[str, Any]:
        """
        Handle an event from a vertical that should trigger a WhatsApp message.

        Events like QUOTE_CREATED, ORDER_STATUS_CHANGED can trigger
        notifications to customers.

        Args:
            envelope: Event envelope from vertical

        Returns:
            Processing result
        """
        from messaging_whatsapp.contracts.event_types import VERTICAL_EVENTS_TO_NOTIFY
        from messaging_whatsapp.providers.meta_cloud.templates import template_registry

        event_type = envelope.event_type
        payload = envelope.payload
        tenant_id = envelope.tenant_id

        # Check if this event type should trigger notification
        template_name = VERTICAL_EVENTS_TO_NOTIFY.get(event_type)
        if not template_name:
            return {"status": "skipped", "reason": "event_type_not_configured"}

        # Check for explicit opt-in
        if not payload.get("notify_whatsapp", False):
            # Check if customer_phone is provided (implicit opt-in)
            if not payload.get("customer_phone"):
                return {"status": "skipped", "reason": "no_customer_phone"}

        customer_phone = payload.get("customer_phone")
        if not customer_phone:
            return {"status": "skipped", "reason": "no_customer_phone"}

        # Check template exists
        template = template_registry.get(template_name)
        if not template:
            logger.warning(f"Template {template_name} not found")
            return {"status": "skipped", "reason": "template_not_found"}

        # Build template variables from payload
        variables = self._extract_template_variables(payload, template_name)

        # Queue outbound message
        outbound_payload = {
            "to_phone": customer_phone,
            "message_type": "template",
            "template_name": template_name,
            "template_language": "pt_BR",
            "template_components": template.build_components(variables),
            "triggered_by_event_id": str(envelope.event_id),
        }

        self.producer.publish_outbound(
            tenant_id=tenant_id,
            payload=outbound_payload,
            correlation_id=envelope.correlation_id,
            triggered_by_event_id=envelope.event_id,
        )

        return {
            "status": "queued",
            "template": template_name,
            "to_phone": customer_phone,
        }

    def _extract_template_variables(
        self,
        payload: dict[str, Any],
        template_name: str,
    ) -> dict[str, Any]:
        """Extract template variables from event payload."""
        variables: dict[str, Any] = {}

        # Common variables
        if "customer_name" in payload:
            variables["customer_name"] = payload["customer_name"]
        elif "client_name" in payload:
            variables["customer_name"] = payload["client_name"]

        # Quote templates
        if "quote" in template_name:
            variables["quote_number"] = payload.get("quote_number", payload.get("numero", ""))
            variables["total_value"] = str(payload.get("total_value", payload.get("valor_total", "")))

        # Order templates
        if "order" in template_name:
            variables["order_number"] = payload.get("order_number", payload.get("numero", ""))
            variables["status"] = payload.get("new_status", payload.get("status", ""))

        # Delivery templates
        if "delivery" in template_name:
            variables["order_number"] = payload.get("order_number", payload.get("numero", ""))
            variables["estimated_time"] = payload.get("estimated_time", "")

        return variables

