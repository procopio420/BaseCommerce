"""
WhatsApp Event Envelope

Standard wrapper for WhatsApp engine events.
Compatible with engines_core EventEnvelope but specialized for WhatsApp.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4


@dataclass
class WhatsAppEnvelope:
    """
    Standard event envelope for WhatsApp engine events.

    This envelope is used:
    - By the webhook to publish inbound events to Redis Streams
    - By the worker to consume and process events
    - By the worker to publish outbound events

    Attributes:
        event_id: Unique identifier for this event instance
        event_type: Type of event (WhatsAppEventType value)
        tenant_id: Multi-tenant isolation key
        occurred_at: When the event occurred (UTC)
        version: Event contract version
        payload: Event-specific data
        correlation_id: Optional correlation ID for tracing
        metadata: Additional metadata (retry count, source, etc.)
    """

    event_id: UUID
    event_type: str
    tenant_id: UUID
    occurred_at: datetime
    payload: dict[str, Any]
    version: int = 1
    correlation_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        event_type: str,
        tenant_id: UUID,
        payload: dict[str, Any],
        correlation_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "WhatsAppEnvelope":
        """Create a new envelope with auto-generated event_id and timestamp."""
        return cls(
            event_id=uuid4(),
            event_type=event_type,
            tenant_id=tenant_id,
            occurred_at=datetime.utcnow(),
            payload=payload,
            correlation_id=correlation_id,
            metadata=metadata or {},
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WhatsAppEnvelope":
        """Create an envelope from a dictionary (e.g., from Redis Stream)."""
        return cls(
            event_id=UUID(data["event_id"]) if isinstance(data["event_id"], str) else data["event_id"],
            event_type=data["event_type"],
            tenant_id=UUID(data["tenant_id"]) if isinstance(data["tenant_id"], str) else data["tenant_id"],
            occurred_at=(
                datetime.fromisoformat(data["occurred_at"])
                if isinstance(data["occurred_at"], str)
                else data["occurred_at"]
            ),
            version=int(data.get("version", 1)),
            payload=data.get("payload", {}),
            correlation_id=data.get("correlation_id"),
            metadata=data.get("metadata", {}),
        )

    @classmethod
    def from_stream_message(cls, msg_id: str, data: dict[str, str]) -> "WhatsAppEnvelope":
        """Parse a Redis Stream message into an envelope."""
        payload = json.loads(data.get("payload", "{}"))
        metadata = json.loads(data.get("metadata", "{}"))
        metadata["stream_msg_id"] = msg_id

        return cls(
            event_id=UUID(data["event_id"]),
            event_type=data["event_type"],
            tenant_id=UUID(data["tenant_id"]),
            occurred_at=(
                datetime.fromisoformat(data["occurred_at"])
                if data.get("occurred_at")
                else datetime.utcnow()
            ),
            version=int(data.get("version", "1")),
            payload=payload,
            correlation_id=data.get("correlation_id"),
            metadata=metadata,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "event_id": str(self.event_id),
            "event_type": self.event_type,
            "tenant_id": str(self.tenant_id),
            "occurred_at": self.occurred_at.isoformat(),
            "version": self.version,
            "payload": self.payload,
            "correlation_id": self.correlation_id,
            "metadata": self.metadata,
        }

    def to_stream_data(self) -> dict[str, str]:
        """Convert to dictionary suitable for Redis Stream (all string values)."""
        return {
            "event_id": str(self.event_id),
            "event_type": self.event_type,
            "tenant_id": str(self.tenant_id),
            "occurred_at": self.occurred_at.isoformat(),
            "version": str(self.version),
            "payload": json.dumps(self.payload),
            "correlation_id": self.correlation_id or "",
            "metadata": json.dumps(self.metadata),
        }

