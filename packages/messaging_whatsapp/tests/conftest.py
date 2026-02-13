"""
Pytest fixtures for WhatsApp tests.
"""

import pytest


@pytest.fixture
def sample_tenant_id():
    """Sample tenant UUID."""
    from uuid import UUID
    return UUID("12345678-1234-1234-1234-123456789012")


@pytest.fixture
def sample_phone():
    """Sample phone number."""
    return "+5511999999999"




