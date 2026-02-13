"""
Tenant Resolver

Resolves tenant from incoming WhatsApp messages using phone_number_id mapping.
"""

import logging
from functools import lru_cache
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from messaging_whatsapp.persistence.models import WhatsAppTenantBinding
from messaging_whatsapp.persistence.repo import WhatsAppRepository

logger = logging.getLogger(__name__)


class TenantResolver:
    """
    Resolves tenant from WhatsApp webhook data.

    Uses phone_number_id to look up the tenant binding.
    """

    def __init__(self, db: Session):
        self.db = db
        self.repo = WhatsAppRepository(db)

    def resolve_from_phone_number_id(
        self,
        phone_number_id: str,
    ) -> WhatsAppTenantBinding | None:
        """
        Resolve tenant binding from WhatsApp phone number ID (Meta Cloud API).

        Args:
            phone_number_id: WhatsApp Business phone number ID from webhook

        Returns:
            Tenant binding if found and active, None otherwise
        """
        binding = self.repo.get_binding_by_phone_number_id(phone_number_id)

        if binding:
            logger.debug(
                f"Resolved tenant from phone_number_id",
                extra={
                    "phone_number_id": phone_number_id,
                    "tenant_id": str(binding.tenant_id),
                },
            )
        else:
            logger.warning(
                f"No tenant binding found for phone_number_id: {phone_number_id}"
            )

        return binding

    def resolve_from_instance_name(
        self,
        instance_name: str,
    ) -> WhatsAppTenantBinding | None:
        """
        Resolve tenant binding from Evolution API instance name.

        Args:
            instance_name: Evolution API instance name from webhook

        Returns:
            Tenant binding if found and active, None otherwise
        """
        binding = self.repo.get_binding_by_instance_name(instance_name)

        if binding:
            logger.debug(
                f"Resolved tenant from instance_name",
                extra={
                    "instance_name": instance_name,
                    "tenant_id": str(binding.tenant_id),
                },
            )
        else:
            logger.warning(
                f"No tenant binding found for instance_name: {instance_name}"
            )

        return binding

    def resolve_tenant_id(self, phone_number_id: str) -> UUID | None:
        """
        Resolve just the tenant ID from phone number ID.

        Args:
            phone_number_id: WhatsApp Business phone number ID

        Returns:
            Tenant UUID if found, None otherwise
        """
        binding = self.resolve_from_phone_number_id(phone_number_id)
        return binding.tenant_id if binding else None

    def get_binding_for_tenant(self, tenant_id: UUID) -> WhatsAppTenantBinding | None:
        """
        Get the active WhatsApp binding for a tenant.

        Used when sending outbound messages.

        Args:
            tenant_id: Tenant UUID

        Returns:
            Active binding for the tenant, None if none exists
        """
        return self.repo.get_active_binding_for_tenant(tenant_id)

    def get_access_token(
        self,
        binding: WhatsAppTenantBinding,
        encryption_key: str | None = None,
    ) -> str | None:
        """
        Get decrypted access token from binding.

        Args:
            binding: Tenant binding
            encryption_key: Fernet key for decryption (if encrypted)

        Returns:
            Decrypted access token, None if not available
        """
        if not binding.access_token_encrypted:
            return None

        # If not actually encrypted (e.g., stub mode), return as-is
        if not encryption_key:
            return binding.access_token_encrypted

        try:
            from cryptography.fernet import Fernet

            f = Fernet(encryption_key.encode())
            return f.decrypt(binding.access_token_encrypted.encode()).decode()
        except Exception as e:
            logger.error(f"Failed to decrypt access token: {e}")
            return None


def resolve_from_webhook_payload(
    db: Session,
    payload: dict[str, Any],
) -> tuple[UUID | None, WhatsAppTenantBinding | None]:
    """
    Convenience function to resolve tenant from webhook payload.

    Supports both Meta Cloud API and Evolution API webhook formats.

    Args:
        db: Database session
        payload: Webhook payload (Meta or Evolution format)

    Returns:
        Tuple of (tenant_id, binding) or (None, None) if not resolved
    """
    resolver = TenantResolver(db)

    # Detect provider by payload structure
    # Meta Cloud API: {"object": "whatsapp_business_account", "entry": [...]}
    # Evolution API: {"event": "...", "instance": "...", "data": {...}}

    if payload.get("object") == "whatsapp_business_account":
        # Meta Cloud API format
        phone_number_id = None
        try:
            for entry in payload.get("entry", []):
                for change in entry.get("changes", []):
                    value = change.get("value", {})
                    metadata = value.get("metadata", {})
                    phone_number_id = metadata.get("phone_number_id")
                    if phone_number_id:
                        break
                if phone_number_id:
                    break
        except Exception:
            pass

        if phone_number_id:
            binding = resolver.resolve_from_phone_number_id(phone_number_id)
            if binding:
                return binding.tenant_id, binding

    elif payload.get("instance") or payload.get("event"):
        # Evolution API format
        instance_name = payload.get("instance")
        if instance_name:
            binding = resolver.resolve_from_instance_name(instance_name)
            if binding:
                return binding.tenant_id, binding

    logger.warning("Could not resolve tenant from webhook payload")
    return None, None

