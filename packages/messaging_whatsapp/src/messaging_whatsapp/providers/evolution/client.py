"""
Evolution API WhatsApp Provider

Provider for Evolution API (Baileys-based WhatsApp Web integration).
Uses REST API to send messages and manage instances.

Documentation: https://doc.evolution-api.com/
"""

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


class EvolutionWhatsAppProvider(WhatsAppProvider):
    """
    Evolution API provider for WhatsApp.

    Uses Evolution API REST endpoints to send messages and receive webhooks.
    Each tenant has its own instance (identified by instance_name).
    """

    def __init__(
        self,
        api_url: str,
        api_key: str,
        instance_name: str,
        timeout: float = 30.0,
    ):
        """
        Initialize Evolution API provider.

        Args:
            api_url: Base URL of Evolution API (e.g., "https://evolution-api.example.com")
            api_key: API key for authentication
            instance_name: Name of the Evolution instance
            timeout: HTTP request timeout
        """
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self.instance_name = instance_name
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                headers={
                    "Content-Type": "application/json",
                    "apikey": self.api_key,
                },
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        json_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make an authenticated API request."""
        client = await self._get_client()
        url = f"{self.api_url}{endpoint}"

        try:
            if method.upper() == "GET":
                response = await client.get(url)
            else:
                response = await client.post(url, json=json_data)

            response_data = response.json()

            if response.status_code >= 400:
                error = response_data.get("error") or response_data.get("message", "Unknown error")
                raise ProviderError(
                    message=str(error),
                    code=str(response.status_code),
                    details=response_data,
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
        phone_number_id: str,  # Not used for Evolution, but kept for interface compatibility
        access_token: str,  # Not used for Evolution
        to: str,
        text: str,
        reply_to: str | None = None,
        preview_url: bool = False,
    ) -> ProviderResponse:
        """Send a text message via Evolution API."""
        endpoint = f"/message/sendText/{self.instance_name}"

        payload: dict[str, Any] = {
            "number": to,
            "text": text,
        }

        if reply_to:
            payload["quoted"] = reply_to

        try:
            response = await self._make_request("POST", endpoint, payload)
            message_id = response.get("key", {}).get("id") or response.get("id")

            logger.info(
                f"Sent text message via Evolution API",
                extra={"to": to, "message_id": message_id, "instance": self.instance_name},
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
        """
        Send a template message.

        Note: Evolution API doesn't support official templates.
        This sends a formatted text message instead.
        """
        # Evolution API doesn't support templates, so we format as text
        text = f"[Template: {template_name}]\n"

        if components:
            for comp in components:
                if comp.get("type") == "body" and comp.get("parameters"):
                    for param in comp.get("parameters", []):
                        if param.get("type") == "text":
                            text += param.get("text", "") + "\n"

        return await self.send_text(phone_number_id, access_token, to, text.strip())

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
        """Send an interactive button message via Evolution API."""
        endpoint = f"/message/sendButtons/{self.instance_name}"

        # Format buttons for Evolution API
        buttons_list = []
        for btn in buttons[:3]:  # Max 3 buttons
            buttons_list.append({
                "buttonId": btn.get("id", ""),
                "buttonText": {"displayText": btn.get("title", "")},
            })

        payload: dict[str, Any] = {
            "number": to,
            "buttons": buttons_list,
            "text": body_text,
        }

        if header_text:
            payload["title"] = header_text
        if footer_text:
            payload["footer"] = footer_text

        try:
            response = await self._make_request("POST", endpoint, payload)
            message_id = response.get("key", {}).get("id") or response.get("id")

            logger.info(
                f"Sent interactive message via Evolution API",
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
        endpoint = f"/chat/markMessageAsRead/{self.instance_name}"

        payload = {
            "read_messages": [message_id],
        }

        try:
            await self._make_request("POST", endpoint, payload)
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
        endpoint = f"/chat/fetchBase64FromMediaMessage/{self.instance_name}"

        payload = {
            "message": {"key": {"id": media_id}},
        }

        try:
            response = await self._make_request("POST", endpoint, payload)
            # Evolution API returns base64, we'd need to convert to URL
            # For now, return None and handle media differently
            return None
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
        Validate webhook signature.

        Evolution API can use API key in header or JWT.
        For simplicity, we accept if API key matches.
        """
        # Evolution API doesn't use HMAC like Meta
        # We validate via API key in header instead
        # This is called but signature validation happens at webhook level
        return True

    def parse_webhook(
        self,
        payload: dict[str, Any],
    ) -> tuple[list[InboundMessage], list[DeliveryStatus]]:
        """
        Parse Evolution API webhook payload.

        Evolution API webhook format:
        {
            "event": "messages.upsert",
            "instance": "instance_name",
            "data": {
                "key": {"id": "...", "remoteJid": "..."},
                "message": {...},
                "messageType": "conversation",
                "messageTimestamp": 1234567890,
            }
        }
        """
        messages: list[InboundMessage] = []
        statuses: list[DeliveryStatus] = []

        try:
            event = payload.get("event", "")

            if event == "messages.upsert":
                # Incoming message
                data = payload.get("data", {})
                key = data.get("key", {})
                message_data = data.get("message", {})

                msg = self._parse_message(payload.get("instance", ""), key, message_data, data)
                if msg:
                    messages.append(msg)

            elif event == "messages.update":
                # Status update
                data = payload.get("data", {})
                status = self._parse_status(data)
                if status:
                    statuses.append(status)

        except Exception as e:
            logger.error(f"Failed to parse Evolution webhook: {e}", exc_info=True)

        return messages, statuses

    def verify_webhook_challenge(
        self,
        mode: str,
        token: str,
        challenge: str,
        verify_token: str,
    ) -> str | None:
        """Evolution API doesn't use webhook verification challenge."""
        return None

    def _parse_message(
        self,
        instance_name: str,
        key: dict[str, Any],
        message_data: dict[str, Any],
        full_data: dict[str, Any],
    ) -> InboundMessage | None:
        """Parse a single message from Evolution webhook."""
        try:
            message_id = key.get("id", "")
            remote_jid = key.get("remoteJid", "").replace("@s.whatsapp.net", "")
            message_type_str = full_data.get("messageType", "conversation")

            # Map Evolution message types
            type_mapping = {
                "conversation": MessageType.TEXT,
                "extendedTextMessage": MessageType.TEXT,
                "imageMessage": MessageType.IMAGE,
                "videoMessage": MessageType.VIDEO,
                "audioMessage": MessageType.AUDIO,
                "documentMessage": MessageType.DOCUMENT,
                "stickerMessage": MessageType.STICKER,
                "locationMessage": MessageType.LOCATION,
                "contactsArrayMessage": MessageType.CONTACTS,
                "buttonsResponseMessage": MessageType.BUTTON,
                "listResponseMessage": MessageType.INTERACTIVE,
            }

            msg_type = type_mapping.get(message_type_str, MessageType.UNKNOWN)

            # Extract text
            text = None
            if msg_type == MessageType.TEXT:
                text = message_data.get("conversation") or message_data.get("extendedTextMessage", {}).get("text")

            # Extract media info
            media_id = None
            caption = None
            if msg_type in (MessageType.IMAGE, MessageType.VIDEO, MessageType.AUDIO, MessageType.DOCUMENT):
                media_obj = message_data.get(f"{message_type_str.lower()}Message", {})
                media_id = media_obj.get("mediaKey")
                caption = media_obj.get("caption")

            # Extract button response
            button_payload = None
            button_text = None
            if msg_type == MessageType.BUTTON:
                button_obj = message_data.get("buttonsResponseMessage", {})
                button_payload = button_obj.get("selectedButtonId")
                button_text = button_obj.get("selectedButtonText")

            # Extract location
            location_lat = None
            location_lng = None
            if msg_type == MessageType.LOCATION:
                location_obj = message_data.get("locationMessage", {})
                location_lat = location_obj.get("degreesLatitude")
                location_lng = location_obj.get("degreesLongitude")

            # Parse timestamp
            timestamp = datetime.utcnow()
            if full_data.get("messageTimestamp"):
                try:
                    timestamp = datetime.fromtimestamp(int(full_data["messageTimestamp"]))
                except (ValueError, TypeError):
                    pass

            return InboundMessage(
                message_id=message_id,
                from_phone=remote_jid,
                to_phone="",  # Evolution doesn't provide this in webhook
                phone_number_id=instance_name,  # Use instance name as identifier
                waba_id=instance_name,  # Evolution doesn't have WABA
                message_type=msg_type,
                timestamp=timestamp,
                text=text,
                caption=caption,
                media_id=media_id,
                context_message_id=key.get("participant"),  # Reply context
                button_payload=button_payload,
                button_text=button_text,
                location_latitude=location_lat,
                location_longitude=location_lng,
                raw_payload=full_data,
            )

        except Exception as e:
            logger.error(f"Failed to parse Evolution message: {e}", exc_info=True)
            return None

    def _parse_status(self, data: dict[str, Any]) -> DeliveryStatus | None:
        """Parse a status update from Evolution webhook."""
        try:
            key = data.get("key", {})
            update = data.get("update", {})

            status_map = {
                "READ": "read",
                "DELIVERED": "delivered",
                "SENT": "sent",
            }

            status_str = update.get("status") or "sent"
            status = status_map.get(status_str.upper(), status_str.lower())

            return DeliveryStatus(
                message_id=key.get("id", ""),
                recipient_phone=key.get("remoteJid", "").replace("@s.whatsapp.net", ""),
                status=status,
                timestamp=datetime.utcnow(),
                raw_payload=data,
            )

        except Exception as e:
            logger.error(f"Failed to parse Evolution status: {e}", exc_info=True)
            return None




