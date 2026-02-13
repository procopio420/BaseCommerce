"""
Tests for Evolution API provider.
"""

from datetime import datetime

import pytest

from messaging_whatsapp.providers.base import MessageType
from messaging_whatsapp.providers.evolution import EvolutionWhatsAppProvider
from messaging_whatsapp.providers.evolution.webhook import (
    extract_instance_name,
    is_message_webhook,
    is_status_webhook,
    parse_evolution_webhook,
    validate_api_key,
)


@pytest.fixture
def evolution_text_message_webhook():
    """Sample Evolution API webhook for a text message."""
    return {
        "event": "messages.upsert",
        "instance": "test_instance",
        "data": {
            "key": {
                "id": "msg_123",
                "remoteJid": "5511888888888@s.whatsapp.net",
            },
            "message": {
                "conversation": "Preciso de cimento",
            },
            "messageType": "conversation",
            "messageTimestamp": 1704067200,
        },
    }


@pytest.fixture
def evolution_button_webhook():
    """Sample Evolution API webhook for a button click."""
    return {
        "event": "messages.upsert",
        "instance": "test_instance",
        "data": {
            "key": {
                "id": "msg_button",
                "remoteJid": "5511888888888@s.whatsapp.net",
            },
            "message": {
                "buttonsResponseMessage": {
                    "selectedButtonId": "btn_quote",
                    "selectedButtonText": "Fazer cotação",
                },
            },
            "messageType": "buttonsResponseMessage",
            "messageTimestamp": 1704067200,
        },
    }


@pytest.fixture
def evolution_status_webhook():
    """Sample Evolution API webhook for a status update."""
    return {
        "event": "messages.update",
        "instance": "test_instance",
        "data": {
            "key": {
                "id": "msg_sent",
                "remoteJid": "5511888888888@s.whatsapp.net",
            },
            "update": {
                "status": "READ",
            },
        },
    }


class TestEvolutionWebhookParsing:
    """Tests for Evolution API webhook parsing utilities."""

    def test_extract_instance_name(self, evolution_text_message_webhook):
        """Test extracting instance name from webhook."""
        instance = extract_instance_name(evolution_text_message_webhook)
        assert instance == "test_instance"

    def test_extract_instance_name_missing(self):
        """Test extracting from invalid payload."""
        instance = extract_instance_name({})
        assert instance is None

    def test_is_message_webhook(self, evolution_text_message_webhook, evolution_status_webhook):
        """Test detecting message webhooks."""
        assert is_message_webhook(evolution_text_message_webhook) is True
        assert is_message_webhook(evolution_status_webhook) is False

    def test_is_status_webhook(self, evolution_text_message_webhook, evolution_status_webhook):
        """Test detecting status webhooks."""
        assert is_status_webhook(evolution_text_message_webhook) is False
        assert is_status_webhook(evolution_status_webhook) is True

    def test_parse_evolution_webhook(self, evolution_text_message_webhook):
        """Test parsing Evolution webhook."""
        result = parse_evolution_webhook(evolution_text_message_webhook)

        assert result["instance"] == "test_instance"
        assert result["event"] == "messages.upsert"
        assert len(result["messages"]) == 1
        assert len(result["statuses"]) == 0

    def test_validate_api_key(self):
        """Test API key validation."""
        headers = {"apikey": "test-key"}
        assert validate_api_key(headers, "test-key") is True
        assert validate_api_key(headers, "wrong-key") is False

    def test_validate_api_key_bearer(self):
        """Test API key validation with Bearer token."""
        headers = {"authorization": "Bearer test-key"}
        assert validate_api_key(headers, "test-key") is True
        assert validate_api_key(headers, "wrong-key") is False


class TestEvolutionProvider:
    """Tests for Evolution API provider."""

    def test_parse_text_message(self, evolution_text_message_webhook):
        """Test parsing a text message from webhook."""
        provider = EvolutionWhatsAppProvider(
            api_url="https://test.example.com",
            api_key="test-key",
            instance_name="test_instance",
        )
        messages, statuses = provider.parse_webhook(evolution_text_message_webhook)

        assert len(messages) == 1
        assert len(statuses) == 0

        msg = messages[0]
        assert msg.message_id == "msg_123"
        assert msg.from_phone == "5511888888888"
        assert msg.phone_number_id == "test_instance"
        assert msg.waba_id == "test_instance"
        assert msg.message_type == MessageType.TEXT
        assert msg.text == "Preciso de cimento"

    def test_parse_button_click(self, evolution_button_webhook):
        """Test parsing a button click from webhook."""
        provider = EvolutionWhatsAppProvider(
            api_url="https://test.example.com",
            api_key="test-key",
            instance_name="test_instance",
        )
        messages, statuses = provider.parse_webhook(evolution_button_webhook)

        assert len(messages) == 1
        msg = messages[0]
        assert msg.message_type == MessageType.BUTTON
        assert msg.button_payload == "btn_quote"
        assert msg.button_text == "Fazer cotação"

    def test_parse_status_update(self, evolution_status_webhook):
        """Test parsing a status update from webhook."""
        provider = EvolutionWhatsAppProvider(
            api_url="https://test.example.com",
            api_key="test-key",
            instance_name="test_instance",
        )
        messages, statuses = provider.parse_webhook(evolution_status_webhook)

        assert len(messages) == 0
        assert len(statuses) == 1

        status = statuses[0]
        assert status.message_id == "msg_sent"
        assert status.status == "read"
        assert status.recipient_phone == "5511888888888"

    def test_parse_unknown_event(self):
        """Test parsing unknown event returns empty."""
        provider = EvolutionWhatsAppProvider(
            api_url="https://test.example.com",
            api_key="test-key",
            instance_name="test_instance",
        )
        messages, statuses = provider.parse_webhook({"event": "unknown"})

        assert len(messages) == 0
        assert len(statuses) == 0




