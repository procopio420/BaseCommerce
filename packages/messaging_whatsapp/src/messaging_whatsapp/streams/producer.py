"""
WhatsApp Stream Producer

Publishes events to Redis Streams for WhatsApp messaging.
"""

import json
import logging
from typing import Any
from uuid import UUID

import redis

from messaging_whatsapp.contracts.envelope import WhatsAppEnvelope
from messaging_whatsapp.contracts.event_types import WhatsAppEventType
from messaging_whatsapp.streams.groups import (
    DLQ_STREAM,
    INBOUND_STREAM,
    OUTBOUND_STREAM,
)

logger = logging.getLogger(__name__)


class WhatsAppStreamProducer:
    """
    Producer for publishing WhatsApp events to Redis Streams.
    """

    def __init__(
        self,
        redis_client: redis.Redis,
        max_len: int = 100000,
    ):
        self.redis = redis_client
        self.max_len = max_len

    def publish_inbound(
        self,
        tenant_id: UUID,
        payload: dict[str, Any],
        correlation_id: str | None = None,
    ) -> str:
        """
        Publish an inbound message event.

        Called by webhook when a message is received from WhatsApp.

        Returns:
            Stream message ID
        """
        envelope = WhatsAppEnvelope.create(
            event_type=WhatsAppEventType.INBOUND_RECEIVED.value,
            tenant_id=tenant_id,
            payload=payload,
            correlation_id=correlation_id,
        )

        return self._publish(INBOUND_STREAM, envelope)

    def publish_outbound(
        self,
        tenant_id: UUID,
        payload: dict[str, Any],
        correlation_id: str | None = None,
        triggered_by_event_id: UUID | None = None,
    ) -> str:
        """
        Publish an outbound message event.

        Called when a message needs to be sent via WhatsApp.

        Returns:
            Stream message ID
        """
        if triggered_by_event_id:
            payload["triggered_by_event_id"] = str(triggered_by_event_id)

        envelope = WhatsAppEnvelope.create(
            event_type=WhatsAppEventType.OUTBOUND_QUEUED.value,
            tenant_id=tenant_id,
            payload=payload,
            correlation_id=correlation_id,
        )

        return self._publish(OUTBOUND_STREAM, envelope)

    def publish_action_requested(
        self,
        tenant_id: UUID,
        intent: str,
        from_phone: str,
        original_message_id: str,
        context: dict[str, Any] | None = None,
        correlation_id: str | None = None,
    ) -> str:
        """
        Publish an action requested event.

        Called when customer requests a specific action via button or keyword.

        Returns:
            Stream message ID
        """
        payload = {
            "intent": intent,
            "from_phone": from_phone,
            "original_message_id": original_message_id,
            "context": context or {},
        }

        envelope = WhatsAppEnvelope.create(
            event_type=WhatsAppEventType.ACTION_REQUESTED.value,
            tenant_id=tenant_id,
            payload=payload,
            correlation_id=correlation_id,
        )

        # Publish to the main events stream so verticals can consume
        return self._publish("events:materials", envelope)

    def publish_optout(
        self,
        tenant_id: UUID,
        phone: str,
        reason: str,
        original_message_id: str,
        correlation_id: str | None = None,
    ) -> str:
        """
        Publish an opt-out event.

        Returns:
            Stream message ID
        """
        payload = {
            "phone": phone,
            "reason": reason,
            "original_message_id": original_message_id,
        }

        envelope = WhatsAppEnvelope.create(
            event_type=WhatsAppEventType.CUSTOMER_OPTED_OUT.value,
            tenant_id=tenant_id,
            payload=payload,
            correlation_id=correlation_id,
        )

        return self._publish("events:materials", envelope)

    def publish_delivery_status(
        self,
        tenant_id: UUID,
        event_type: WhatsAppEventType,
        payload: dict[str, Any],
        correlation_id: str | None = None,
    ) -> str:
        """
        Publish a delivery status event.

        Returns:
            Stream message ID
        """
        envelope = WhatsAppEnvelope.create(
            event_type=event_type.value,
            tenant_id=tenant_id,
            payload=payload,
            correlation_id=correlation_id,
        )

        return self._publish("events:materials", envelope)

    def publish_to_dlq(
        self,
        original_envelope: WhatsAppEnvelope,
        error: str,
        retry_count: int,
    ) -> str:
        """
        Publish a failed message to the dead letter queue.

        Returns:
            Stream message ID
        """
        dlq_payload = {
            "original_event": original_envelope.to_dict(),
            "error": error,
            "retry_count": retry_count,
        }

        dlq_envelope = WhatsAppEnvelope.create(
            event_type="whatsapp_dlq_entry",
            tenant_id=original_envelope.tenant_id,
            payload=dlq_payload,
            correlation_id=original_envelope.correlation_id,
        )

        return self._publish(DLQ_STREAM, dlq_envelope)

    def _publish(self, stream_name: str, envelope: WhatsAppEnvelope) -> str:
        """
        Publish an envelope to a stream.

        Returns:
            Stream message ID
        """
        data = envelope.to_stream_data()

        msg_id = self.redis.xadd(
            stream_name,
            data,
            maxlen=self.max_len,
            approximate=True,
        )

        logger.debug(
            f"Published to {stream_name}",
            extra={
                "stream": stream_name,
                "event_type": envelope.event_type,
                "event_id": str(envelope.event_id),
                "msg_id": msg_id,
            },
        )

        return msg_id

