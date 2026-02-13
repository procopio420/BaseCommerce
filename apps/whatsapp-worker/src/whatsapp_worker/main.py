"""
WhatsApp Worker Service

Consumes WhatsApp events from Redis Streams and processes them.

This worker uses ONLY:
- basecore (DB, settings, logging, redis)
- messaging_whatsapp (handlers, contracts, providers)

NO imports from backend/ or verticals are allowed.

Features:
- XREADGROUP consumer for horizontal scaling
- PEL reclaim for stuck messages
- Strong idempotency
- Graceful shutdown
- Multi-stream consumption (inbound, outbound, vertical events)
"""

import asyncio
import logging
import os
import signal
import socket
import sys
import threading
import time

from basecore.db import get_db
from basecore.logging import setup_logging
from basecore.redis import get_redis_client

from messaging_whatsapp.providers.base import WhatsAppProvider
from messaging_whatsapp.providers.meta_cloud import MetaCloudWhatsAppProvider
from messaging_whatsapp.providers.stub import StubWhatsAppProvider
from messaging_whatsapp.service.inbound_handler import InboundHandler
from messaging_whatsapp.service.outbound_handler import OutboundHandler
from messaging_whatsapp.streams.consumer import WhatsAppStreamConsumer
from messaging_whatsapp.streams.groups import (
    DLQ_STREAM,
    INBOUND_STREAM,
    OUTBOUND_STREAM,
    VERTICAL_EVENTS_STREAM,
    WHATSAPP_GROUP,
    WHATSAPP_NOTIFIER_GROUP,
    ensure_whatsapp_streams,
)

setup_logging()
logger = logging.getLogger(__name__)

# Configuration
CONSUMER_NAME = os.getenv(
    "WHATSAPP_CONSUMER_NAME",
    f"whatsapp-worker-{socket.gethostname()}-{os.getpid()}",
)
BATCH_SIZE = int(os.getenv("WHATSAPP_BATCH_SIZE", "10"))
BLOCK_MS = int(os.getenv("WHATSAPP_BLOCK_MS", "5000"))
RECLAIM_INTERVAL_SEC = int(os.getenv("WHATSAPP_RECLAIM_INTERVAL", "60"))
RECLAIM_IDLE_MS = int(os.getenv("WHATSAPP_RECLAIM_IDLE_MS", "60000"))
WHATSAPP_PROVIDER = os.getenv("WHATSAPP_PROVIDER", "stub")

# Graceful shutdown
shutdown_requested = False


def signal_handler(signum, frame):
    global shutdown_requested
    logger.info(f"Received signal {signum}, requesting shutdown...")
    shutdown_requested = True


signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)


def get_provider() -> WhatsAppProvider:
    """Get the appropriate WhatsApp provider."""
    if WHATSAPP_PROVIDER == "meta":
        return MetaCloudWhatsAppProvider()
    return StubWhatsAppProvider()


def process_inbound_messages(redis_client, consumer: WhatsAppStreamConsumer) -> int:
    """Process inbound messages from the stream."""
    messages = consumer.read_messages(
        INBOUND_STREAM,
        count=BATCH_SIZE,
        block_ms=BLOCK_MS,
    )

    if not messages:
        return 0

    processed = 0
    db = next(get_db())

    try:
        handler = InboundHandler(db, redis_client)

        for msg_id, envelope in messages:
            try:
                # Check if this is a status update
                if envelope.payload.get("is_status_update"):
                    from messaging_whatsapp.providers.base import DeliveryStatus
                    from datetime import datetime

                    status = DeliveryStatus(
                        message_id=envelope.payload.get("provider_message_id", ""),
                        recipient_phone=envelope.payload.get("recipient_phone", ""),
                        status=envelope.payload.get("status", ""),
                        timestamp=datetime.utcnow(),
                        error_code=envelope.payload.get("error_code"),
                        error_message=envelope.payload.get("error_message"),
                    )
                    result = handler.handle_delivery_status(envelope.tenant_id, status)
                else:
                    result = handler.handle_envelope(envelope)

                consumer.ack(INBOUND_STREAM, msg_id)
                processed += 1

                logger.debug(
                    f"Processed inbound message",
                    extra={"msg_id": msg_id, "result": result},
                )

            except Exception as e:
                logger.error(
                    f"Failed to process inbound message {msg_id}: {e}",
                    exc_info=True,
                )
                # Don't ACK - will be reclaimed

    finally:
        db.close()

    return processed


async def process_outbound_messages(redis_client, consumer: WhatsAppStreamConsumer) -> int:
    """Process outbound messages from the stream."""
    messages = consumer.read_messages(
        OUTBOUND_STREAM,
        count=BATCH_SIZE,
        block_ms=100,  # Short block for outbound
    )

    if not messages:
        return 0

    processed = 0
    db = next(get_db())
    provider = get_provider()

    try:
        handler = OutboundHandler(db, redis_client, provider)

        for msg_id, envelope in messages:
            try:
                result = await handler.handle_envelope(envelope)

                # ACK if processed (even if failed after retries)
                if result.get("status") in ("sent", "blocked") or result.get("sent_to_dlq"):
                    consumer.ack(OUTBOUND_STREAM, msg_id)
                    processed += 1
                # Don't ACK if will_retry - let PEL reclaim handle it

                logger.debug(
                    f"Processed outbound message",
                    extra={"msg_id": msg_id, "result": result},
                )

            except Exception as e:
                logger.error(
                    f"Failed to process outbound message {msg_id}: {e}",
                    exc_info=True,
                )

    finally:
        db.close()
        if hasattr(provider, "close"):
            await provider.close()

    return processed


