"""
Outbox Relay - DB to Redis Streams

This service:
1. Polls DB outbox for unpublished events
2. Publishes each event to Redis Streams
3. Marks events as published

Uses FOR UPDATE SKIP LOCKED for safe multi-replica operation.
"""

import json
import logging
import os
import signal
import sys
import time
from datetime import datetime
from typing import Any
from uuid import UUID

from basecore.db import get_db
from basecore.logging import setup_logging
from basecore.redis import ensure_stream_group, publish_to_stream

setup_logging()
logger = logging.getLogger(__name__)

# Configuration
BATCH_SIZE = int(os.getenv("RELAY_BATCH_SIZE", "100"))
POLL_INTERVAL_EMPTY = float(os.getenv("RELAY_POLL_INTERVAL_EMPTY", "5.0"))
POLL_INTERVAL_BUSY = float(os.getenv("RELAY_POLL_INTERVAL_BUSY", "0.1"))
STREAM_MAX_LEN = int(os.getenv("RELAY_STREAM_MAX_LEN", "100000"))

# Graceful shutdown
shutdown_requested = False


def signal_handler(signum, frame):
    global shutdown_requested
    logger.info(f"Received signal {signum}, requesting shutdown...")
    shutdown_requested = True


signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)


def get_unpublished_events(db, limit: int = 100) -> list[dict[str, Any]]:
    """
    Get unpublished events from outbox with row locking.

    Uses FOR UPDATE SKIP LOCKED to allow multiple relay instances.
    """
    from sqlalchemy import text

    query = text("""
        SELECT 
            id, event_id, tenant_id, event_type, 
            payload, version, created_at
        FROM event_outbox
        WHERE published_at IS NULL
          AND status IN ('pending', 'processing', 'processed')
        ORDER BY created_at ASC
        LIMIT :limit
        FOR UPDATE SKIP LOCKED
    """)

    result = db.execute(query, {"limit": limit})

    events = []
    for row in result:
        events.append({
            "id": row[0],
            "event_id": row[1],
            "tenant_id": row[2],
            "event_type": row[3],
            "payload": row[4],
            "version": row[5],
            "created_at": row[6],
        })

    return events


def mark_published(db, event_ids: list[UUID]) -> int:
    """Mark events as published."""
    if not event_ids:
        return 0

    from sqlalchemy import text

    result = db.execute(
        text("""
            UPDATE event_outbox
            SET published_at = :now
            WHERE id = ANY(:ids)
        """),
        {"now": datetime.utcnow(), "ids": event_ids},
    )
    return result.rowcount


def get_stream_name(vertical: str) -> str:
    """Get Redis stream name for a vertical."""
    return f"events:{vertical}"


def publish_event_to_stream(event: dict[str, Any]) -> str:
    """
    Publish a single event to Redis Streams.

    Returns the stream message ID.
    """
    # Extract vertical from payload or default
    payload = event["payload"] or {}
    vertical = payload.get("vertical", "materials")

    stream_name = get_stream_name(vertical)

    # Prepare message data
    message_data = {
        "event_id": str(event["event_id"]),
        "tenant_id": str(event["tenant_id"]),
        "event_type": event["event_type"],
        "vertical": vertical,
        "version": str(event["version"]),
        "occurred_at": event["created_at"].isoformat() if event["created_at"] else datetime.utcnow().isoformat(),
        "payload": json.dumps(payload),
    }

    return publish_to_stream(stream_name, message_data, max_len=STREAM_MAX_LEN)


def relay_batch(db) -> int:
    """
    Relay a batch of events from DB to Redis Streams.

    Returns number of events published.
    """
    events = get_unpublished_events(db, limit=BATCH_SIZE)

    if not events:
        return 0

    published_ids = []
    published_count = 0

    for event in events:
        try:
            stream_msg_id = publish_event_to_stream(event)
            published_ids.append(event["id"])
            published_count += 1

            logger.debug(
                f"Published event {event['event_id']} to stream",
                extra={
                    "event_id": str(event["event_id"]),
                    "event_type": event["event_type"],
                    "stream_msg_id": stream_msg_id,
                },
            )
        except Exception as e:
            logger.error(
                f"Failed to publish event {event['event_id']}: {e}",
                extra={"event_id": str(event["event_id"])},
                exc_info=True,
            )
            # Continue with other events

    # Mark successfully published events
    if published_ids:
        mark_published(db, published_ids)
        db.commit()

    return published_count


def ensure_stream_groups():
    """Ensure consumer groups exist for all known verticals."""
    verticals = ["materials"]  # Add more as needed

    for vertical in verticals:
        stream_name = get_stream_name(vertical)
        created = ensure_stream_group(stream_name, "engines", start_id="0")
        if created:
            logger.info(f"Created consumer group 'engines' for stream '{stream_name}'")
        else:
            logger.debug(f"Consumer group 'engines' already exists for stream '{stream_name}'")


def main():
    """Main relay loop."""
    logger.info(
        f"Starting outbox relay (batch_size={BATCH_SIZE}, "
        f"poll_empty={POLL_INTERVAL_EMPTY}s, poll_busy={POLL_INTERVAL_BUSY}s)"
    )

    # Ensure consumer groups exist
    ensure_stream_groups()

    consecutive_empty = 0

    while not shutdown_requested:
        db = next(get_db())
        try:
            count = relay_batch(db)

            if count > 0:
                logger.info(f"Relayed {count} events to Redis Streams")
                consecutive_empty = 0
                time.sleep(POLL_INTERVAL_BUSY)
            else:
                consecutive_empty += 1
                # Exponential backoff with max
                sleep_time = min(POLL_INTERVAL_EMPTY * (1.5 ** min(consecutive_empty, 5)), 30)
                time.sleep(sleep_time)

        except Exception as e:
            logger.error(f"Error in relay loop: {e}", exc_info=True)
            db.rollback()
            time.sleep(POLL_INTERVAL_EMPTY)
        finally:
            db.close()

    logger.info("Outbox relay shutting down gracefully")


if __name__ == "__main__":
    main()

