"""
Event Envelope - Standard wrapper for all engine events.

This envelope is used by the outbox relay to publish events to Redis Streams
and by the engines worker to consume them.

The payload MUST be self-contained with all data needed for engines to operate
without querying vertical tables.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass
class EventEnvelope:
    """
    Standard event envelope for engine events.

    All events flowing through the system are wrapped in this envelope.
    The payload contains all data needed for engines to process the event
    without querying vertical tables.

    Attributes:
        event_id: Unique identifier for this event instance
        event_type: Type of event (e.g., "quote_converted", "sale_recorded")
        tenant_id: Multi-tenant isolation key
        vertical: Vertical identifier (e.g., "materials", "restaurant")
        occurred_at: When the event occurred (UTC)
        version: Event contract version (for schema evolution)
        payload: Self-contained event data (no need to query vertical tables)
        correlation_id: Optional correlation ID for tracing
        metadata: Optional metadata (retry count, source, etc.)
    """

    event_id: UUID
    event_type: str
    tenant_id: UUID
    vertical: str
    occurred_at: datetime
    version: int
    payload: dict[str, Any]
    correlation_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EventEnvelope":
        """Create an EventEnvelope from a dictionary (e.g., from Redis Stream)."""
        return cls(
            event_id=UUID(data["event_id"]) if isinstance(data["event_id"], str) else data["event_id"],
            event_type=data["event_type"],
            tenant_id=UUID(data["tenant_id"]) if isinstance(data["tenant_id"], str) else data["tenant_id"],
            vertical=data.get("vertical", "materials"),  # default for backward compat
            occurred_at=datetime.fromisoformat(data["occurred_at"]) if isinstance(data["occurred_at"], str) else data["occurred_at"],
            version=int(data.get("version", 1)),
            payload=data.get("payload", {}),
            correlation_id=data.get("correlation_id"),
            metadata=data.get("metadata", {}),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "event_id": str(self.event_id),
            "event_type": self.event_type,
            "tenant_id": str(self.tenant_id),
            "vertical": self.vertical,
            "occurred_at": self.occurred_at.isoformat(),
            "version": self.version,
            "payload": self.payload,
            "correlation_id": self.correlation_id,
            "metadata": self.metadata,
        }

