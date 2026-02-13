"""
Tests for automation engine.
"""

import pytest

from messaging_whatsapp.contracts.payloads import ActionIntent
from messaging_whatsapp.service.automation import (
    AutomationEngine,
    AutoReplyType,
    DetectionResult,
)


class TestAutomationEngine:
    """Tests for the automation engine."""

    @pytest.fixture
    def engine(self):
        """Create automation engine instance."""
        return AutomationEngine()

    def test_detect_optout_stop(self, engine):
        """Test detecting STOP keyword."""
        result = engine.detect("STOP")
        assert result.is_optout is True
        assert result.optout_keyword == "stop"

    def test_detect_optout_sair(self, engine):
        """Test detecting SAIR keyword (Portuguese)."""
        result = engine.detect("Quero sair")
        assert result.is_optout is True
        assert result.optout_keyword == "sair"

    def test_detect_optout_cancelar(self, engine):
        """Test detecting cancelar keyword."""
        result = engine.detect("cancelar mensagens")
        assert result.is_optout is True
        assert result.optout_keyword == "cancelar"

    def test_detect_intent_quote(self, engine):
        """Test detecting quote intent."""
        result = engine.detect("Quero fazer uma cotação")
        assert result.is_optout is False
        assert result.intent == ActionIntent.CREATE_QUOTE

    def test_detect_intent_order_status(self, engine):
        """Test detecting order status intent."""
        result = engine.detect("Qual o status do meu pedido?")
        assert result.intent == ActionIntent.ORDER_STATUS

    def test_detect_intent_human(self, engine):
        """Test detecting talk to human intent."""
        result = engine.detect("Quero falar com atendente")
        assert result.intent == ActionIntent.TALK_TO_HUMAN

    def test_detect_button_payload(self, engine):
        """Test detecting intent from button payload."""
        result = engine.detect(button_payload="btn_quote")
        assert result.intent == ActionIntent.CREATE_QUOTE
        assert result.confidence == 1.0

    def test_detect_button_takes_priority(self, engine):
        """Test that button payload takes priority over text."""
        result = engine.detect(text="stop", button_payload="btn_status")
        assert result.is_optout is False
        assert result.intent == ActionIntent.ORDER_STATUS

    def test_detect_no_match(self, engine):
        """Test no match returns empty result."""
        result = engine.detect("Hello, I need some building materials")
        assert result.is_optout is False
        assert result.intent is None

    def test_get_auto_reply_welcome(self, engine):
        """Test getting welcome auto-reply."""
        reply = engine.get_auto_reply(
            AutoReplyType.WELCOME,
            variables={"business_name": "Materiais ABC"},
        )
        assert "Materiais ABC" in reply.text
        assert reply.reply_type == AutoReplyType.WELCOME

    def test_get_auto_reply_with_buttons(self, engine):
        """Test getting auto-reply with buttons."""
        reply = engine.get_auto_reply(
            AutoReplyType.WELCOME,
            with_buttons=True,
        )
        assert reply.buttons is not None
        assert len(reply.buttons) == 3
        assert any(b["id"] == "btn_quote" for b in reply.buttons)

    def test_get_default_buttons(self, engine):
        """Test getting default buttons."""
        buttons = engine.get_default_buttons()
        assert len(buttons) == 3
        assert buttons[0]["id"] == "btn_quote"
        assert buttons[1]["id"] == "btn_status"
        assert buttons[2]["id"] == "btn_human"

    def test_should_auto_reply_optout(self, engine):
        """Test auto-reply for opt-out."""
        detection = DetectionResult(is_optout=True, optout_keyword="stop")
        result = engine.should_auto_reply(
            is_new_conversation=False,
            detection=detection,
        )
        assert result == AutoReplyType.OPT_OUT_CONFIRMED

    def test_should_auto_reply_human_requested(self, engine):
        """Test auto-reply for human request."""
        detection = DetectionResult(intent=ActionIntent.TALK_TO_HUMAN)
        result = engine.should_auto_reply(
            is_new_conversation=False,
            detection=detection,
        )
        assert result == AutoReplyType.HUMAN_REQUESTED

    def test_should_auto_reply_new_conversation(self, engine):
        """Test auto-reply for new conversation."""
        detection = DetectionResult()
        result = engine.should_auto_reply(
            is_new_conversation=True,
            detection=detection,
        )
        assert result == AutoReplyType.WELCOME

    def test_should_auto_reply_regular_message(self, engine):
        """Test auto-reply for regular message."""
        detection = DetectionResult()
        result = engine.should_auto_reply(
            is_new_conversation=False,
            detection=detection,
        )
        assert result == AutoReplyType.RECEIVED

    def test_custom_auto_reply_template(self, engine):
        """Test setting custom auto-reply template."""
        engine.set_auto_reply(
            AutoReplyType.RECEIVED,
            "Olá {customer_name}! Recebemos sua mensagem.",
        )

        reply = engine.get_auto_reply(
            AutoReplyType.RECEIVED,
            variables={"customer_name": "João"},
        )

        assert "João" in reply.text
        assert "Recebemos sua mensagem" in reply.text




