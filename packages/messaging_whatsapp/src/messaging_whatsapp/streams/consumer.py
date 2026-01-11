"""
WhatsApp Stream Consumer

Consumes events from Redis Streams using XREADGROUP.
"""

import logging
from typing import Any, Callable

import redis

from messaging_whatsapp.contracts.envelope import WhatsAppEnvelope
from messaging_whatsapp.streams.groups import WHATSAPP_GROUP

logger = logging.getLogger(__name__)


class WhatsAppStreamConsumer:
    """
    Consumer for reading WhatsApp events from Redis Streams.

    Uses XREADGROUP for consumer group support and reliable delivery.
    """

    def __init__(
        self,
        redis_client: redis.Redis,
        consumer_name: str,
        group_name: str = WHATSAPP_GROUP,
    ):
        self.redis = redis_client
        self.consumer_name = consumer_name
        self.group_name = group_name

    def read_messages(
        self,
        stream_name: str,
        count: int = 10,
        block_ms: int = 5000,
    ) -> list[tuple[str, WhatsAppEnvelope]]:
        """
        Read messages from a stream.

        Args:
            stream_name: Name of the stream to read from
            count: Maximum messages to read
            block_ms: Milliseconds to block waiting for messages

        Returns:
            List of (message_id, envelope) tuples
        """
        try:
            result = self.redis.xreadgroup(
                self.group_name,
                self.consumer_name,
                {stream_name: ">"},
                count=count,
                block=block_ms,
            )

            if not result:
                return []

            messages = []
            for _stream, entries in result:
                for msg_id, data in entries:
                    try:
                        envelope = WhatsAppEnvelope.from_stream_message(msg_id, data)
                        messages.append((msg_id, envelope))
                    except Exception as e:
                        logger.error(f"Failed to parse message {msg_id}: {e}")
                        # ACK invalid messages to prevent blocking
                        self.ack(stream_name, msg_id)

            return messages

        except redis.ResponseError as e:
            if "NOGROUP" in str(e):
                logger.error(f"Consumer group {self.group_name} does not exist for {stream_name}")
            raise

    def read_from_multiple_streams(
        self,
        streams: list[str],
        count: int = 10,
        block_ms: int = 5000,
    ) -> dict[str, list[tuple[str, WhatsAppEnvelope]]]:
        """
        Read messages from multiple streams.

        Args:
            streams: List of stream names
            count: Maximum messages per stream
            block_ms: Milliseconds to block

        Returns:
            Dict mapping stream name to list of (message_id, envelope) tuples
        """
        try:
            stream_ids = {stream: ">" for stream in streams}
            result = self.redis.xreadgroup(
                self.group_name,
                self.consumer_name,
                stream_ids,
                count=count,
                block=block_ms,
            )

            if not result:
                return {}

            messages: dict[str, list[tuple[str, WhatsAppEnvelope]]] = {}
            for stream_name, entries in result:
                stream_messages = []
                for msg_id, data in entries:
                    try:
                        envelope = WhatsAppEnvelope.from_stream_message(msg_id, data)
                        stream_messages.append((msg_id, envelope))
                    except Exception as e:
                        logger.error(f"Failed to parse message {msg_id}: {e}")
                        self.ack(stream_name, msg_id)

                if stream_messages:
                    messages[stream_name] = stream_messages

            return messages

        except redis.ResponseError as e:
            logger.error(f"Error reading from streams: {e}")
            raise

    def ack(self, stream_name: str, message_id: str) -> int:
        """
        Acknowledge a message as processed.

        Args:
            stream_name: Stream the message came from
            message_id: ID of the message to acknowledge

        Returns:
            Number of messages acknowledged (0 or 1)
        """
        return self.redis.xack(stream_name, self.group_name, message_id)

    def get_pending(
        self,
        stream_name: str,
        min_idle_ms: int = 60000,
        count: int = 100,
    ) -> list[dict[str, Any]]:
        """
        Get pending messages that have been idle too long.

        Args:
            stream_name: Stream to check
            min_idle_ms: Minimum idle time in milliseconds
            count: Maximum messages to return

        Returns:
            List of pending message info dicts
        """
        try:
            pending_info = self.redis.xpending(stream_name, self.group_name)
            if not pending_info or pending_info.get("pending", 0) == 0:
                return []

            pending_range = self.redis.xpending_range(
                stream_name,
                self.group_name,
                min="-",
                max="+",
                count=count,
            )

            idle_messages = []
            for entry in pending_range:
                if entry.get("time_since_delivered", 0) >= min_idle_ms:
                    idle_messages.append({
                        "message_id": entry["message_id"],
                        "consumer": entry["consumer"],
                        "idle_ms": entry["time_since_delivered"],
                        "delivery_count": entry["times_delivered"],
                    })

            return idle_messages

        except redis.ResponseError:
            return []

    def claim_messages(
        self,
        stream_name: str,
        message_ids: list[str],
        min_idle_ms: int = 60000,
    ) -> list[tuple[str, WhatsAppEnvelope]]:
        """
        Claim pending messages from other consumers.

        Args:
            stream_name: Stream to claim from
            message_ids: List of message IDs to claim
            min_idle_ms: Minimum idle time for claiming

        Returns:
            List of (message_id, envelope) tuples for claimed messages
        """
        if not message_ids:
            return []

        try:
            result = self.redis.xclaim(
                stream_name,
                self.group_name,
                self.consumer_name,
                min_idle_ms,
                message_ids,
            )

            messages = []
            for msg_id, data in result:
                try:
                    envelope = WhatsAppEnvelope.from_stream_message(msg_id, data)
                    messages.append((msg_id, envelope))
                except Exception as e:
                    logger.error(f"Failed to parse claimed message {msg_id}: {e}")

            return messages

        except redis.ResponseError as e:
            logger.error(f"Failed to claim messages: {e}")
            return []

    def reclaim_pending(
        self,
        stream_name: str,
        min_idle_ms: int = 60000,
        count: int = 100,
    ) -> list[tuple[str, WhatsAppEnvelope]]:
        """
        Reclaim and return pending messages that have been idle.

        Combines get_pending and claim_messages.

        Args:
            stream_name: Stream to reclaim from
            min_idle_ms: Minimum idle time
            count: Maximum messages to reclaim

        Returns:
            List of (message_id, envelope) tuples
        """
        pending = self.get_pending(stream_name, min_idle_ms, count)
        if not pending:
            return []

        message_ids = [p["message_id"] for p in pending]
        return self.claim_messages(stream_name, message_ids, min_idle_ms)

