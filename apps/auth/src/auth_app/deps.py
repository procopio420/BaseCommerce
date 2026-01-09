from typing import Optional

from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from basecore.db import get_db
from basecore.security import decode_access_token
from auth_app.models import Tenant, TenantBranding, User

# Re-export get_db from basecore
get_db = get_db

security = HTTPBearer(auto_error=False)


def get_tenant_slug_from_header(
    x_tenant_slug: Optional[str] = Header(None, alias="X-Tenant-Slug"),
) -> Optional[str]:
    """Extract tenant slug from X-Tenant-Slug header (set by Nginx)."""
    return x_tenant_slug


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


async def get_tenant_from_header(
    tenant_slug: Optional[str] = Depends(get_tenant_slug_from_header),
    db: Session = Depends(get_db),
) -> Optional[Tenant]:
    """Get tenant from X-Tenant-Slug header."""
    if not tenant_slug:
        return None
    return get_tenant_by_slug(db, tenant_slug)


async def require_tenant(
    tenant: Optional[Tenant] = Depends(get_tenant_from_header),
) -> Tenant:
    """Require tenant to be present (raises 400 if not)."""
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant not specified or not found",
        )
    return tenant


def get_token_from_request(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[str]:
    """Extract token from Bearer header or cookie."""
    # Try Bearer header first
    if credentials and credentials.credentials:
        return credentials.credentials
    # Fall back to cookie
    return request.cookies.get("access_token")


async def get_current_user(
    token: Optional[str] = Depends(get_token_from_request),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """Get current user from token (Bearer or cookie)."""
    if not token:
        return None

    payload = decode_access_token(token)
    if payload is None:
        return None

    user_id: Optional[str] = payload.get("sub")
    tenant_id: Optional[str] = payload.get("tenant_id")

    if not user_id or not tenant_id:
        return None

    user = (
        db.query(User)
        .filter(
            User.id == user_id,
            User.tenant_id == tenant_id,
            User.ativo == True,  # noqa: E712
        )
        .first()
    )

    return user


async def require_current_user(
    user: Optional[User] = Depends(get_current_user),
) -> User:
    """Require authenticated user (raises 401 if not)."""
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


