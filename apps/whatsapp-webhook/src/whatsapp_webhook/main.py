"""
WhatsApp Webhook Service

FastAPI app that receives WhatsApp webhooks from Meta Cloud API.

Responsibilities:
- Verify webhook signature
- Parse webhook payload
- Resolve tenant from phone_number_id
- Publish to Redis Stream for async processing
- Return 200 quickly (webhook timeout is 20s)
"""

import json
import logging
import os
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request, Response

from basecore.db import get_db
from basecore.logging import setup_logging
from basecore.redis import get_redis_client

from messaging_whatsapp.providers.base import WhatsAppProvider
from messaging_whatsapp.providers.meta_cloud import MetaCloudWhatsAppProvider
from messaging_whatsapp.providers.meta_cloud.webhook import extract_phone_number_id, validate_signature
from messaging_whatsapp.providers.stub import StubWhatsAppProvider
from messaging_whatsapp.routing.tenant_resolver import TenantResolver
from messaging_whatsapp.streams.groups import ensure_whatsapp_streams
from messaging_whatsapp.streams.producer import WhatsAppStreamProducer

setup_logging()
logger = logging.getLogger(__name__)

# Configuration
WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "basecommerce_verify_token")
WHATSAPP_APP_SECRET = os.getenv("WHATSAPP_APP_SECRET", "")
WHATSAPP_PROVIDER = os.getenv("WHATSAPP_PROVIDER", "stub")

app = FastAPI(
    title="WhatsApp Webhook",
    description="Receives WhatsApp webhooks and publishes to Redis Streams",
    version="1.0.0",
)


def get_provider() -> WhatsAppProvider:
    """Get the appropriate provider."""
    if WHATSAPP_PROVIDER == "meta":
        return MetaCloudWhatsAppProvider()
    return StubWhatsAppProvider()


@app.on_event("startup")
async def startup():
    """Ensure Redis streams exist on startup."""
    try:
        redis_client = get_redis_client()
        ensure_whatsapp_streams(redis_client)
        logger.info("WhatsApp webhook service started")
    except Exception as e:
        logger.error(f"Failed to initialize streams: {e}")
        raise


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "service": "whatsapp-webhook"}


@app.get("/webhook")
async def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
):
    """
    Handle Meta webhook verification.

    Meta sends a GET request with hub.mode, hub.verify_token, and hub.challenge.
    We must return hub.challenge if the token matches.
    """
    logger.info(
        f"Webhook verification request",
        extra={
            "mode": hub_mode,
            "token_received": bool(hub_verify_token),
        },
    )

    provider = get_provider()
    challenge = provider.verify_webhook_challenge(
        mode=hub_mode or "",
        token=hub_verify_token or "",
        challenge=hub_challenge or "",
        verify_token=WHATSAPP_VERIFY_TOKEN,
    )

    if challenge:
        logger.info("Webhook verification successful")
        return Response(content=challenge, media_type="text/plain")

    logger.warning("Webhook verification failed")
    raise HTTPException(status_code=403, detail="Verification failed")


@app.post("/webhook")
async def receive_webhook(request: Request):
    """
    Receive webhook from Meta Cloud API.

    Flow:
    1. Validate signature (if app secret configured)
    2. Parse payload
    3. Extract phone_number_id for tenant resolution
    4. Resolve tenant
    5. Publish to Redis Stream
    6. Return 200 immediately
    """
    # Get raw body for signature validation
    body = await request.body()

    # Validate signature if app secret is configured
    if WHATSAPP_APP_SECRET and WHATSAPP_PROVIDER == "meta":
        signature = request.headers.get("X-Hub-Signature-256", "")
        if not validate_signature(body, signature, WHATSAPP_APP_SECRET):
            logger.warning("Invalid webhook signature")
            raise HTTPException(status_code=403, detail="Invalid signature")

    # Parse payload
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        logger.warning("Invalid JSON payload")
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # Quick validation - only process WhatsApp webhooks
    if payload.get("object") != "whatsapp_business_account":
        logger.debug(f"Ignoring non-WhatsApp webhook: {payload.get('object')}")
        return {"status": "ignored", "reason": "not_whatsapp"}

    # Extract phone_number_id for tenant resolution
    phone_number_id = extract_phone_number_id(payload)
    if not phone_number_id:
        logger.warning("No phone_number_id in webhook payload")
        return {"status": "ignored", "reason": "no_phone_number_id"}

    # Resolve tenant
    db = next(get_db())
    try:
        resolver = TenantResolver(db)
        binding = resolver.resolve_from_phone_number_id(phone_number_id)

        if not binding:
            logger.warning(f"No tenant binding for phone_number_id: {phone_number_id}")
            return {"status": "ignored", "reason": "no_binding"}

        tenant_id = binding.tenant_id

        # Parse webhook to get messages and statuses
        provider = get_provider()
        messages, statuses = provider.parse_webhook(payload)

        # Publish to Redis Stream
        redis_client = get_redis_client()
        producer = WhatsAppStreamProducer(redis_client)

        published_count = 0

        # Publish inbound messages
        for message in messages:
            message_payload = _message_to_payload(message)
            producer.publish_inbound(
                tenant_id=tenant_id,
                payload=message_payload,
                correlation_id=message.message_id,
            )
            published_count += 1

            logger.info(
                f"Published inbound message",
                extra={
                    "message_id": message.message_id,
                    "from": message.from_phone,
                    "type": message.message_type.value,
                },
            )

        # Publish status updates (as inbound events for status handling)
        for status in statuses:
            status_payload = _status_to_payload(status)
            producer.publish_inbound(
                tenant_id=tenant_id,
                payload={
                    "is_status_update": True,
                    **status_payload,
                },
                correlation_id=status.message_id,
            )

            logger.debug(
                f"Published status update",
                extra={
                    "message_id": status.message_id,
                    "status": status.status,
                },
            )

        return {
            "status": "accepted",
            "messages": len(messages),
            "statuses": len(statuses),
        }

    except Exception as e:
        logger.error(f"Error processing webhook: {e}", exc_info=True)
        # Still return 200 to prevent Meta from retrying
        return {"status": "error", "message": str(e)}

    finally:
        db.close()


def _message_to_payload(message) -> dict[str, Any]:
    """Convert InboundMessage to dict payload."""
    return {
        "message_id": message.message_id,
        "from_phone": message.from_phone,
        "to_phone": message.to_phone,
        "phone_number_id": message.phone_number_id,
        "waba_id": message.waba_id,
        "message_type": message.message_type.value,
        "timestamp": message.timestamp.isoformat(),
        "text": message.text,
        "caption": message.caption,
        "media_id": message.media_id,
        "media_mime_type": message.media_mime_type,
        "media_url": message.media_url,
        "context_message_id": message.context_message_id,
        "customer_name": message.contact_name,
        "button_payload": message.button_payload,
        "button_text": message.button_text,
        "raw_payload": message.raw_payload,
    }


def _status_to_payload(status) -> dict[str, Any]:
    """Convert DeliveryStatus to dict payload."""
    return {
        "provider_message_id": status.message_id,
        "recipient_phone": status.recipient_phone,
        "status": status.status,
        "timestamp": status.timestamp.isoformat(),
        "error_code": status.error_code,
        "error_message": status.error_message,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8090)

