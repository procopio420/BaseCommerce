"""
Redis Streams Consumer for Engines

This consumer reads from Redis Streams using XREADGROUP and processes events
using the engines_core handlers. It is completely independent from any vertical code.

Features:
- Consumer group support for horizontal scaling
- Strong idempotency via engine_processed_events table
- XACK only after successful DB commit
"""

import json
import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from engines_core.contracts.envelope import EventEnvelope
from engines_core.handlers.router import handle_event

logger = logging.getLogger(__name__)


# Stream and group configuration
DEFAULT_STREAM_NAME = "events:materials"
DEFAULT_GROUP_NAME = "engines"


def is_event_processed(db: Session, event_id: UUID) -> bool:
    """Check if an event has already been processed (idempotency check)."""
    result = db.execute(
        text("SELECT 1 FROM engine_processed_events WHERE event_id = :event_id"),
        {"event_id": event_id},
    )
    return result.fetchone() is not None


def mark_event_processed(
    db: Session,
    event_id: UUID,
    tenant_id: UUID,
    vertical: str,
    event_type: str,
    result: dict | None = None,
) -> bool:
    """
    Mark an event as processed (idempotency).

    Uses INSERT ... ON CONFLICT DO NOTHING for atomic check-and-set.

    Returns:
        True if the event was marked (first time processing)
        False if it was already processed
    """
    insert_result = db.execute(
        text("""
            INSERT INTO engine_processed_events 
                (event_id, tenant_id, vertical, event_type, processed_at, result)
            VALUES 
                (:event_id, :tenant_id, :vertical, :event_type, :processed_at, :result)
            ON CONFLICT (event_id) DO NOTHING
        """),
        {
            "event_id": event_id,
            "tenant_id": tenant_id,
            "vertical": vertical,
            "event_type": event_type,
            "processed_at": datetime.utcnow(),
            "result": json.dumps(result) if result else None,
        },
    )
    return insert_result.rowcount > 0


def parse_stream_message(msg_id: str, data: dict[str, str]) -> EventEnvelope:
    """Parse a Redis Stream message into an EventEnvelope."""
    payload = json.loads(data.get("payload", "{}"))

    return EventEnvelope(
        event_id=UUID(data["event_id"]),
        event_type=data["event_type"],
        tenant_id=UUID(data["tenant_id"]),
        vertical=data.get("vertical", "materials"),
        occurred_at=datetime.fromisoformat(data["occurred_at"]) if data.get("occurred_at") else datetime.utcnow(),
        version=int(data.get("version", "1")),
        payload=payload,
        correlation_id=data.get("correlation_id"),
        metadata={"stream_msg_id": msg_id},
    )


def process_stream_message(
    db: Session,
    msg_id: str,
    data: dict[str, str],
) -> dict[str, Any]:
    """
    Process a single stream message.

    Implements idempotency:
    1. Parse envelope
    2. Check if already processed
    3. If not: process and mark as processed
    4. Commit transaction

    Returns:
        Processing result dict
    """
    envelope = parse_stream_message(msg_id, data)

    # Check idempotency
    if is_event_processed(db, envelope.event_id):
        logger.debug(f"Event {envelope.event_id} already processed, skipping")
        return {
            "event_id": str(envelope.event_id),
            "status": "skipped",
            "reason": "already_processed",
        }

    # Process the event
    try:
        result = handle_event(db, envelope)

        # Mark as processed (within same transaction)
        marked = mark_event_processed(
            db,
            envelope.event_id,
            envelope.tenant_id,
            envelope.vertical,
            envelope.event_type,
            result,
        )

        if not marked:
            # Race condition - another worker processed it
            logger.debug(f"Event {envelope.event_id} was processed by another worker")
            db.rollback()
            return {
                "event_id": str(envelope.event_id),
                "status": "skipped",
                "reason": "concurrent_processing",
            }

        # Commit all writes together
        db.commit()

        logger.info(
            f"Processed event {envelope.event_id}",
            extra={
                "event_id": str(envelope.event_id),
                "event_type": envelope.event_type,
                "tenant_id": str(envelope.tenant_id),
            },
        )

        return {
            "event_id": str(envelope.event_id),
            "status": "processed",
            "result": result,
        }

    except Exception as e:
        db.rollback()
        logger.error(
            f"Error processing event {envelope.event_id}: {e}",
            extra={
                "event_id": str(envelope.event_id),
                "event_type": envelope.event_type,
            },
            exc_info=True,
        )
        raise


def consume_from_stream(
    db: Session,
    stream_name: str = DEFAULT_STREAM_NAME,
    group_name: str = DEFAULT_GROUP_NAME,
    consumer_name: str = "engines-worker",
    count: int = 10,
    block_ms: int = 5000,
) -> int:
    """
    Consume and process messages from Redis Streams.

    Args:
        db: Database session
        stream_name: Redis stream name
        group_name: Consumer group name
        consumer_name: This consumer's name
        count: Max messages to read per batch
        block_ms: Milliseconds to block waiting for messages

    Returns:
        Number of messages processed
    """
    from basecore.redis import read_from_stream, ack_message

    messages = read_from_stream(
        stream_name,
        group_name,
        consumer_name,
        count=count,
        block_ms=block_ms,
    )

    if not messages:
        return 0

    processed_count = 0

    for msg_id, data in messages:
        try:
            result = process_stream_message(db, msg_id, data)

            # ACK the message after successful processing
            ack_message(stream_name, group_name, msg_id)
            processed_count += 1

            logger.debug(
                f"ACKed message {msg_id}",
                extra={"msg_id": msg_id, "result": result},
            )

        except Exception as e:
            # Don't ACK - message will be redelivered or reclaimed
            logger.error(
                f"Failed to process message {msg_id}: {e}",
                extra={"msg_id": msg_id},
                exc_info=True,
            )
            # Continue processing other messages

    return processed_count


