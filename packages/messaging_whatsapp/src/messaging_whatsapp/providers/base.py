"""
WhatsApp Provider Base

Abstract interface for WhatsApp API providers.
Implementations: Meta Cloud API, Stub (for development).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class ProviderError(Exception):
    """Error from WhatsApp provider."""

    def __init__(
        self,
        message: str,
        code: str | None = None,
        details: dict[str, Any] | None = None,
        retryable: bool = False,
    ):
        super().__init__(message)
        self.code = code
        self.details = details or {}
        self.retryable = retryable


class MessageType(str, Enum):
    """Types of WhatsApp messages."""

    TEXT = "text"
    IMAGE = "image"
    DOCUMENT = "document"
    AUDIO = "audio"
    VIDEO = "video"
    TEMPLATE = "template"
    INTERACTIVE = "interactive"
    LOCATION = "location"
    CONTACTS = "contacts"
    STICKER = "sticker"
    REACTION = "reaction"
    UNKNOWN = "unknown"


@dataclass
class InboundMessage:
    """
    Parsed inbound message from webhook.

    Provider-agnostic representation of an incoming WhatsApp message.
    """

    message_id: str
    from_phone: str
    to_phone: str
    phone_number_id: str
    waba_id: str
    message_type: MessageType
    timestamp: datetime
    text: str | None = None
    caption: str | None = None
    media_id: str | None = None
    media_mime_type: str | None = None
    media_url: str | None = None
    context_message_id: str | None = None  # Replied-to message
    contact_name: str | None = None  # Sender's WhatsApp profile name
    button_payload: str | None = None  # For button/interactive responses
    button_text: str | None = None
    location_latitude: float | None = None
    location_longitude: float | None = None
    location_name: str | None = None
    raw_payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class DeliveryStatus:
    """
    Parsed delivery status update from webhook.
    """

    message_id: str
    recipient_phone: str
    status: str  # sent, delivered, read, failed
    timestamp: datetime
    error_code: str | None = None
    error_message: str | None = None
    conversation_id: str | None = None  # Provider's conversation ID
    raw_payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class ProviderResponse:
    """
    Response from provider after sending a message.
    """

    success: bool
    message_id: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    raw_response: dict[str, Any] = field(default_factory=dict)


class WhatsAppProvider(ABC):
    """
    Abstract interface for WhatsApp API providers.

    Implementations must handle:
    - Sending text and template messages
    - Sending interactive messages (buttons)
    - Webhook signature validation
    - Webhook payload parsing
    """

    @abstractmethod
    async def send_text(
        self,
        phone_number_id: str,
        access_token: str,
        to: str,
        text: str,
        reply_to: str | None = None,
        preview_url: bool = False,
    ) -> ProviderResponse:
        """
        Send a text message.

        Args:
            phone_number_id: Business phone number ID
            access_token: Access token for this number
            to: Recipient phone number (E.164 format)
            text: Message text
            reply_to: Message ID to reply to (optional)
            preview_url: Whether to show URL previews

        Returns:
            ProviderResponse with message ID if successful
        """
        ...

    @abstractmethod
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

        Args:
            phone_number_id: Business phone number ID
            access_token: Access token for this number
            to: Recipient phone number (E.164 format)
            template_name: Approved template name
            language_code: Template language code (e.g., "pt_BR")
            components: Template components (header, body, buttons variables)

        Returns:
            ProviderResponse with message ID if successful
        """
        ...

    @abstractmethod
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
        """
        Send an interactive message with buttons.

        Args:
            phone_number_id: Business phone number ID
            access_token: Access token for this number
            to: Recipient phone number (E.164 format)
            body_text: Main message body
            buttons: List of buttons [{id, title}] (max 3)
            header_text: Optional header
            footer_text: Optional footer
            reply_to: Message ID to reply to (optional)

        Returns:
            ProviderResponse with message ID if successful
        """
        ...

    @abstractmethod
    async def mark_as_read(
        self,
        phone_number_id: str,
        access_token: str,
        message_id: str,
    ) -> bool:
        """
        Mark a message as read.

        Args:
            phone_number_id: Business phone number ID
            access_token: Access token for this number
            message_id: Message ID to mark as read

        Returns:
            True if successful
        """
        ...

    @abstractmethod
    async def get_media_url(
        self,
        media_id: str,
        access_token: str,
    ) -> str | None:
        """
        Get the download URL for a media file.

        Args:
            media_id: Media ID from the message
            access_token: Access token

        Returns:
            Download URL or None if failed
        """
        ...

    @abstractmethod
    def validate_webhook_signature(
        self,
        payload: bytes,
        signature: str,
        app_secret: str,
    ) -> bool:
        """
        Validate webhook signature.

        Args:
            payload: Raw request body
            signature: X-Hub-Signature-256 header value
            app_secret: Facebook App Secret

        Returns:
            True if signature is valid
        """
        ...

    @abstractmethod
    def parse_webhook(
        self,
        payload: dict[str, Any],
    ) -> tuple[list[InboundMessage], list[DeliveryStatus]]:
        """
        Parse webhook payload into messages and status updates.

        Args:
            payload: Parsed JSON webhook payload

        Returns:
            Tuple of (list of inbound messages, list of delivery statuses)
        """
        ...

    @abstractmethod
    def verify_webhook_challenge(
        self,
        mode: str,
        token: str,
        challenge: str,
        verify_token: str,
    ) -> str | None:
        """
        Handle webhook verification challenge.

        Args:
            mode: hub.mode query parameter
            token: hub.verify_token query parameter
            challenge: hub.challenge query parameter
            verify_token: Our configured verify token

        Returns:
            challenge string if valid, None otherwise
        """
        ...

