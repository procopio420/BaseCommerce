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
from messaging_whatsapp.providers.evolution import EvolutionWhatsAppProvider
from messaging_whatsapp.providers.meta_cloud import MetaCloudWhatsAppProvider
from messaging_whatsapp.providers.stub import StubWhatsAppProvider
from messaging_whatsapp.persistence.models import WhatsAppTenantBinding
from messaging_whatsapp.routing.conversation import ConversationManager
from messaging_whatsapp.routing.tenant_resolver import TenantResolver
from messaging_whatsapp.streams.producer import WhatsAppStreamProducer

logger = logging.getLogger(__name__)

# Maximum retries before sending to DLQ
MAX_RETRIES = 3


def get_provider_for_binding(
    binding: WhatsAppTenantBinding,
    encryption_key: str | None = None,
) -> WhatsAppProvider:
    """
    Get the appropriate WhatsApp provider based on binding configuration.

    Args:
        binding: Tenant binding with provider configuration
        encryption_key: Key for decrypting tokens/keys

    Returns:
        Provider instance configured for this binding
    """
    if binding.provider == "meta":
        return MetaCloudWhatsAppProvider()

    elif binding.provider == "evolution":
        # Decrypt API key if encrypted
        api_key = binding.api_key or ""
        if encryption_key and api_key:
            try:
                from cryptography.fernet import Fernet
                f = Fernet(encryption_key.encode())
                api_key = f.decrypt(api_key.encode()).decode()
            except Exception as e:
                logger.warning(f"Failed to decrypt Evolution API key: {e}")

        api_url = binding.api_url or binding.config.get("api_url", "")
        instance_name = binding.instance_name or ""

        if not api_url or not instance_name:
            logger.warning(
                f"Evolution provider missing configuration: api_url={bool(api_url)}, instance_name={bool(instance_name)}"
            )

        return EvolutionWhatsAppProvider(
            api_url=api_url,
            api_key=api_key,
            instance_name=instance_name,
        )

    else:
        # Default to stub for development
        return StubWhatsAppProvider()


def get_provider(provider_type: str | None = None) -> WhatsAppProvider:
    """
    Get the appropriate WhatsApp provider (legacy function for default provider).

    Uses WHATSAPP_PROVIDER env var if provider_type not specified.
    """
    provider_type = provider_type or os.getenv("WHATSAPP_PROVIDER", "stub")

    if provider_type == "meta":
        return MetaCloudWhatsAppProvider()
    elif provider_type == "evolution":
        # For default evolution, we'd need config from env
        api_url = os.getenv("EVOLUTION_API_URL", "")
        api_key = os.getenv("EVOLUTION_API_KEY", "")
        instance_name = os.getenv("EVOLUTION_INSTANCE_NAME", "")
        if api_url and api_key and instance_name:
            return EvolutionWhatsAppProvider(api_url, api_key, instance_name)
        return StubWhatsAppProvider()
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

        # Get provider for this binding
        provider = get_provider_for_binding(binding, self.encryption_key)

        # Get access token/credentials based on provider
        if binding.provider == "meta":
            access_token = self.tenant_resolver.get_access_token(binding, self.encryption_key)
            if not access_token:
                return {"status": "failed", "error": "No access token configured"}
            phone_number_id = binding.phone_number_id or ""
        elif binding.provider == "evolution":
            # Evolution uses instance_name instead of phone_number_id
            access_token = ""  # Not used for Evolution
            phone_number_id = binding.instance_name or ""
            if not phone_number_id:
                return {"status": "failed", "error": "No instance_name configured for Evolution"}
        else:
            # Stub provider
            access_token = ""
            phone_number_id = ""

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
                response = await provider.send_template(
                    phone_number_id=phone_number_id,
                    access_token=access_token,
                    to=to_phone,
                    template_name=payload.get("template_name", ""),
                    language_code=payload.get("template_language", "pt_BR"),
                    components=payload.get("template_components"),
                )

            elif message_type == "interactive" and payload.get("buttons"):
                response = await provider.send_interactive(
                    phone_number_id=phone_number_id,
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
                response = await provider.send_text(
                    phone_number_id=phone_number_id,
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

        # Get tenant binding to determine provider
        binding = self.tenant_resolver.get_binding_for_tenant(tenant_id)
        if not binding:
            return {"status": "skipped", "reason": "no_binding"}

        # Build message based on provider
        if binding.provider == "meta":
            # Use templates for Meta
            from messaging_whatsapp.providers.meta_cloud.templates import template_registry

            template = template_registry.get(template_name)
            if not template:
                logger.warning(f"Template {template_name} not found")
                return {"status": "skipped", "reason": "template_not_found"}

            variables = self._extract_template_variables(payload, template_name)

            outbound_payload = {
                "to_phone": customer_phone,
                "message_type": "template",
                "template_name": template_name,
                "template_language": "pt_BR",
                "template_components": template.build_components(variables),
                "triggered_by_event_id": str(envelope.event_id),
            }
        else:
            # Evolution or stub: send formatted text message
            text = self._format_notification_text(event_type, payload)
            outbound_payload = {
                "to_phone": customer_phone,
                "message_type": "text",
                "text": text,
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
            "provider": binding.provider,
            "to_phone": customer_phone,
        }

    def _format_notification_text(
        self,
        event_type: str,
        payload: dict[str, Any],
    ) -> str:
        """Format a notification text message for Evolution/stub providers."""
        customer_name = payload.get("customer_name") or payload.get("client_name", "Cliente")

        if event_type == "quote_created":
            quote_num = payload.get("quote_number") or payload.get("numero", "")
            total = payload.get("total_value") or payload.get("valor_total", "")
            return (
                f"Olá {customer_name}!\n\n"
                f"Sua cotação #{quote_num} foi criada com sucesso.\n"
                f"Valor total: R$ {total}\n\n"
                f"Em breve um vendedor entrará em contato."
            )

        elif event_type == "order_status_changed":
            order_num = payload.get("order_number") or payload.get("numero", "")
            status = payload.get("new_status") or payload.get("status", "")
            status_pt = {
                "pendente": "Pendente",
                "em_preparacao": "Em preparação",
                "saiu_entrega": "Saiu para entrega",
                "entregue": "Entregue",
            }.get(status, status)
            return (
                f"Olá {customer_name}!\n\n"
                f"Status do seu pedido #{order_num} foi atualizado:\n"
                f"{status_pt}"
            )

        elif event_type == "delivery_started":
            order_num = payload.get("order_number") or payload.get("numero", "")
            return (
                f"Olá {customer_name}!\n\n"
                f"Seu pedido #{order_num} saiu para entrega!\n"
                f"Em breve você receberá sua compra."
            )

        elif event_type == "delivery_completed":
            order_num = payload.get("order_number") or payload.get("numero", "")
            return (
                f"Olá {customer_name}!\n\n"
                f"Seu pedido #{order_num} foi entregue com sucesso!\n"
                f"Obrigado pela preferência!"
            )

        else:
            return f"Olá {customer_name}! Você tem uma atualização sobre seu pedido."

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

