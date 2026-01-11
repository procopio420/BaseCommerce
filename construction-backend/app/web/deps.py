"""Web-specific dependencies for cookie-based authentication."""

from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session
from starlette.responses import RedirectResponse

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import User


class WebAuthException(HTTPException):
    """Exception that triggers redirect to login page."""
    
    def __init__(self, redirect_url: str = "/web/login"):
        super().__init__(status_code=302, headers={"Location": redirect_url})


async def get_optional_web_user(
    request: Request,
    db: Session = Depends(get_db),
) -> Optional[User]:
    """
    Get current user from cookie if present and valid.
    Returns None if not authenticated (doesn't raise exception).
    """
    token = request.cookies.get("access_token")
    if not token:
        return None
    
    payload = decode_access_token(token)
    if payload is None:
        return None
    
    user_id: Optional[str] = payload.get("sub")
    token_tenant_id: Optional[str] = payload.get("tenant_id")
    
    if not user_id or not token_tenant_id:
        return None
    
    # Validate tenant matches request if tenant resolution is active
    request_tenant_id = getattr(request.state, "tenant_id", None)
    if request_tenant_id and str(request_tenant_id) != token_tenant_id:
        # Token is for a different tenant than the subdomain
        return None
    
    user = (
        db.query(User)
        .filter(
            User.id == user_id,
            User.tenant_id == token_tenant_id,
            User.ativo == True,  # noqa: E712
        )
        .first()
    )
    
    return user


async def require_web_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    """
    Require authenticated user from cookie.
    Redirects to login page if not authenticated.
    """
    user = await get_optional_web_user(request, db)
    
    if user is None:
        # For HTMX requests, return HX-Redirect header
        if request.headers.get("HX-Request"):
            raise HTTPException(
                status_code=200,
                headers={"HX-Redirect": "/web/login"},
            )
        raise WebAuthException("/web/login")
    
    return user


def get_tenant_id_from_request(request: Request) -> Optional[UUID]:
    """Get tenant_id from request state (set by middleware)."""
    return getattr(request.state, "tenant_id", None)


def require_tenant(request: Request) -> UUID:
    """Require tenant to be resolved from subdomain."""
    tenant_id = get_tenant_id_from_request(request)
    if not tenant_id:
        raise HTTPException(
            status_code=400,
            detail="Tenant não identificado. Use um subdomínio válido.",
        )
    return tenant_id




