"""Evolution API WhatsApp provider."""

from messaging_whatsapp.providers.evolution.client import EvolutionWhatsAppProvider
from messaging_whatsapp.providers.evolution.webhook import parse_evolution_webhook
from messaging_whatsapp.providers.evolution.instance_manager import EvolutionInstanceManager

__all__ = [
    "EvolutionWhatsAppProvider",
    "parse_evolution_webhook",
    "EvolutionInstanceManager",
]




