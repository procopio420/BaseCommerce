"""
Engines Worker - Redis Streams Consumer

This worker uses ONLY:
- basecore (DB, settings, logging, redis)
- engines_core (handlers, persistence, consumer)

NO imports from backend/ are allowed.

Features:
- XREADGROUP consumer for horizontal scaling
- PEL reclaim for stuck messages
- Strong idempotency via engine_processed_events table
- Graceful shutdown
"""

import logging
import os
import signal
import socket
import sys
import time
import threading
from uuid import UUID

# Only basecore + engines_core imports
from basecore.db import get_db
from basecore.logging import setup_logging
from basecore.redis import ensure_stream_group
from engines_core.consumer import (
    consume_from_stream,
    reclaim_pending_messages,
    DEFAULT_STREAM_NAME,
    DEFAULT_GROUP_NAME,
)

setup_logging()
logger = logging.getLogger(__name__)

# Configuration
STREAM_NAME = os.getenv("ENGINES_STREAM_NAME", DEFAULT_STREAM_NAME)
GROUP_NAME = os.getenv("ENGINES_GROUP_NAME", DEFAULT_GROUP_NAME)
CONSUMER_NAME = os.getenv("ENGINES_CONSUMER_NAME", f"engines-{socket.gethostname()}-{os.getpid()}")
BATCH_SIZE = int(os.getenv("ENGINES_BATCH_SIZE", "10"))
BLOCK_MS = int(os.getenv("ENGINES_BLOCK_MS", "5000"))
RECLAIM_INTERVAL_SEC = int(os.getenv("ENGINES_RECLAIM_INTERVAL", "60"))
RECLAIM_IDLE_MS = int(os.getenv("ENGINES_RECLAIM_IDLE_MS", "60000"))

# Graceful shutdown
shutdown_requested = False


def signal_handler(signum, frame):
    global shutdown_requested
    logger.info(f"Received signal {signum}, requesting shutdown...")
    shutdown_requested = True


signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)


def ensure_consumer_group():
    """Ensure the consumer group exists for the stream."""
    try:
        created = ensure_stream_group(STREAM_NAME, GROUP_NAME, start_id="0")
        if created:
            logger.info(f"Created consumer group '{GROUP_NAME}' for stream '{STREAM_NAME}'")
        else:
            logger.debug(f"Consumer group '{GROUP_NAME}' already exists for stream '{STREAM_NAME}'")
        return True
    except Exception as e:
        logger.error(f"Failed to ensure consumer group: {e}", exc_info=True)
        return False


def run_reclaim_loop():
    """
    Background thread for reclaiming pending messages.

    Runs every RECLAIM_INTERVAL_SEC seconds.
    """
    logger.info(f"Starting PEL reclaim loop (interval={RECLAIM_INTERVAL_SEC}s, idle_threshold={RECLAIM_IDLE_MS}ms)")

    while not shutdown_requested:
        try:
            # Sleep first to allow main loop to start
            for _ in range(RECLAIM_INTERVAL_SEC):
                if shutdown_requested:
                    return
                time.sleep(1)

            if shutdown_requested:
                return

            db = next(get_db())
            try:
                reclaimed = reclaim_pending_messages(
                    db,
                    stream_name=STREAM_NAME,
                    group_name=GROUP_NAME,
                    consumer_name=CONSUMER_NAME,
                    min_idle_ms=RECLAIM_IDLE_MS,
                    count=100,
                )
                if reclaimed > 0:
                    logger.info(f"Reclaimed and processed {reclaimed} pending messages")
            finally:
                db.close()

        except Exception as e:
            logger.error(f"Error in reclaim loop: {e}", exc_info=True)


def main():
    """Main worker loop."""
    logger.info(
        f"Starting engines worker (stream={STREAM_NAME}, group={GROUP_NAME}, "
        f"consumer={CONSUMER_NAME}, batch={BATCH_SIZE})"
    )
    logger.info("Using Redis Streams with XREADGROUP - fully independent from verticals")

    # Ensure consumer group exists
    if not ensure_consumer_group():
        logger.error("Failed to initialize consumer group, exiting")
        sys.exit(1)

    # Initial reclaim on startup to pick up orphaned messages
    logger.info("Running initial PEL reclaim on startup...")
    db = next(get_db())
    try:
        initial_reclaimed = reclaim_pending_messages(
            db,
            stream_name=STREAM_NAME,
            group_name=GROUP_NAME,
            consumer_name=CONSUMER_NAME,
            min_idle_ms=RECLAIM_IDLE_MS,
            count=100,
        )
        if initial_reclaimed > 0:
            logger.info(f"Initial reclaim: processed {initial_reclaimed} orphaned messages")
    except Exception as e:
        logger.warning(f"Initial reclaim failed: {e}")
    finally:
        db.close()

    # Start reclaim background thread
    reclaim_thread = threading.Thread(target=run_reclaim_loop, daemon=True)
    reclaim_thread.start()

    # Main consume loop
    consecutive_empty = 0

    while not shutdown_requested:
        db = next(get_db())
        try:
            count = consume_from_stream(
                db,
                stream_name=STREAM_NAME,
                group_name=GROUP_NAME,
                consumer_name=CONSUMER_NAME,
                count=BATCH_SIZE,
                block_ms=BLOCK_MS,
            )

            if count > 0:
                logger.info(f"Processed {count} events from stream")
                consecutive_empty = 0
            else:
                consecutive_empty += 1

        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.error(f"Error in consume loop: {e}", exc_info=True)
            time.sleep(1)  # Brief pause on error
        finally:
            db.close()

    logger.info("Engines worker shutting down gracefully")


if __name__ == "__main__":
    main()
