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
from messaging_whatsapp.providers.evolution import EvolutionWhatsAppProvider
from messaging_whatsapp.providers.evolution.webhook import (
    extract_instance_name as extract_evolution_instance,
    validate_api_key as validate_evolution_api_key,
)
from messaging_whatsapp.providers.meta_cloud import MetaCloudWhatsAppProvider
from messaging_whatsapp.providers.meta_cloud.webhook import extract_phone_number_id, validate_signature
from messaging_whatsapp.providers.stub import StubWhatsAppProvider
from messaging_whatsapp.routing.tenant_resolver import TenantResolver, resolve_from_webhook_payload
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


def detect_provider(payload: dict[str, Any], request_headers: dict[str, str]) -> str:
    """
    Detect which provider sent the webhook.

    Args:
        payload: Parsed webhook payload
        request_headers: Request headers

    Returns:
        Provider name: "meta", "evolution", or "unknown"
    """
    # Meta Cloud API format
    if payload.get("object") == "whatsapp_business_account":
        return "meta"

    # Evolution API format
    if payload.get("event") or payload.get("instance"):
        return "evolution"

    return "unknown"


@app.post("/webhook")
async def receive_webhook(request: Request):
    """
    Receive webhook from WhatsApp providers (Meta Cloud API or Evolution API).

    Flow:
    1. Detect provider from payload
    2. Validate signature/api key
    3. Parse payload
    4. Resolve tenant (by phone_number_id or instance_name)
    5. Publish to Redis Stream
    6. Return 200 immediately
    """
    # Get raw body for signature validation
    body = await request.body()

    # Parse payload
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        logger.warning("Invalid JSON payload")
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # Detect provider
    provider_type = detect_provider(payload, dict(request.headers))

    if provider_type == "unknown":
        logger.debug(f"Unknown webhook format: {payload.keys()}")
        return {"status": "ignored", "reason": "unknown_provider"}

    # Validate based on provider
    if provider_type == "meta":
        # Validate Meta signature
        if WHATSAPP_APP_SECRET:
            signature = request.headers.get("X-Hub-Signature-256", "")
            if not validate_signature(body, signature, WHATSAPP_APP_SECRET):
                logger.warning("Invalid Meta webhook signature")
                raise HTTPException(status_code=403, detail="Invalid signature")

    elif provider_type == "evolution":
        # Validate Evolution API key (if configured globally)
        # Note: Evolution API can also validate per-instance, but we check here
        evolution_api_key = os.getenv("EVOLUTION_API_KEY")
        if evolution_api_key:
            if not validate_evolution_api_key(dict(request.headers), evolution_api_key):
                logger.warning("Invalid Evolution API key")
                raise HTTPException(status_code=403, detail="Invalid API key")

    # Resolve tenant
    db = next(get_db())
    try:
        tenant_id, binding = resolve_from_webhook_payload(db, payload)

        if not binding or not tenant_id:
            logger.warning("Could not resolve tenant from webhook")
            return {"status": "ignored", "reason": "no_binding"}

        # Get provider for this binding
        if binding.provider == "meta":
            provider = MetaCloudWhatsAppProvider()
        elif binding.provider == "evolution":
            # Get API key from binding
            api_key = binding.api_key or ""
            encryption_key = os.getenv("WHATSAPP_ENCRYPTION_KEY")
            if encryption_key and api_key:
                try:
                    from cryptography.fernet import Fernet
                    f = Fernet(encryption_key.encode())
                    api_key = f.decrypt(api_key.encode()).decode()
                except Exception as e:
                    logger.warning(f"Failed to decrypt Evolution API key: {e}")

            provider = EvolutionWhatsAppProvider(
                api_url=binding.api_url or "",
                api_key=api_key,
                instance_name=binding.instance_name or "",
            )
        else:
            provider = StubWhatsAppProvider()

        # Parse webhook to get messages and statuses
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
            "provider": provider_type,
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