def reclaim_pending_messages(
    db: Session,
    stream_name: str = DEFAULT_STREAM_NAME,
    group_name: str = DEFAULT_GROUP_NAME,
    consumer_name: str = "engines-worker",
    min_idle_ms: int = 60000,
    count: int = 100,
) -> int:
    """
    Reclaim and process pending messages that have been idle too long.

    This handles:
    - Messages from crashed consumers
    - Messages stuck in processing

    Idempotency protects against duplicate processing.

    Args:
        db: Database session
        stream_name: Redis stream name
        group_name: Consumer group name
        consumer_name: This consumer's name
        min_idle_ms: Minimum idle time in milliseconds
        count: Max messages to reclaim

    Returns:
        Number of messages reclaimed and processed
    """
    from basecore.redis import get_pending_messages, claim_messages, ack_message

    pending = get_pending_messages(stream_name, group_name, min_idle_ms, count)

    if not pending:
        return 0

    message_ids = [p["message_id"] for p in pending]
    claimed = claim_messages(stream_name, group_name, consumer_name, message_ids, min_idle_ms)

    if not claimed:
        return 0

    logger.info(f"Reclaimed {len(claimed)} pending messages")

    processed_count = 0

    for msg_id, data in claimed:
        try:
            result = process_stream_message(db, msg_id, data)
            ack_message(stream_name, group_name, msg_id)
            processed_count += 1

            logger.debug(
                f"Processed reclaimed message {msg_id}",
                extra={"msg_id": msg_id, "result": result},
            )

        except Exception as e:
            logger.error(
                f"Failed to process reclaimed message {msg_id}: {e}",
                extra={"msg_id": msg_id},
                exc_info=True,
            )

    return processed_count


# ============================================================
# Legacy DB polling consumer (for backwards compatibility)
# ============================================================

class OutboxStatus:
    """Status of outbox events."""
    PENDING = "pending"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"


def consume_outbox(
    db: Session,
    limit: int = 100,
    tenant_id: UUID | None = None,
) -> int:
    """
    DEPRECATED: Legacy DB polling consumer.

    Use consume_from_stream() instead for production.
    This is kept for backwards compatibility during migration.
    """
    logger.warning("Using legacy DB polling consumer - migrate to Redis Streams")

    query = """
        SELECT 
            id, event_id, tenant_id, event_type, 
            payload, version, status, created_at
        FROM event_outbox
        WHERE status = :status
    """
    params: dict[str, Any] = {"status": OutboxStatus.PENDING}

    if tenant_id:
        query += " AND tenant_id = :tenant_id"
        params["tenant_id"] = tenant_id

    query += " ORDER BY created_at ASC LIMIT :limit"
    params["limit"] = limit

    result = db.execute(text(query), params)

    events = []
    for row in result:
        events.append({
            "id": row[0],
            "event_id": row[1],
            "tenant_id": row[2],
            "event_type": row[3],
            "payload": row[4],
            "version": row[5],
            "status": row[6],
            "created_at": row[7],
        })

    processed_count = 0

    for event_data in events:
        event_id = event_data["event_id"]

        # Try to lock the event
        lock_result = db.execute(
            text("""
                UPDATE event_outbox
                SET status = :new_status
                WHERE event_id = :event_id AND status = :old_status
            """),
            {
                "new_status": OutboxStatus.PROCESSING,
                "old_status": OutboxStatus.PENDING,
                "event_id": event_id,
            },
        )
        db.commit()

        if lock_result.rowcount == 0:
            continue

        try:
            envelope = EventEnvelope(
                event_id=event_id,
                event_type=event_data["event_type"],
                tenant_id=event_data["tenant_id"],
                vertical=event_data.get("vertical", "materials"),
                occurred_at=event_data["created_at"],
                version=int(str(event_data.get("version", "1")).split(".")[0]),
                payload=event_data["payload"] or {},
            )

            handle_event(db, envelope)

            db.execute(
                text("""
                    UPDATE event_outbox
                    SET status = :status, processed_at = :now
                    WHERE event_id = :event_id
                """),
                {
                    "status": OutboxStatus.PROCESSED,
                    "now": datetime.utcnow(),
                    "event_id": event_id,
                },
            )
            db.commit()
            processed_count += 1

        except Exception as e:
            logger.error(f"Error processing event {event_id}: {e}", exc_info=True)
            db.execute(
                text("""
                    UPDATE event_outbox
                    SET status = :status, error_message = :error
                    WHERE event_id = :event_id
                """),
                {
                    "status": OutboxStatus.FAILED,
                    "error": str(e),
                    "event_id": event_id,
                },
            )
            db.commit()

    return processed_count