async def process_vertical_events(redis_client, consumer: WhatsAppStreamConsumer) -> int:
    """Process events from verticais that should trigger WhatsApp messages."""
    # Use a separate consumer group for vertical events
    vertical_consumer = WhatsAppStreamConsumer(
        redis_client,
        CONSUMER_NAME,
        group_name=WHATSAPP_NOTIFIER_GROUP,
    )

    messages = vertical_consumer.read_messages(
        VERTICAL_EVENTS_STREAM,
        count=BATCH_SIZE,
        block_ms=100,
    )

    if not messages:
        return 0

    processed = 0
    db = next(get_db())
    provider = get_provider()

    try:
        handler = OutboundHandler(db, redis_client, provider)

        for msg_id, envelope in messages:
            try:
                # Only process events that should trigger notifications
                from messaging_whatsapp.contracts.event_types import VERTICAL_EVENTS_TO_NOTIFY

                if envelope.event_type in VERTICAL_EVENTS_TO_NOTIFY:
                    result = await handler.handle_vertical_event(envelope)

                    logger.debug(
                        f"Processed vertical event",
                        extra={
                            "msg_id": msg_id,
                            "event_type": envelope.event_type,
                            "result": result,
                        },
                    )
                else:
                    logger.debug(f"Ignoring event type: {envelope.event_type}")

                vertical_consumer.ack(VERTICAL_EVENTS_STREAM, msg_id)
                processed += 1

            except Exception as e:
                logger.error(
                    f"Failed to process vertical event {msg_id}: {e}",
                    exc_info=True,
                )
                # ACK anyway to not block queue (event processing is best-effort)
                vertical_consumer.ack(VERTICAL_EVENTS_STREAM, msg_id)

    finally:
        db.close()
        if hasattr(provider, "close"):
            await provider.close()

    return processed


def run_reclaim_loop(redis_client):
    """Background thread for reclaiming pending messages."""
    logger.info(
        f"Starting PEL reclaim loop "
        f"(interval={RECLAIM_INTERVAL_SEC}s, idle_threshold={RECLAIM_IDLE_MS}ms)"
    )

    consumer = WhatsAppStreamConsumer(redis_client, CONSUMER_NAME)

    while not shutdown_requested:
        try:
            # Sleep first
            for _ in range(RECLAIM_INTERVAL_SEC):
                if shutdown_requested:
                    return
                time.sleep(1)

            if shutdown_requested:
                return

            # Reclaim from inbound stream
            inbound_reclaimed = consumer.reclaim_pending(
                INBOUND_STREAM,
                min_idle_ms=RECLAIM_IDLE_MS,
                count=100,
            )
            if inbound_reclaimed:
                logger.info(f"Reclaimed {len(inbound_reclaimed)} inbound messages")

            # Reclaim from outbound stream
            outbound_reclaimed = consumer.reclaim_pending(
                OUTBOUND_STREAM,
                min_idle_ms=RECLAIM_IDLE_MS,
                count=100,
            )
            if outbound_reclaimed:
                logger.info(f"Reclaimed {len(outbound_reclaimed)} outbound messages")

        except Exception as e:
            logger.error(f"Error in reclaim loop: {e}", exc_info=True)


async def main_loop():
    """Main worker loop."""
    redis_client = get_redis_client()

    # Ensure streams exist
    ensure_whatsapp_streams(redis_client)

    consumer = WhatsAppStreamConsumer(redis_client, CONSUMER_NAME)

    logger.info(
        f"Starting WhatsApp worker "
        f"(consumer={CONSUMER_NAME}, batch={BATCH_SIZE}, provider={WHATSAPP_PROVIDER})"
    )

    # Start reclaim background thread
    reclaim_thread = threading.Thread(
        target=run_reclaim_loop,
        args=(redis_client,),
        daemon=True,
    )
    reclaim_thread.start()

    while not shutdown_requested:
        try:
            # Process inbound (sync - doesn't need async provider)
            inbound_count = process_inbound_messages(redis_client, consumer)
            if inbound_count > 0:
                logger.info(f"Processed {inbound_count} inbound messages")

            # Process outbound (async - needs provider)
            outbound_count = await process_outbound_messages(redis_client, consumer)
            if outbound_count > 0:
                logger.info(f"Processed {outbound_count} outbound messages")

            # Process vertical events
            vertical_count = await process_vertical_events(redis_client, consumer)
            if vertical_count > 0:
                logger.info(f"Processed {vertical_count} vertical events")

            # Small sleep if nothing processed
            if inbound_count == 0 and outbound_count == 0 and vertical_count == 0:
                await asyncio.sleep(0.1)

        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.error(f"Error in main loop: {e}", exc_info=True)
            await asyncio.sleep(1)

    logger.info("WhatsApp worker shutting down gracefully")


def main():
    """Entry point."""
    logger.info("WhatsApp worker starting...")
    asyncio.run(main_loop())


if __name__ == "__main__":
    main()




