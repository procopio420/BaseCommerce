"""Web-specific dependencies for cookie-based authentication."""

from dataclasses import dataclass
from typing import Optional, Dict, Any
from uuid import UUID

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from construction_app.core.security import decode_access_token
from construction_app.core.database import get_db
from construction_app.models.tenant import Tenant
from construction_app.models.tenant_branding import TenantBranding


@dataclass
class UserClaims:
    """User information extracted from JWT token.
    
    This replaces the User model for authentication purposes.
    User data is stored in auth service, vertical only needs claims.
    """
    id: UUID
    tenant_id: UUID
    email: str
    role: str


class WebAuthException(HTTPException):
    """Exception that triggers redirect to login page."""
    
    def __init__(self, redirect_url: str = "/auth/login"):
        super().__init__(status_code=302, headers={"Location": redirect_url})


async def get_optional_web_user(request: Request) -> Optional[UserClaims]:
    """
    Get current user from cookie if present and valid.
    Returns None if not authenticated (doesn't raise exception).
    
    Extracts user info from JWT claims without querying database.
    """
    token = request.cookies.get("access_token")
    if not token:
        return None
    
    payload = decode_access_token(token)
    if payload is None:
        return None
    
    user_id: Optional[str] = payload.get("sub")
    token_tenant_id: Optional[str] = payload.get("tenant_id")
    email: Optional[str] = payload.get("email")
    role: Optional[str] = payload.get("role", "vendedor")
    
    if not user_id or not token_tenant_id or not email:
        return None
    
    # Validate tenant matches request if tenant resolution is active
    request_tenant_slug = getattr(request.state, "tenant_slug", None)
    request_tenant_id = getattr(request.state, "tenant_id", None)
    
    # If we have a tenant_id from request state, validate it matches the token
    if request_tenant_id and str(request_tenant_id) != token_tenant_id:
        # Token is for a different tenant than the subdomain
        return None
    
    return UserClaims(
        id=UUID(user_id),
        tenant_id=UUID(token_tenant_id),
        email=email,
        role=role,
    )


async def require_web_user(request: Request) -> UserClaims:
    """
    Require authenticated user from cookie.
    Redirects to login page if not authenticated.
    """
    user = await get_optional_web_user(request)
    
    if user is None:
        # For HTMX requests, return HX-Redirect header
        if request.headers.get("HX-Request"):
            raise HTTPException(
                status_code=200,
                headers={"HX-Redirect": "/auth/login"},
            )
        raise WebAuthException("/auth/login")
    
    return user


def get_tenant_id_from_request(request: Request) -> Optional[UUID]:
    """Get tenant_id from request state (set by middleware)."""
    return getattr(request.state, "tenant_id", None)


def get_tenant_slug_from_request(request: Request) -> Optional[str]:
    """Get tenant_slug from request state (set by middleware)."""
    return getattr(request.state, "tenant_slug", None)


def require_tenant(request: Request) -> UUID:
    """Require tenant to be resolved from subdomain."""
    tenant_id = get_tenant_id_from_request(request)
    if not tenant_id:
        raise HTTPException(
            status_code=400,
            detail="Tenant não identificado. Use um subdomínio válido.",
        )
    return tenant_id


def get_current_tenant_context(
    user: Optional[UserClaims] = None,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Get current tenant context (name, slug, branding) from database.
    
    Uses user.tenant_id to fetch Tenant and TenantBranding.
    Returns defaults if tenant or branding not found.
    """
    # Default values
    defaults = {
        "name": "BaseCommerce",
        "slug": "",
        "logo_url": None,
        "primary_color": "#1a73e8",
        "secondary_color": "#ea4335",
        "feature_flags": {},
    }
    
    if not user:
        return defaults
    
    # Fetch tenant
    tenant = db.query(Tenant).filter(
        Tenant.id == user.tenant_id,
        Tenant.ativo == True,  # noqa: E712
    ).first()
    
    if not tenant:
        return defaults
    
    # Fetch branding
    branding = db.query(TenantBranding).filter(
        TenantBranding.tenant_id == user.tenant_id
    ).first()
    
    return {
        "name": tenant.nome,
        "slug": tenant.slug,
        "logo_url": branding.logo_url if branding else None,
        "primary_color": branding.primary_color if branding else "#1a73e8",
        "secondary_color": branding.secondary_color if branding else "#ea4335",
        "feature_flags": branding.feature_flags if branding and branding.feature_flags else {},
    }
