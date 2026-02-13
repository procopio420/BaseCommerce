"""
Tests for webhook signature validation.
"""

import hashlib
import hmac

import pytest

from messaging_whatsapp.providers.meta_cloud import MetaCloudWhatsAppProvider
from messaging_whatsapp.providers.meta_cloud.webhook import validate_signature
from messaging_whatsapp.providers.stub import StubWhatsAppProvider


class TestSignatureValidation:
    """Tests for webhook signature validation."""

    def test_valid_signature_meta(self):
        """Test valid HMAC-SHA256 signature validation."""
        app_secret = "test_secret_key"
        payload = b'{"test": "data"}'

        # Generate valid signature
        signature = hmac.new(
            app_secret.encode("utf-8"),
            payload,
            hashlib.sha256,
        ).hexdigest()

        signature_header = f"sha256={signature}"

        assert validate_signature(payload, signature_header, app_secret) is True

    def test_invalid_signature_meta(self):
        """Test invalid signature is rejected."""
        app_secret = "test_secret_key"
        payload = b'{"test": "data"}'

        invalid_signature = "sha256=invalid_signature_here"

        assert validate_signature(payload, invalid_signature, app_secret) is False

    def test_missing_signature_prefix(self):
        """Test signature without sha256= prefix is rejected."""
        app_secret = "test_secret_key"
        payload = b'{"test": "data"}'

        # Valid hash but wrong format
        signature = hmac.new(
            app_secret.encode("utf-8"),
            payload,
            hashlib.sha256,
        ).hexdigest()

        assert validate_signature(payload, signature, app_secret) is False

    def test_empty_signature(self):
        """Test empty signature is rejected."""
        assert validate_signature(b"payload", "", "secret") is False
        assert validate_signature(b"payload", None, "secret") is False

    def test_meta_provider_validation(self):
        """Test MetaCloudWhatsAppProvider signature validation."""
        provider = MetaCloudWhatsAppProvider()
        app_secret = "my_app_secret"
        payload = b'{"object": "whatsapp_business_account"}'

        signature = hmac.new(
            app_secret.encode("utf-8"),
            payload,
            hashlib.sha256,
        ).hexdigest()

        assert provider.validate_webhook_signature(
            payload,
            f"sha256={signature}",
            app_secret,
        ) is True

        assert provider.validate_webhook_signature(
            payload,
            "sha256=wrong",
            app_secret,
        ) is False

    def test_stub_provider_accepts_any_signature(self):
        """Test StubWhatsAppProvider accepts any signature."""
        provider = StubWhatsAppProvider()

        assert provider.validate_webhook_signature(
            b"any payload",
            "any signature",
            "any secret",
        ) is True

        assert provider.validate_webhook_signature(
            b"payload",
            "",
            "",
        ) is True




