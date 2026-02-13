"""
Evolution API Webhook Utilities

Helper functions for processing Evolution API webhooks.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def parse_evolution_webhook(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Parse and normalize an Evolution API webhook payload.

    Returns a normalized structure:
    {
        "instance": "...",
        "event": "messages.upsert",
        "messages": [...],
        "statuses": [...],
    }
    """
    result: dict[str, Any] = {
        "instance": None,
        "event": None,
        "messages": [],
        "statuses": [],
    }

    instance = payload.get("instance")
    event = payload.get("event")

    if not instance or not event:
        return result

    result["instance"] = instance
    result["event"] = event

    if event == "messages.upsert":
        # Incoming message
        data = payload.get("data", {})
        if data:
            result["messages"].append(data)

    elif event == "messages.update":
        # Status update
        data = payload.get("data", {})
        if data:
            result["statuses"].append(data)

    return result


def extract_instance_name(payload: dict[str, Any]) -> str | None:
    """
    Extract instance name from webhook payload.

    This is used for tenant resolution before full parsing.
    """
    return payload.get("instance")


def is_message_webhook(payload: dict[str, Any]) -> bool:
    """Check if this webhook contains messages."""
    return payload.get("event") == "messages.upsert"


def is_status_webhook(payload: dict[str, Any]) -> bool:
    """Check if this webhook contains status updates."""
    return payload.get("event") == "messages.update"


def validate_api_key(request_headers: dict[str, str], expected_api_key: str) -> bool:
    """
    Validate API key from request headers.

    Evolution API can send API key in:
    - Header: "apikey"
    - Header: "Authorization: Bearer <key>"
    """
    apikey_header = request_headers.get("apikey") or request_headers.get("Apikey")
    if apikey_header == expected_api_key:
        return True

    auth_header = request_headers.get("authorization") or request_headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        if token == expected_api_key:
            return True

    return False




