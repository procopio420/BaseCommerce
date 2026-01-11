"""
WhatsApp Service Layer

Handlers for processing inbound and outbound messages.
"""

from messaging_whatsapp.service.inbound_handler import InboundHandler
from messaging_whatsapp.service.outbound_handler import OutboundHandler
from messaging_whatsapp.service.automation import AutomationEngine

__all__ = [
    "InboundHandler",
    "OutboundHandler",
    "AutomationEngine",
]

