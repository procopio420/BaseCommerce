"""
WhatsApp Engine Persistence

SQLAlchemy models and repository for WhatsApp engine tables.
These tables are OWNED by the WhatsApp engine - no vertical should modify them directly.
"""

from messaging_whatsapp.persistence.models import (
    WhatsAppBase,
    WhatsAppTenantBinding,
    WhatsAppConversation,
    WhatsAppMessage,
    WhatsAppOptOut,
    ConversationStatus,
    MessageDirection,
    MessageStatus,
)
from messaging_whatsapp.persistence.repo import WhatsAppRepository

__all__ = [
    "WhatsAppBase",
    "WhatsAppTenantBinding",
    "WhatsAppConversation",
    "WhatsAppMessage",
    "WhatsAppOptOut",
    "WhatsAppRepository",
    "ConversationStatus",
    "MessageDirection",
    "MessageStatus",
]




