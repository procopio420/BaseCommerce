"""
WhatsApp Automation Engine

Simple automation for WhatsApp messages:
- Keyword detection (opt-out, intent)
- Auto-reply messages
- Button/quick reply handling
"""

import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any

from messaging_whatsapp.contracts.payloads import ActionIntent

logger = logging.getLogger(__name__)


class AutoReplyType(str, Enum):
    """Types of auto-replies."""

    WELCOME = "welcome"
    RECEIVED = "received"
    OPT_OUT_CONFIRMED = "opt_out_confirmed"
    HUMAN_REQUESTED = "human_requested"
    OUTSIDE_HOURS = "outside_hours"


# Opt-out keywords (case insensitive)
OPTOUT_KEYWORDS = {
    "stop",
    "sair",
    "cancelar",
    "remover",
    "unsubscribe",
    "parar",
    "nao quero mais",
    "não quero mais",
}

# Intent keywords
INTENT_KEYWORDS: dict[ActionIntent, set[str]] = {
    ActionIntent.CREATE_QUOTE: {
        "cotacao",
        "cotação",
        "orcamento",
        "orçamento",
        "preco",
        "preço",
        "quanto custa",
        "valor",
    },
    ActionIntent.ORDER_STATUS: {
        "status",
        "pedido",
        "entrega",
        "rastrear",
        "acompanhar",
        "onde esta",
        "onde está",
        "meu pedido",
    },
    ActionIntent.TALK_TO_HUMAN: {
        "atendente",
        "humano",
        "pessoa",
        "falar com alguem",
        "falar com alguém",
        "ajuda",
        "help",
        "suporte",
    },
}

# Button IDs that map to intents
BUTTON_INTENTS: dict[str, ActionIntent] = {
    "btn_quote": ActionIntent.CREATE_QUOTE,
    "btn_status": ActionIntent.ORDER_STATUS,
    "btn_human": ActionIntent.TALK_TO_HUMAN,
    "create_quote": ActionIntent.CREATE_QUOTE,
    "order_status": ActionIntent.ORDER_STATUS,
    "talk_to_human": ActionIntent.TALK_TO_HUMAN,
}


@dataclass
class DetectionResult:
    """Result of keyword/intent detection."""

    is_optout: bool = False
    optout_keyword: str | None = None
    intent: ActionIntent | None = None
    intent_keyword: str | None = None
    confidence: float = 0.0


@dataclass
class AutoReply:
    """An auto-reply message to send."""

    reply_type: AutoReplyType
    text: str
    buttons: list[dict[str, str]] | None = None


