"""
Engine-owned persistence models.

These tables are OWNED by engines, not by verticals.
Engines write to these tables, verticals only read from them.
"""

from engines_core.persistence.models import (
    EngineBase,
    EngineStockAlert,
    EngineReplenishmentSuggestion,
    EngineSalesSuggestion,
    EngineSupplierPriceAlert,
    EngineDeliveryRoute,
)
from engines_core.persistence.facts import (
    EngineSalesFact,
    EngineStockFact,
)

__all__ = [
    "EngineBase",
    "EngineStockAlert",
    "EngineReplenishmentSuggestion",
    "EngineSalesSuggestion",
    "EngineSupplierPriceAlert",
    "EngineDeliveryRoute",
    "EngineSalesFact",
    "EngineStockFact",
]

