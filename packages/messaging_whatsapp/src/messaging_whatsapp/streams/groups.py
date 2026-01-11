"""
Redis Stream Configuration

Stream names, consumer groups, and setup utilities.
"""

import logging
from dataclasses import dataclass

import redis

logger = logging.getLogger(__name__)

# Stream names
INBOUND_STREAM = "bc:whatsapp:inbound"
OUTBOUND_STREAM = "bc:whatsapp:outbound"
DLQ_STREAM = "bc:whatsapp:dlq"

# Consumer group
WHATSAPP_GROUP = "whatsapp-engine"

# For consuming vertical events (same stream as engines)
VERTICAL_EVENTS_STREAM = "events:materials"
WHATSAPP_NOTIFIER_GROUP = "whatsapp-notifier"


@dataclass
class StreamConfig:
    """Configuration for a stream and its consumer group."""

    stream_name: str
    group_name: str
    max_len: int = 100000
    start_id: str = "0"  # "0" = all history, "$" = new only


# Default configurations
STREAM_CONFIGS = [
    StreamConfig(INBOUND_STREAM, WHATSAPP_GROUP),
    StreamConfig(OUTBOUND_STREAM, WHATSAPP_GROUP),
    StreamConfig(DLQ_STREAM, WHATSAPP_GROUP),
    StreamConfig(VERTICAL_EVENTS_STREAM, WHATSAPP_NOTIFIER_GROUP, start_id="$"),
]


def ensure_stream_group(
    client: redis.Redis,
    stream_name: str,
    group_name: str,
    start_id: str = "0",
) -> bool:
    """
    Ensure a consumer group exists for a stream.

    Creates the group if it doesn't exist. Safe to call multiple times.

    Args:
        client: Redis client
        stream_name: Name of the Redis stream
        group_name: Name of the consumer group
        start_id: ID from which to start reading ("0" = all, "$" = new only)

    Returns:
        True if group was created, False if it already existed
    """
    try:
        client.xgroup_create(stream_name, group_name, id=start_id, mkstream=True)
        logger.info(f"Created consumer group '{group_name}' for stream '{stream_name}'")
        return True
    except redis.ResponseError as e:
        if "BUSYGROUP" in str(e):
            logger.debug(f"Consumer group '{group_name}' already exists for '{stream_name}'")
            return False
        raise


def ensure_whatsapp_streams(client: redis.Redis) -> None:
    """
    Ensure all WhatsApp streams and consumer groups exist.

    Should be called on startup by webhook and worker services.
    """
    for config in STREAM_CONFIGS:
        ensure_stream_group(
            client,
            config.stream_name,
            config.group_name,
            config.start_id,
        )


def get_stream_info(client: redis.Redis, stream_name: str) -> dict:
    """Get information about a stream."""
    try:
        info = client.xinfo_stream(stream_name)
        return {
            "length": info.get("length", 0),
            "first_entry": info.get("first-entry"),
            "last_entry": info.get("last-entry"),
            "groups": client.xinfo_groups(stream_name),
        }
    except redis.ResponseError:
        return {"length": 0, "error": "Stream does not exist"}


def get_pending_count(
    client: redis.Redis,
    stream_name: str,
    group_name: str,
) -> int:
    """Get count of pending (unacknowledged) messages in a group."""
    try:
        info = client.xpending(stream_name, group_name)
        return info.get("pending", 0) if info else 0
    except redis.ResponseError:
        return 0

