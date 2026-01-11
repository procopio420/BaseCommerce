"""
Meta Cloud API WhatsApp Provider

Production provider for WhatsApp Business Cloud API.
Implements the Graph API v18.0+ for sending and receiving messages.
"""

import hashlib
import hmac
import logging
from datetime import datetime
from typing import Any

import httpx

from messaging_whatsapp.providers.base import (
    DeliveryStatus,
    InboundMessage,
    MessageType,
    ProviderError,
    ProviderResponse,
    WhatsAppProvider,
)

logger = logging.getLogger(__name__)

# Meta Graph API configuration
GRAPH_API_VERSION = "v18.0"
GRAPH_API_BASE_URL = f"https://graph.facebook.com/{GRAPH_API_VERSION}"


class MetaCloudWhatsAppProvider(WhatsAppProvider):
    """
    Meta Cloud API provider for WhatsApp Business.

    Uses the Graph API to send messages and handle webhooks.
    """

    def __init__(
        self,
        timeout: float = 30.0,
        max_retries: int = 3,
    ):
        self.timeout = timeout
        self.max_retries = max_retries
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                headers={"Content-Type": "application/json"},
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def _make_request(
        self,
        method: str,
        url: str,
        access_token: str,
        json_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make an authenticated API request."""
        client = await self._get_client()

        headers = {"Authorization": f"Bearer {access_token}"}

        try:
            if method.upper() == "GET":
                response = await client.get(url, headers=headers)
            else:
                response = await client.post(url, headers=headers, json=json_data)

            response_data = response.json()

            if response.status_code >= 400:
                error = response_data.get("error", {})
                raise ProviderError(
                    message=error.get("message", "Unknown error"),
                    code=str(error.get("code", response.status_code)),
                    details=error,
                    retryable=response.status_code >= 500,
                )

            return response_data

        except httpx.RequestError as e:
            logger.error(f"HTTP request failed: {e}")
            raise ProviderError(
                message=f"HTTP request failed: {e}",
                code="HTTP_ERROR",
                retryable=True,
            )

    async def send_text(
        self,
        phone_number_id: str,
        access_token: str,
        to: str,
        text: str,
        reply_to: str | None = None,
        preview_url: bool = False,
    ) -> ProviderResponse:
        """Send a text message via Graph API."""
        url = f"{GRAPH_API_BASE_URL}/{phone_number_id}/messages"

        payload: dict[str, Any] = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "text",
            "text": {
                "preview_url": preview_url,
                "body": text,
            },
        }

        if reply_to:
            payload["context"] = {"message_id": reply_to}

        try:
            response = await self._make_request("POST", url, access_token, payload)
            message_id = response.get("messages", [{}])[0].get("id")

            logger.info(
                f"Sent text message via Meta API",
                extra={"to": to, "message_id": message_id},
            )

            return ProviderResponse(
                success=True,
                message_id=message_id,
                raw_response=response,
            )

        except ProviderError as e:
            logger.error(f"Failed to send text message: {e}")
            return ProviderResponse(
                success=False,
                error_code=e.code,
                error_message=str(e),
                raw_response=e.details,
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
        """Send a template message via Graph API."""
        url = f"{GRAPH_API_BASE_URL}/{phone_number_id}/messages"

        payload: dict[str, Any] = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language_code},
            },
        }

        if components:
            payload["template"]["components"] = components

        try:
            response = await self._make_request("POST", url, access_token, payload)
            message_id = response.get("messages", [{}])[0].get("id")

            logger.info(
                f"Sent template message via Meta API",
                extra={"to": to, "template": template_name, "message_id": message_id},
            )

            return ProviderResponse(
                success=True,
                message_id=message_id,
                raw_response=response,
            )

        except ProviderError as e:
            logger.error(f"Failed to send template message: {e}")
            return ProviderResponse(
                success=False,
                error_code=e.code,
                error_message=str(e),
                raw_response=e.details,
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
        """Send an interactive button message via Graph API."""
        url = f"{GRAPH_API_BASE_URL}/{phone_number_id}/messages"

        # Build button list (max 3 buttons)
        button_rows = []
        for i, btn in enumerate(buttons[:3]):
            button_rows.append({
                "type": "reply",
                "reply": {
                    "id": btn.get("id", f"btn_{i}"),
                    "title": btn.get("title", f"Button {i + 1}")[:20],  # Max 20 chars
                },
            })

        interactive: dict[str, Any] = {
            "type": "button",
            "body": {"text": body_text},
            "action": {"buttons": button_rows},
        }

        if header_text:
            interactive["header"] = {"type": "text", "text": header_text}

        if footer_text:
            interactive["footer"] = {"text": footer_text}

        payload: dict[str, Any] = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "interactive",
            "interactive": interactive,
        }

        if reply_to:
            payload["context"] = {"message_id": reply_to}

        try:
            response = await self._make_request("POST", url, access_token, payload)
            message_id = response.get("messages", [{}])[0].get("id")

            logger.info(
                f"Sent interactive message via Meta API",
                extra={"to": to, "buttons": len(buttons), "message_id": message_id},
            )

            return ProviderResponse(
                success=True,
                message_id=message_id,
                raw_response=response,
            )

        except ProviderError as e:
            logger.error(f"Failed to send interactive message: {e}")
            return ProviderResponse(
                success=False,
                error_code=e.code,
                error_message=str(e),
                raw_response=e.details,
            )

    async def mark_as_read(
        self,
        phone_number_id: str,
        access_token: str,
        message_id: str,
    ) -> bool:
        """Mark a message as read."""
        url = f"{GRAPH_API_BASE_URL}/{phone_number_id}/messages"

        payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id,
        }

        try:
            await self._make_request("POST", url, access_token, payload)
            return True
        except ProviderError as e:
            logger.warning(f"Failed to mark message as read: {e}")
            return False

    async def get_media_url(
        self,
        media_id: str,
        access_token: str,
    ) -> str | None:
        """Get the download URL for a media file."""
        url = f"{GRAPH_API_BASE_URL}/{media_id}"

        try:
            response = await self._make_request("GET", url, access_token)
            return response.get("url")
        except ProviderError as e:
            logger.warning(f"Failed to get media URL: {e}")
            return None

    def validate_webhook_signature(
        self,
        payload: bytes,
        signature: str,
        app_secret: str,
    ) -> bool:
        """
        Validate webhook signature using HMAC-SHA256.

        The signature header format: sha256=<signature>
        """
        if not signature or not signature.startswith("sha256="):
            logger.warning("Invalid signature format")
            return False

        expected_signature = signature[7:]  # Remove "sha256=" prefix

        computed_signature = hmac.new(
            app_secret.encode("utf-8"),
            payload,
            hashlib.sha256,
        ).hexdigest()

        is_valid = hmac.compare_digest(computed_signature, expected_signature)

        if not is_valid:
            logger.warning("Webhook signature validation failed")

        return is_valid

    def parse_webhook(
        self,
        payload: dict[str, Any],
    ) -> tuple[list[InboundMessage], list[DeliveryStatus]]:
        """
        Parse Meta webhook payload into messages and status updates.

        Webhook format:
        {
            "object": "whatsapp_business_account",
            "entry": [{
                "id": "WABA_ID",
                "changes": [{
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {
                            "display_phone_number": "...",
                            "phone_number_id": "..."
                        },
                        "contacts": [...],
                        "messages": [...],
                        "statuses": [...]
                    },
                    "field": "messages"
                }]
            }]
        }
        """
        messages: list[InboundMessage] = []
        statuses: list[DeliveryStatus] = []

        try:
            if payload.get("object") != "whatsapp_business_account":
                logger.debug(f"Ignoring non-WhatsApp webhook: {payload.get('object')}")
                return messages, statuses

            for entry in payload.get("entry", []):
                waba_id = entry.get("id", "")

                for change in entry.get("changes", []):
                    if change.get("field") != "messages":
                        continue

                    value = change.get("value", {})
                    metadata = value.get("metadata", {})
                    contacts = value.get("contacts", [])

                    # Parse messages
                    for msg_data in value.get("messages", []):
                        msg = self._parse_message(waba_id, metadata, contacts, msg_data)
                        if msg:
                            messages.append(msg)

                    # Parse statuses
                    for status_data in value.get("statuses", []):
                        status = self._parse_status(status_data)
                        if status:
                            statuses.append(status)

        except Exception as e:
            logger.error(f"Failed to parse webhook payload: {e}", exc_info=True)

        return messages, statuses

    def verify_webhook_challenge(
        self,
        mode: str,
        token: str,
        challenge: str,
        verify_token: str,
    ) -> str | None:
        """Handle Meta webhook verification challenge."""
        if mode == "subscribe" and token == verify_token:
            logger.info("Webhook verification successful")
            return challenge

        logger.warning(f"Webhook verification failed: mode={mode}, token mismatch")
        return None

    def _parse_message(
        self,
        waba_id: str,
        metadata: dict[str, Any],
        contacts: list[dict[str, Any]],
        msg_data: dict[str, Any],
    ) -> InboundMessage | None:
        """Parse a single message from webhook."""
        try:
            msg_type_str = msg_data.get("type", "unknown")
            msg_type = self._map_message_type(msg_type_str)

            # Get contact info
            contact = contacts[0] if contacts else {}
            contact_name = contact.get("profile", {}).get("name")

            # Parse timestamp
            timestamp_str = msg_data.get("timestamp")
            timestamp = (
                datetime.fromtimestamp(int(timestamp_str))
                if timestamp_str
                else datetime.utcnow()
            )

            # Extract content based on type
            text = None
            caption = None
            media_id = None
            media_mime_type = None
            button_payload = None
            button_text = None
            location_lat = None
            location_lng = None
            location_name = None

            if msg_type == MessageType.TEXT:
                text = msg_data.get("text", {}).get("body")

            elif msg_type in (MessageType.IMAGE, MessageType.VIDEO, MessageType.AUDIO, MessageType.DOCUMENT, MessageType.STICKER):
                media_data = msg_data.get(msg_type_str, {})
                media_id = media_data.get("id")
                media_mime_type = media_data.get("mime_type")
                caption = media_data.get("caption")

            elif msg_type == MessageType.INTERACTIVE:
                interactive = msg_data.get("interactive", {})
                interactive_type = interactive.get("type")

                if interactive_type == "button_reply":
                    button_reply = interactive.get("button_reply", {})
                    button_payload = button_reply.get("id")
                    button_text = button_reply.get("title")

                elif interactive_type == "list_reply":
                    list_reply = interactive.get("list_reply", {})
                    button_payload = list_reply.get("id")
                    button_text = list_reply.get("title")

            elif msg_type == MessageType.BUTTON:
                button = msg_data.get("button", {})
                button_payload = button.get("payload")
                button_text = button.get("text")

            elif msg_type == MessageType.LOCATION:
                location = msg_data.get("location", {})
                location_lat = location.get("latitude")
                location_lng = location.get("longitude")
                location_name = location.get("name")

            # Get reply context
            context_message_id = msg_data.get("context", {}).get("id")

            return InboundMessage(
                message_id=msg_data.get("id", ""),
                from_phone=msg_data.get("from", ""),
                to_phone=metadata.get("display_phone_number", ""),
                phone_number_id=metadata.get("phone_number_id", ""),
                waba_id=waba_id,
                message_type=msg_type,
                timestamp=timestamp,
                text=text,
                caption=caption,
                media_id=media_id,
                media_mime_type=media_mime_type,
                context_message_id=context_message_id,
                contact_name=contact_name,
                button_payload=button_payload,
                button_text=button_text,
                location_latitude=location_lat,
                location_longitude=location_lng,
                location_name=location_name,
                raw_payload=msg_data,
            )

        except Exception as e:
            logger.error(f"Failed to parse message: {e}", exc_info=True)
            return None

    def _parse_status(self, status_data: dict[str, Any]) -> DeliveryStatus | None:
        """Parse a single status update from webhook."""
        try:
            timestamp_str = status_data.get("timestamp")
            timestamp = (
                datetime.fromtimestamp(int(timestamp_str))
                if timestamp_str
                else datetime.utcnow()
            )

            error_code = None
            error_message = None
            errors = status_data.get("errors", [])
            if errors:
                error = errors[0]
                error_code = str(error.get("code", ""))
                error_message = error.get("message") or error.get("title")

            return DeliveryStatus(
                message_id=status_data.get("id", ""),
                recipient_phone=status_data.get("recipient_id", ""),
                status=status_data.get("status", ""),
                timestamp=timestamp,
                error_code=error_code,
                error_message=error_message,
                conversation_id=status_data.get("conversation", {}).get("id"),
                raw_payload=status_data,
            )

        except Exception as e:
            logger.error(f"Failed to parse status: {e}", exc_info=True)
            return None

    def _map_message_type(self, type_str: str) -> MessageType:
        """Map Meta message type string to MessageType enum."""
        mapping = {
            "text": MessageType.TEXT,
            "image": MessageType.IMAGE,
            "video": MessageType.VIDEO,
            "audio": MessageType.AUDIO,
            "document": MessageType.DOCUMENT,
            "sticker": MessageType.STICKER,
            "location": MessageType.LOCATION,
            "contacts": MessageType.CONTACTS,
            "interactive": MessageType.INTERACTIVE,
            "button": MessageType.BUTTON,
            "reaction": MessageType.REACTION,
        }
        return mapping.get(type_str, MessageType.UNKNOWN)