class AutomationEngine:
    """
    Simple automation engine for WhatsApp messages.

    Detects:
    - Opt-out requests
    - Customer intents (quote, status, human)
    - Button clicks

    Generates:
    - Auto-reply messages
    - Action events for verticais
    """

    def __init__(
        self,
        optout_keywords: set[str] | None = None,
        intent_keywords: dict[ActionIntent, set[str]] | None = None,
        button_intents: dict[str, ActionIntent] | None = None,
    ):
        self.optout_keywords = optout_keywords or OPTOUT_KEYWORDS
        self.intent_keywords = intent_keywords or INTENT_KEYWORDS
        self.button_intents = button_intents or BUTTON_INTENTS

        # Default auto-reply messages (can be customized per tenant)
        self.auto_replies: dict[AutoReplyType, str] = {
            AutoReplyType.WELCOME: (
                "Olá! Bem-vindo ao {business_name}. "
                "Como posso ajudar você hoje?"
            ),
            AutoReplyType.RECEIVED: (
                "Mensagem recebida! Um vendedor vai te responder em breve."
            ),
            AutoReplyType.OPT_OUT_CONFIRMED: (
                "Você foi removido da nossa lista de mensagens. "
                "Se mudar de ideia, é só nos enviar uma mensagem."
            ),
            AutoReplyType.HUMAN_REQUESTED: (
                "Entendi! Um atendente vai entrar em contato com você em breve."
            ),
            AutoReplyType.OUTSIDE_HOURS: (
                "Obrigado pela mensagem! Estamos fora do horário de atendimento. "
                "Responderemos assim que possível."
            ),
        }

    def detect(
        self,
        text: str | None = None,
        button_payload: str | None = None,
    ) -> DetectionResult:
        """
        Detect opt-out or intent from message.

        Args:
            text: Message text (optional)
            button_payload: Button payload/ID (optional)

        Returns:
            DetectionResult with findings
        """
        result = DetectionResult()

        # Check button payload first (higher priority)
        if button_payload:
            intent = self.button_intents.get(button_payload)
            if intent:
                result.intent = intent
                result.intent_keyword = button_payload
                result.confidence = 1.0
                return result

        # Check text
        if not text:
            return result

        text_lower = text.lower().strip()

        # Check for opt-out
        for keyword in self.optout_keywords:
            if self._matches(text_lower, keyword):
                result.is_optout = True
                result.optout_keyword = keyword
                result.confidence = 1.0
                return result

        # Check for intents
        for intent, keywords in self.intent_keywords.items():
            for keyword in keywords:
                if self._matches(text_lower, keyword):
                    result.intent = intent
                    result.intent_keyword = keyword
                    result.confidence = 0.8  # Keyword match
                    return result

        return result

    def _matches(self, text: str, keyword: str) -> bool:
        """Check if text matches keyword (word boundary aware)."""
        # Escape special regex characters in keyword
        pattern = r"\b" + re.escape(keyword) + r"\b"
        return bool(re.search(pattern, text, re.IGNORECASE))

    def get_auto_reply(
        self,
        reply_type: AutoReplyType,
        variables: dict[str, str] | None = None,
        with_buttons: bool = False,
    ) -> AutoReply:
        """
        Get an auto-reply message.

        Args:
            reply_type: Type of auto-reply
            variables: Variables to substitute in template
            with_buttons: Whether to include quick reply buttons

        Returns:
            AutoReply with text and optional buttons
        """
        template = self.auto_replies.get(reply_type, "")

        # Substitute variables
        text = template
        if variables:
            for key, value in variables.items():
                text = text.replace(f"{{{key}}}", value)

        buttons = None
        if with_buttons and reply_type in (AutoReplyType.WELCOME, AutoReplyType.RECEIVED):
            buttons = self.get_default_buttons()

        return AutoReply(
            reply_type=reply_type,
            text=text,
            buttons=buttons,
        )

    def get_default_buttons(self) -> list[dict[str, str]]:
        """Get default quick reply buttons."""
        return [
            {"id": "btn_quote", "title": "Fazer cotação"},
            {"id": "btn_status", "title": "Status do pedido"},
            {"id": "btn_human", "title": "Falar com atendente"},
        ]

    def set_auto_reply(self, reply_type: AutoReplyType, template: str) -> None:
        """
        Set a custom auto-reply template.

        Args:
            reply_type: Type of auto-reply
            template: Template text (use {variable} for substitution)
        """
        self.auto_replies[reply_type] = template

    def should_auto_reply(
        self,
        is_new_conversation: bool,
        detection: DetectionResult,
        tenant_config: dict[str, Any] | None = None,
    ) -> AutoReplyType | None:
        """
        Determine if and what auto-reply to send.

        Args:
            is_new_conversation: Whether this is a new conversation
            detection: Detection result from message
            tenant_config: Tenant-specific configuration

        Returns:
            AutoReplyType to send, or None if no auto-reply
        """
        # Opt-out gets a confirmation
        if detection.is_optout:
            return AutoReplyType.OPT_OUT_CONFIRMED

        # Human request gets acknowledgment
        if detection.intent == ActionIntent.TALK_TO_HUMAN:
            return AutoReplyType.HUMAN_REQUESTED

        # New conversations get welcome
        if is_new_conversation:
            return AutoReplyType.WELCOME

        # Default: acknowledge receipt
        config = tenant_config or {}
        if config.get("auto_reply_enabled", True):
            return AutoReplyType.RECEIVED

        return None




