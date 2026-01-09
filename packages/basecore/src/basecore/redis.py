"""
Redis client utilities for basecore.

Provides lazy-initialized Redis client to avoid import-time connections.
"""

import functools
import os
from typing import Any

import redis


@functools.lru_cache()
def get_redis_url() -> str:
    """Get Redis URL from environment."""
    return os.getenv("REDIS_URL", "redis://localhost:6379/0")


@functools.lru_cache()
def get_redis_client() -> redis.Redis:
    """
    Get Redis client (cached).

    This function lazily initializes the Redis client to avoid import-time connections.
    """
    url = get_redis_url()
    return redis.from_url(url, decode_responses=True)


def ensure_stream_group(
    stream_name: str,
    group_name: str,
    start_id: str = "0",
) -> bool:
    """
    Ensure a consumer group exists for a stream.

    Creates the group if it doesn't exist. Safe to call multiple times.

    Args:
        stream_name: Name of the Redis stream
        group_name: Name of the consumer group
        start_id: ID from which to start reading ("0" = all, "$" = new only)

    Returns:
        True if group was created, False if it already existed
    """
    client = get_redis_client()
    try:
        client.xgroup_create(stream_name, group_name, id=start_id, mkstream=True)
        return True
    except redis.ResponseError as e:
        if "BUSYGROUP" in str(e):
            # Group already exists
            return False
        raise


def publish_to_stream(
    stream_name: str,
    data: dict[str, Any],
    max_len: int | None = 10000,
) -> str:
    """
    Publish a message to a Redis stream.

    Args:
        stream_name: Name of the Redis stream
        data: Dictionary of field-value pairs to publish
        max_len: Maximum stream length (approximate trim)

    Returns:
        Message ID assigned by Redis
    """
    client = get_redis_client()

    # Convert all values to strings for Redis
    string_data = {k: str(v) if not isinstance(v, str) else v for k, v in data.items()}

    if max_len:
        return client.xadd(stream_name, string_data, maxlen=max_len, approximate=True)
    return client.xadd(stream_name, string_data)


def read_from_stream(
    stream_name: str,
    group_name: str,
    consumer_name: str,
    count: int = 10,
    block_ms: int = 5000,
) -> list[tuple[str, dict[str, str]]]:
    """
    Read messages from a Redis stream using consumer group.

    Args:
        stream_name: Name of the Redis stream
        group_name: Name of the consumer group
        consumer_name: Name of this consumer
        count: Maximum messages to read
        block_ms: Milliseconds to block waiting for messages

    Returns:
        List of (message_id, data) tuples
    """
    client = get_redis_client()

    result = client.xreadgroup(
        group_name,
        consumer_name,
        {stream_name: ">"},
        count=count,
        block=block_ms,
    )

    if not result:
        return []

    # Result format: [[stream_name, [(msg_id, data), ...]]]
    messages = []
    for _stream, entries in result:
        for msg_id, data in entries:
            messages.append((msg_id, data))

    return messages


def ack_message(stream_name: str, group_name: str, message_id: str) -> int:
    """
    Acknowledge a message as processed.

    Args:
        stream_name: Name of the Redis stream
        group_name: Name of the consumer group
        message_id: ID of the message to acknowledge

    Returns:
        Number of messages acknowledged (0 or 1)
    """
    client = get_redis_client()
    return client.xack(stream_name, group_name, message_id)


def get_pending_messages(
    stream_name: str,
    group_name: str,
    min_idle_ms: int = 60000,
    count: int = 100,
) -> list[dict[str, Any]]:
    """
    Get pending messages that have been idle for too long.

    Args:
        stream_name: Name of the Redis stream
        group_name: Name of the consumer group
        min_idle_ms: Minimum idle time in milliseconds
        count: Maximum messages to return

    Returns:
        List of pending message info dicts
    """
    client = get_redis_client()

    # Get pending entries summary first
    pending_info = client.xpending(stream_name, group_name)
    if not pending_info or pending_info["pending"] == 0:
        return []

    # Get detailed pending entries
    pending_range = client.xpending_range(
        stream_name,
        group_name,
        min="-",
        max="+",
        count=count,
    )

    # Filter by idle time
    idle_messages = []
    for entry in pending_range:
        if entry["time_since_delivered"] >= min_idle_ms:
            idle_messages.append({
                "message_id": entry["message_id"],
                "consumer": entry["consumer"],
                "idle_ms": entry["time_since_delivered"],
                "delivery_count": entry["times_delivered"],
            })

    return idle_messages


def claim_messages(
    stream_name: str,
    group_name: str,
    consumer_name: str,
    message_ids: list[str],
    min_idle_ms: int = 60000,
) -> list[tuple[str, dict[str, str]]]:
    """
    Claim pending messages from other consumers.

    Args:
        stream_name: Name of the Redis stream
        group_name: Name of the consumer group
        consumer_name: Name of this consumer (who will claim)
        message_ids: List of message IDs to claim
        min_idle_ms: Minimum idle time for claiming

    Returns:
        List of (message_id, data) tuples for claimed messages
    """
    if not message_ids:
        return []

    client = get_redis_client()

    result = client.xclaim(
        stream_name,
        group_name,
        consumer_name,
        min_idle_ms,
        message_ids,
    )

    return [(msg_id, data) for msg_id, data in result]

