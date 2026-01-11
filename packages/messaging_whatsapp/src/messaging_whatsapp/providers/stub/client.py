"""
Stub WhatsApp Provider

Development provider that logs all operations without making real API calls.
Useful for local development and testing.
"""

import logging
from datetime import datetime
from typing import Any
from uuid import uuid4

from messaging_whatsapp.providers.base import (
    DeliveryStatus,
    InboundMessage,
    MessageType,
    ProviderResponse,
    WhatsAppProvider,
)

logger = logging.getLogger(__name__)


class StubWhatsAppProvider(WhatsAppProvider):
    """
    Stub provider for development and testing.

    - Logs all outbound messages
    - Accepts any webhook signature
    - Generates fake message IDs
    - Can be configured to simulate failures
    """

    def __init__(
        self,
        simulate_failures: bool = False,
        failure_rate: float = 0.1,
    ):
        self.simulate_failures = simulate_failures
        self.failure_rate = failure_rate
        self.sent_messages: list[dict[str, Any]] = []

    async def send_text(
        self,
        phone_number_id: str,
        access_token: str,
        to: str,
        text: str,
        reply_to: str | None = None,
        preview_url: bool = False,
    ) -> ProviderResponse:
        """Log and return success for text message."""
        message_id = f"stub_msg_{uuid4().hex[:16]}"

        message_data = {
            "type": "text",
            "phone_number_id": phone_number_id,
            "to": to,
            "text": text,
            "reply_to": reply_to,
            "message_id": message_id,
            "timestamp": datetime.utcnow().isoformat(),
        }

        self.sent_messages.append(message_data)

        logger.info(
            f"[STUB] Sending text message",
            extra={
                "to": to,
                "text": text[:100] + "..." if len(text) > 100 else text,
                "message_id": message_id,
            },
        )

        if self._should_fail():
            return ProviderResponse(
                success=False,
                error_code="STUB_SIMULATED_FAILURE",
                error_message="Simulated failure for testing",
            )

        return ProviderResponse(
            success=True,
            message_id=message_id,
            raw_response={"stub": True, "message_id": message_id},
        )

    async def send_template(
        self,
        phone_number_id: str,
        access_token: str,
        to: str,
        template_name: str,
        language_code: str,
        components: list[dict[str, Any]] | None = None,
    ) -> ProviderResponse:
        """Log and return success for template message."""
        message_id = f"stub_tmpl_{uuid4().hex[:16]}"

        message_data = {
            "type": "template",
            "phone_number_id": phone_number_id,
            "to": to,
            "template_name": template_name,
            "language_code": language_code,
            "components": components,
            "message_id": message_id,
            "timestamp": datetime.utcnow().isoformat(),
        }

        self.sent_messages.append(message_data)

        logger.info(
            f"[STUB] Sending template message",
            extra={
                "to": to,
                "template": template_name,
                "language": language_code,
                "message_id": message_id,
            },
        )

        if self._should_fail():
            return ProviderResponse(
                success=False,
                error_code="STUB_SIMULATED_FAILURE",
                error_message="Simulated failure for testing",
            )

        return ProviderResponse(
            success=True,
            message_id=message_id,
            raw_response={"stub": True, "message_id": message_id},
        )

    async def send_interactive(
        self,
        phone_number_id: str,
        access_token: str,
        to: str,
        body_text: str,
        buttons: list[dict[str, str]],
        header_text: str | None = None,
        footer_text: str | None = None,
        reply_to: str | None = None,
    ) -> ProviderResponse:
        """Log and return success for interactive message."""
        message_id = f"stub_btn_{uuid4().hex[:16]}"

        message_data = {
            "type": "interactive",
            "phone_number_id": phone_number_id,
            "to": to,
            "body_text": body_text,
            "buttons": buttons,
            "header_text": header_text,
            "footer_text": footer_text,
            "reply_to": reply_to,
            "message_id": message_id,
            "timestamp": datetime.utcnow().isoformat(),
        }

        self.sent_messages.append(message_data)

        logger.info(
            f"[STUB] Sending interactive message",
            extra={
                "to": to,
                "body": body_text[:50],
                "buttons": [b.get("title") for b in buttons],
                "message_id": message_id,
            },
        )

        if self._should_fail():
            return ProviderResponse(
                success=False,
                error_code="STUB_SIMULATED_FAILURE",
                error_message="Simulated failure for testing",
            )

        return ProviderResponse(
            success=True,
            message_id=message_id,
            raw_response={"stub": True, "message_id": message_id},
        )

    async def mark_as_read(
        self,
        phone_number_id: str,
        access_token: str,
        message_id: str,
    ) -> bool:
        """Log and return success for mark as read."""
        logger.debug(f"[STUB] Marking message as read: {message_id}")
        return True

    async def get_media_url(
        self,
        media_id: str,
        access_token: str,
    ) -> str | None:
        """Return a fake URL for media."""
        logger.debug(f"[STUB] Getting media URL for: {media_id}")
        return f"https://stub.whatsapp.local/media/{media_id}"

    def validate_webhook_signature(
        self,
        payload: bytes,
        signature: str,
        app_secret: str,
    ) -> bool:
        """Always accept signatures in stub mode."""
        logger.debug("[STUB] Accepting webhook signature (stub mode)")
        return True

    def parse_webhook(
        self,
        payload: dict[str, Any],
    ) -> tuple[list[InboundMessage], list[DeliveryStatus]]:
        """
        Parse webhook payload.

        In stub mode, we expect a simplified format for testing:
        {
            "from": "+5511999999999",
            "text": "Hello",
            "message_id": "test_123"
        }

        Or the full Meta format (same parser as production).
        """
        messages: list[InboundMessage] = []
        statuses: list[DeliveryStatus] = []

        # Check for simplified stub format first
        if "from" in payload and "text" in payload:
            msg = InboundMessage(
                message_id=payload.get("message_id", f"stub_in_{uuid4().hex[:16]}"),
                from_phone=payload["from"],
                to_phone=payload.get("to", "+5511888888888"),
                phone_number_id=payload.get("phone_number_id", "stub_phone_id"),
                waba_id=payload.get("waba_id", "stub_waba_id"),
                message_type=MessageType.TEXT,
                timestamp=datetime.utcnow(),
                text=payload.get("text"),
                contact_name=payload.get("name"),
                raw_payload=payload,
            )
            messages.append(msg)
            return messages, statuses

        # Try to parse Meta-like format
        try:
            entries = payload.get("entry", [])
            for entry in entries:
                changes = entry.get("changes", [])
                for change in changes:
                    value = change.get("value", {})

                    # Parse messages
                    for msg_data in value.get("messages", []):
                        msg = self._parse_message(value, msg_data)
                        if msg:
                            messages.append(msg)

                    # Parse statuses
                    for status_data in value.get("statuses", []):
                        status = self._parse_status(status_data)
                        if status:
                            statuses.append(status)

        except Exception as e:
            logger.warning(f"[STUB] Failed to parse webhook payload: {e}")

        return messages, statuses

    def verify_webhook_challenge(
        self,
        mode: str,
        token: str,
        challenge: str,
        verify_token: str,
    ) -> str | None:
        """Accept any verification in stub mode."""
        if mode == "subscribe":
            logger.info(f"[STUB] Accepting webhook verification challenge")
            return challenge
        return None

    def _should_fail(self) -> bool:
        """Check if we should simulate a failure."""
        if not self.simulate_failures:
            return False

        import random
        return random.random() < self.failure_rate

    def _parse_message(
        self,
        value: dict[str, Any],
        msg_data: dict[str, Any],
    ) -> InboundMessage | None:
        """Parse a single message from Meta-like format."""
        try:
            metadata = value.get("metadata", {})
            contacts = value.get("contacts", [{}])
            contact = contacts[0] if contacts else {}

            msg_type_str = msg_data.get("type", "text")
            msg_type = MessageType(msg_type_str) if msg_type_str in MessageType.__members__.values() else MessageType.UNKNOWN

            text = None
            if msg_type == MessageType.TEXT:
                text = msg_data.get("text", {}).get("body")

            return InboundMessage(
                message_id=msg_data.get("id", f"stub_{uuid4().hex[:8]}"),
                from_phone=msg_data.get("from", ""),
                to_phone=metadata.get("display_phone_number", ""),
                phone_number_id=metadata.get("phone_number_id", "stub_phone_id"),
                waba_id=value.get("waba_id", "stub_waba_id"),
                message_type=msg_type,
                timestamp=datetime.utcnow(),
                text=text,
                contact_name=contact.get("profile", {}).get("name"),
                context_message_id=msg_data.get("context", {}).get("id"),
                raw_payload=msg_data,
            )
        except Exception as e:
            logger.warning(f"[STUB] Failed to parse message: {e}")
            return None

    def _parse_status(self, status_data: dict[str, Any]) -> DeliveryStatus | None:
        """Parse a single status update."""
        try:
            return DeliveryStatus(
                message_id=status_data.get("id", ""),
                recipient_phone=status_data.get("recipient_id", ""),
                status=status_data.get("status", ""),
                timestamp=datetime.utcnow(),
                error_code=status_data.get("errors", [{}])[0].get("code") if status_data.get("errors") else None,
                error_message=status_data.get("errors", [{}])[0].get("message") if status_data.get("errors") else None,
                raw_payload=status_data,
            )
        except Exception as e:
            logger.warning(f"[STUB] Failed to parse status: {e}")
            return None

    def get_sent_messages(self) -> list[dict[str, Any]]:
        """Get all sent messages (for testing)."""
        return self.sent_messages.copy()

    def clear_sent_messages(self) -> None:
        """Clear sent messages history (for testing)."""
        self.sent_messages.clear()

