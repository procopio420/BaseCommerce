"""Tenant resolution middleware for subdomain-based multi-tenancy."""

import json
import re
from typing import Optional

from fastapi import Request
from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.core.database import SessionLocal
from app.models.tenant import Tenant
from app.models.tenant_branding import TenantBranding

# Simple in-memory cache for tenant lookups (in production, use Redis)
_tenant_cache: dict[str, dict] = {}
_CACHE_TTL_SECONDS = 300  # 5 minutes


def extract_slug_from_host(host: str) -> Optional[str]:
    """
    Extract tenant slug from Host header.
    
    Examples:
    - "acme.basecommerce.com.br" -> "acme"
    - "acme.basecommerce.com.br:8000" -> "acme"
    - "localhost:8000" -> None (development mode)
    - "basecommerce.com.br" -> None (root domain)
    """
    # Remove port if present
    host = host.split(":")[0].lower()
    
    # Development mode: localhost or IP addresses
    if host in ("localhost", "127.0.0.1") or re.match(r"^\d+\.\d+\.\d+\.\d+$", host):
        return None
    
    # Check for subdomain pattern: slug.basecommerce.com.br
    # Also support slug.localhost for local development with /etc/hosts
    parts = host.split(".")
    
    # Pattern: slug.domain.tld (at least 3 parts for production)
    # Or: slug.localhost (2 parts for local dev)
    if len(parts) >= 3:
        # e.g., acme.basecommerce.com.br -> acme
        return parts[0]
    elif len(parts) == 2 and parts[1] == "localhost":
        # e.g., acme.localhost -> acme
        return parts[0]
    
    return None


def get_tenant_by_slug(db: Session, slug: str) -> Optional[Tenant]:
    """Fetch tenant by slug from database."""
    return (
        db.query(Tenant)
        .filter(Tenant.slug == slug, Tenant.ativo == True)  # noqa: E712
        .first()
    )


def get_tenant_branding(db: Session, tenant_id) -> Optional[TenantBranding]:
    """Fetch tenant branding from database."""
    return (
        db.query(TenantBranding)
        .filter(TenantBranding.tenant_id == tenant_id)
        .first()
    )


class TenantResolutionMiddleware(BaseHTTPMiddleware):
    """
    Middleware that resolves tenant from Host header.
    
    Sets request.state attributes:
    - tenant_id: UUID of the resolved tenant
    - tenant_slug: slug extracted from Host
    - tenant: Tenant model instance
    - tenant_branding: TenantBranding model instance (or defaults)
    """

    # Paths that don't require tenant resolution
    EXCLUDED_PATHS = (
        "/health",
        "/docs",
        "/openapi.json",
        "/redoc",
        "/api/v1/auth/",  # API auth uses token-based tenant
    )

    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip tenant resolution for excluded paths
        path = request.url.path
        if any(path.startswith(excluded) for excluded in self.EXCLUDED_PATHS):
            return await call_next(request)
        
        # Skip for API routes (they use token-based tenant resolution)
        if path.startswith("/api/"):
            return await call_next(request)
        
        host = request.headers.get("host", "")
        slug = extract_slug_from_host(host)
        
        # Initialize tenant state with defaults
        request.state.tenant_id = None
        request.state.tenant_slug = slug
        request.state.tenant = None
        request.state.tenant_branding = None
        
        if slug:
            db: Session = SessionLocal()
            try:
                tenant = get_tenant_by_slug(db, slug)
                if tenant:
                    branding = get_tenant_branding(db, tenant.id)
                    
                    request.state.tenant_id = tenant.id
                    request.state.tenant = tenant
                    request.state.tenant_branding = branding
            finally:
                db.close()
        
        response = await call_next(request)
        return response


class DefaultBranding:
    """Default branding when no tenant-specific branding exists."""
    
    logo_url: Optional[str] = None
    primary_color: str = "#1a73e8"
    secondary_color: str = "#ea4335"
    feature_flags: dict = {}

    def __init__(self):
        self.feature_flags = {}



