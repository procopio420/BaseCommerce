"""
Tests for webhook payload parsing.
"""

from datetime import datetime

import pytest

from messaging_whatsapp.providers.base import MessageType
from messaging_whatsapp.providers.meta_cloud import MetaCloudWhatsAppProvider
from messaging_whatsapp.providers.meta_cloud.webhook import (
    extract_phone_number_id,
    is_message_webhook,
    is_status_webhook,
    parse_meta_webhook,
)


@pytest.fixture
def meta_text_message_webhook():
    """Sample Meta webhook for a text message."""
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "WABA_123456",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "5511999999999",
                                "phone_number_id": "PHONE_123",
                            },
                            "contacts": [
                                {
                                    "profile": {"name": "John Doe"},
                                    "wa_id": "5511888888888",
                                }
                            ],
                            "messages": [
                                {
                                    "from": "5511888888888",
                                    "id": "wamid.HBgM",
                                    "timestamp": "1704067200",
                                    "text": {"body": "Preciso de cimento"},
                                    "type": "text",
                                }
                            ],
                        },
                        "field": "messages",
                    }
                ],
            }
        ],
    }


@pytest.fixture
def meta_button_webhook():
    """Sample Meta webhook for a button click."""
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "WABA_123456",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "5511999999999",
                                "phone_number_id": "PHONE_123",
                            },
                            "contacts": [
                                {
                                    "profile": {"name": "John Doe"},
                                    "wa_id": "5511888888888",
                                }
                            ],
                            "messages": [
                                {
                                    "context": {
                                        "from": "5511999999999",
                                        "id": "wamid.prev",
                                    },
                                    "from": "5511888888888",
                                    "id": "wamid.button",
                                    "timestamp": "1704067200",
                                    "type": "interactive",
                                    "interactive": {
                                        "type": "button_reply",
                                        "button_reply": {
                                            "id": "btn_quote",
                                            "title": "Fazer cotação",
                                        },
                                    },
                                }
                            ],
                        },
                        "field": "messages",
                    }
                ],
            }
        ],
    }


@pytest.fixture
def meta_status_webhook():
    """Sample Meta webhook for a status update."""
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "WABA_123456",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "5511999999999",
                                "phone_number_id": "PHONE_123",
                            },
                            "statuses": [
                                {
                                    "id": "wamid.sent",
                                    "status": "delivered",
                                    "timestamp": "1704067200",
                                    "recipient_id": "5511888888888",
                                }
                            ],
                        },
                        "field": "messages",
                    }
                ],
            }
        ],
    }


class TestWebhookParsing:
    """Tests for webhook parsing utilities."""

    def test_extract_phone_number_id(self, meta_text_message_webhook):
        """Test extracting phone_number_id from webhook."""
        phone_number_id = extract_phone_number_id(meta_text_message_webhook)
        assert phone_number_id == "PHONE_123"

    def test_extract_phone_number_id_missing(self):
        """Test extracting from invalid payload."""
        phone_number_id = extract_phone_number_id({})
        assert phone_number_id is None

    def test_is_message_webhook(self, meta_text_message_webhook, meta_status_webhook):
        """Test detecting message webhooks."""
        assert is_message_webhook(meta_text_message_webhook) is True
        assert is_message_webhook(meta_status_webhook) is False

    def test_is_status_webhook(self, meta_text_message_webhook, meta_status_webhook):
        """Test detecting status webhooks."""
        assert is_status_webhook(meta_text_message_webhook) is False
        assert is_status_webhook(meta_status_webhook) is True

    def test_parse_meta_webhook(self, meta_text_message_webhook):
        """Test parsing Meta webhook."""
        result = parse_meta_webhook(meta_text_message_webhook)

        assert result["waba_id"] == "WABA_123456"
        assert result["phone_number_id"] == "PHONE_123"
        assert result["display_number"] == "5511999999999"
        assert len(result["messages"]) == 1
        assert result["messages"][0]["type"] == "text"


class TestMetaCloudProvider:
    """Tests for Meta Cloud provider webhook parsing."""

    def test_parse_text_message(self, meta_text_message_webhook):
        """Test parsing a text message from webhook."""
        provider = MetaCloudWhatsAppProvider()
        messages, statuses = provider.parse_webhook(meta_text_message_webhook)

        assert len(messages) == 1
        assert len(statuses) == 0

        msg = messages[0]
        assert msg.message_id == "wamid.HBgM"
        assert msg.from_phone == "5511888888888"
        assert msg.phone_number_id == "PHONE_123"
        assert msg.waba_id == "WABA_123456"
        assert msg.message_type == MessageType.TEXT
        assert msg.text == "Preciso de cimento"
        assert msg.contact_name == "John Doe"

    def test_parse_button_click(self, meta_button_webhook):
        """Test parsing a button click from webhook."""
        provider = MetaCloudWhatsAppProvider()
        messages, statuses = provider.parse_webhook(meta_button_webhook)

        assert len(messages) == 1
        msg = messages[0]
        assert msg.message_type == MessageType.INTERACTIVE
        assert msg.button_payload == "btn_quote"
        assert msg.button_text == "Fazer cotação"
        assert msg.context_message_id == "wamid.prev"

    def test_parse_status_update(self, meta_status_webhook):
        """Test parsing a status update from webhook."""
        provider = MetaCloudWhatsAppProvider()
        messages, statuses = provider.parse_webhook(meta_status_webhook)

        assert len(messages) == 0
        assert len(statuses) == 1

        status = statuses[0]
        assert status.message_id == "wamid.sent"
        assert status.status == "delivered"
        assert status.recipient_phone == "5511888888888"

    def test_parse_non_whatsapp_webhook(self):
        """Test parsing non-WhatsApp webhook returns empty."""
        provider = MetaCloudWhatsAppProvider()
        messages, statuses = provider.parse_webhook({"object": "instagram"})

        assert len(messages) == 0
        assert len(statuses) == 0




