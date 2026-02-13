"""
Meta Webhook Utilities

Helper functions for processing Meta Cloud API webhooks.
"""

import hashlib
import hmac
import logging
from typing import Any

logger = logging.getLogger(__name__)


def validate_signature(
    payload: bytes,
    signature_header: str,
    app_secret: str,
) -> bool:
    """
    Validate Meta webhook signature.

    Args:
        payload: Raw request body bytes
        signature_header: X-Hub-Signature-256 header value
        app_secret: Facebook App Secret

    Returns:
        True if signature is valid
    """
    if not signature_header:
        logger.warning("Missing signature header")
        return False

    if not signature_header.startswith("sha256="):
        logger.warning("Invalid signature format")
        return False

    expected = signature_header[7:]

    computed = hmac.new(
        app_secret.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(computed, expected)


def parse_meta_webhook(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Parse and normalize a Meta webhook payload.

    Returns a normalized structure:
    {
        "waba_id": "...",
        "phone_number_id": "...",
        "display_number": "...",
        "messages": [...],
        "statuses": [...],
    }
    """
    result: dict[str, Any] = {
        "waba_id": None,
        "phone_number_id": None,
        "display_number": None,
        "messages": [],
        "statuses": [],
    }

    if payload.get("object") != "whatsapp_business_account":
        return result

    for entry in payload.get("entry", []):
        result["waba_id"] = entry.get("id")

        for change in entry.get("changes", []):
            if change.get("field") != "messages":
                continue

            value = change.get("value", {})
            metadata = value.get("metadata", {})

            result["phone_number_id"] = metadata.get("phone_number_id")
            result["display_number"] = metadata.get("display_phone_number")

            # Add messages with contact info
            contacts = value.get("contacts", [])
            for msg in value.get("messages", []):
                msg_with_contact = {**msg}
                if contacts:
                    msg_with_contact["_contact"] = contacts[0]
                result["messages"].append(msg_with_contact)

            # Add statuses
            result["statuses"].extend(value.get("statuses", []))

    return result


def extract_phone_number_id(payload: dict[str, Any]) -> str | None:
    """
    Extract phone_number_id from webhook payload.

    This is used for tenant resolution before full parsing.
    """
    try:
        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                metadata = value.get("metadata", {})
                phone_number_id = metadata.get("phone_number_id")
                if phone_number_id:
                    return phone_number_id
    except Exception:
        pass
    return None


def is_message_webhook(payload: dict[str, Any]) -> bool:
    """Check if this webhook contains messages (not just statuses)."""
    try:
        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                if value.get("messages"):
                    return True
    except Exception:
        pass
    return False


def is_status_webhook(payload: dict[str, Any]) -> bool:
    """Check if this webhook contains status updates."""
    try:
        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                if value.get("statuses"):
                    return True
    except Exception:
        pass
    return False




