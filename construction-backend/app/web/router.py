"""Web router for server-rendered HTMX pages."""

from datetime import timedelta
from pathlib import Path
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.application.services.cotacao_service import CotacaoService
from app.application.services.pedido_service import PedidoService
from app.core.database import get_db
from app.core.security import create_access_token, verify_password
from app.domain.cotacao.exceptions import (
    CotacaoNaoPodeSerAprovadaException,
    CotacaoNaoPodeSerEditadaException,
    CotacaoNaoPodeSerEnviadaException,
)
from app.domain.pedido.exceptions import (
    CotacaoNaoAprovadaException,
    CotacaoSemItensException,
    PedidoNaoPodeSerCanceladoException,
)
from app.models.cotacao import Cotacao
from app.models.pedido import Pedido
from app.models.tenant import Tenant
from app.models.user import User
from app.web.deps import get_optional_web_user, require_tenant, require_web_user
from app.web.middleware import DefaultBranding
from basecore.settings import get_settings

# Setup templates
TEMPLATES_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

web_router = APIRouter()


def get_template_context(
    request: Request,
    user: Optional[User] = None,
    **extra_context,
) -> dict:
    """Build common template context with tenant branding."""
    tenant = getattr(request.state, "tenant", None)
    branding = getattr(request.state, "tenant_branding", None) or DefaultBranding()
    
    return {
        "request": request,
        "user": user,
        "tenant_name": tenant.nome if tenant else "BaseCommerce",
        "tenant_slug": getattr(request.state, "tenant_slug", None),
        "branding": branding,
        **extra_context,
    }


# =============================================================================
# Authentication Routes
# =============================================================================

@web_router.get("/login", response_class=HTMLResponse)
async def login_page(
    request: Request,
    user: Optional[User] = Depends(get_optional_web_user),
):
    """Render login page."""
    # If already logged in, redirect to dashboard
    if user:
        return RedirectResponse(url="/web/dashboard", status_code=302)
    
    context = get_template_context(request)
    return templates.TemplateResponse("pages/login.html", context)


@web_router.post("/login")
async def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    """Handle login form submission."""
    settings = get_settings()
    
    # Get tenant from request state (subdomain resolution)
    tenant_id = getattr(request.state, "tenant_id", None)
    
    # Build user query
    query = db.query(User).filter(User.email == email, User.ativo == True)  # noqa: E712
    
    if tenant_id:
        query = query.filter(User.tenant_id == tenant_id)
    
    user = query.first()
    
    if not user or not verify_password(password, user.password_hash):
        context = get_template_context(request, error="Email ou senha incorretos")
        return templates.TemplateResponse(
            "pages/login.html",
            context,
            status_code=401,
        )
    
    # Create access token
    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "tenant_id": str(user.tenant_id),
            "email": user.email,
        },
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    
    # Set cookie and redirect
    response = RedirectResponse(url="/web/dashboard", status_code=302)
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=False,  # Set to True in production with HTTPS
        samesite="lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    
    return response


@web_router.get("/logout")
async def logout(request: Request):
    """Clear auth cookie and redirect to login."""
    response = RedirectResponse(url="/web/login", status_code=302)
    response.delete_cookie(key="access_token")
    return response


# =============================================================================
# Dashboard
# =============================================================================

@web_router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(
    request: Request,
    user: User = Depends(require_web_user),
    db: Session = Depends(get_db),
):
    """Render dashboard page with summary stats."""
    tenant_id = user.tenant_id
    
    # Get counts
    cotacoes_count = db.query(Cotacao).filter(Cotacao.tenant_id == tenant_id).count()
    pedidos_count = db.query(Pedido).filter(Pedido.tenant_id == tenant_id).count()
    
    # Recent cotações
    cotacoes_recentes = (
        db.query(Cotacao)
        .filter(Cotacao.tenant_id == tenant_id)
        .order_by(Cotacao.created_at.desc())
        .limit(5)
        .all()
    )
    
    context = get_template_context(
        request,
        user=user,
        cotacoes_count=cotacoes_count,
        pedidos_count=pedidos_count,
        cotacoes_recentes=cotacoes_recentes,
    )
    return templates.TemplateResponse("pages/dashboard.html", context)


# =============================================================================
# Cotações
# =============================================================================

@web_router.get("/cotacoes", response_class=HTMLResponse)
async def cotacoes_list_page(
    request: Request,
    user: User = Depends(require_web_user),
    db: Session = Depends(get_db),
):
    """Render cotações list page."""
    tenant_id = user.tenant_id
    
    cotacoes = (
        db.query(Cotacao)
        .filter(Cotacao.tenant_id == tenant_id)
        .order_by(Cotacao.created_at.desc())
        .limit(100)
        .all()
    )
    
    context = get_template_context(request, user=user, cotacoes=cotacoes)
    return templates.TemplateResponse("pages/cotacoes_list.html", context)


@web_router.get("/cotacoes/table", response_class=HTMLResponse)
async def cotacoes_table_partial(
    request: Request,
    user: User = Depends(require_web_user),
    db: Session = Depends(get_db),
):
    """HTMX partial: return just the cotações table."""
    tenant_id = user.tenant_id
    
    cotacoes = (
        db.query(Cotacao)
        .filter(Cotacao.tenant_id == tenant_id)
        .order_by(Cotacao.created_at.desc())
        .limit(100)
        .all()
    )
    
    context = get_template_context(request, user=user, cotacoes=cotacoes)
    return templates.TemplateResponse("partials/table_cotacoes.html", context)


@web_router.post("/cotacoes/{cotacao_id}/enviar", response_class=HTMLResponse)
async def enviar_cotacao(
    request: Request,
    cotacao_id: UUID,
    user: User = Depends(require_web_user),
    db: Session = Depends(get_db),
):
    """Send cotação (change status to 'enviada')."""
    service = CotacaoService(db)
    
    try:
        cotacao = service.enviar_cotacao(cotacao_id=cotacao_id, tenant_id=user.tenant_id)
        
        context = get_template_context(
            request,
            user=user,
            cotacoes=[cotacao],
            flash_message="Cotação enviada com sucesso!",
            flash_type="success",
        )
        response = templates.TemplateResponse("partials/table_cotacoes.html", context)
        response.headers["HX-Trigger"] = "cotacaoUpdated"
        return response
        
    except CotacaoNaoPodeSerEnviadaException as e:
        return _flash_error(request, user, str(e))
    except ValueError as e:
        return _flash_error(request, user, str(e))


@web_router.post("/cotacoes/{cotacao_id}/aprovar", response_class=HTMLResponse)
async def aprovar_cotacao(
    request: Request,
    cotacao_id: UUID,
    user: User = Depends(require_web_user),
    db: Session = Depends(get_db),
):
    """Approve cotação (change status to 'aprovada')."""
    service = CotacaoService(db)
    
    try:
        cotacao = service.aprovar_cotacao(cotacao_id=cotacao_id, tenant_id=user.tenant_id)
        
        context = get_template_context(
            request,
            user=user,
            cotacoes=[cotacao],
            flash_message="Cotação aprovada com sucesso!",
            flash_type="success",
        )
        response = templates.TemplateResponse("partials/table_cotacoes.html", context)
        response.headers["HX-Trigger"] = "cotacaoUpdated"
        return response
        
    except CotacaoNaoPodeSerAprovadaException as e:
        return _flash_error(request, user, str(e))
    except ValueError as e:
        return _flash_error(request, user, str(e))


@web_router.post("/cotacoes/{cotacao_id}/cancelar", response_class=HTMLResponse)
async def cancelar_cotacao(
    request: Request,
    cotacao_id: UUID,
    user: User = Depends(require_web_user),
    db: Session = Depends(get_db),
):
    """Cancel cotação."""
    service = CotacaoService(db)
    
    try:
        cotacao = service.cancelar_cotacao(cotacao_id=cotacao_id, tenant_id=user.tenant_id)
        
        context = get_template_context(
            request,
            user=user,
            cotacoes=[cotacao],
            flash_message="Cotação cancelada.",
            flash_type="warning",
        )
        response = templates.TemplateResponse("partials/table_cotacoes.html", context)
        response.headers["HX-Trigger"] = "cotacaoUpdated"
        return response
        
    except CotacaoNaoPodeSerEditadaException as e:
        return _flash_error(request, user, str(e))
    except ValueError as e:
        return _flash_error(request, user, str(e))


# =============================================================================
# Pedidos
# =============================================================================

@web_router.get("/pedidos", response_class=HTMLResponse)
async def pedidos_list_page(
    request: Request,
    user: User = Depends(require_web_user),
    db: Session = Depends(get_db),
):
    """Render pedidos list page."""
    tenant_id = user.tenant_id
    
    pedidos = (
        db.query(Pedido)
        .filter(Pedido.tenant_id == tenant_id)
        .order_by(Pedido.created_at.desc())
        .limit(100)
        .all()
    )
    
    context = get_template_context(request, user=user, pedidos=pedidos)
    return templates.TemplateResponse("pages/pedidos_list.html", context)


@web_router.get("/pedidos/table", response_class=HTMLResponse)
async def pedidos_table_partial(
    request: Request,
    user: User = Depends(require_web_user),
    db: Session = Depends(get_db),
):
    """HTMX partial: return just the pedidos table."""
    tenant_id = user.tenant_id
    
    pedidos = (
        db.query(Pedido)
        .filter(Pedido.tenant_id == tenant_id)
        .order_by(Pedido.created_at.desc())
        .limit(100)
        .all()
    )
    
    context = get_template_context(request, user=user, pedidos=pedidos)
    return templates.TemplateResponse("partials/table_pedidos.html", context)


@web_router.post("/pedidos/from-cotacao/{cotacao_id}", response_class=HTMLResponse)
async def criar_pedido_from_cotacao(
    request: Request,
    cotacao_id: UUID,
    user: User = Depends(require_web_user),
    db: Session = Depends(get_db),
):
    """Convert approved cotação to pedido."""
    service = PedidoService(db)
    
    try:
        pedido = service.converter_cotacao_em_pedido(
            cotacao_id=cotacao_id,
            tenant_id=user.tenant_id,
            usuario_id=user.id,
        )
        
        # Redirect to pedidos page with success message
        response = Response(status_code=200)
        response.headers["HX-Redirect"] = "/web/pedidos"
        return response
        
    except (CotacaoNaoAprovadaException, CotacaoSemItensException) as e:
        return _flash_error(request, user, str(e))
    except ValueError as e:
        return _flash_error(request, user, str(e))


@web_router.post("/pedidos/{pedido_id}/cancelar", response_class=HTMLResponse)
async def cancelar_pedido(
    request: Request,
    pedido_id: UUID,
    user: User = Depends(require_web_user),
    db: Session = Depends(get_db),
):
    """Cancel pedido."""
    service = PedidoService(db)
    
    try:
        pedido = service.cancelar_pedido(pedido_id=pedido_id, tenant_id=user.tenant_id)
        
        context = get_template_context(
            request,
            user=user,
            pedidos=[pedido],
            flash_message="Pedido cancelado.",
            flash_type="warning",
        )
        response = templates.TemplateResponse("partials/table_pedidos.html", context)
        response.headers["HX-Trigger"] = "pedidoUpdated"
        return response
        
    except PedidoNaoPodeSerCanceladoException as e:
        return _flash_error(request, user, str(e))
    except ValueError as e:
        return _flash_error(request, user, str(e))


# =============================================================================
# Tenant JSON Endpoint
# =============================================================================

@web_router.get("/tenant.json")
async def tenant_json(request: Request):
    """
    Return tenant branding as JSON.
    Convenience endpoint for any client-side needs.
    """
    tenant = getattr(request.state, "tenant", None)
    branding = getattr(request.state, "tenant_branding", None)
    
    if not tenant:
        return {
            "name": "BaseCommerce",
            "logo_url": None,
            "primary_color": "#1a73e8",
            "secondary_color": "#ea4335",
            "features": {},
        }
    
    return {
        "name": tenant.nome,
        "slug": tenant.slug,
        "logo_url": branding.logo_url if branding else None,
        "primary_color": branding.primary_color if branding else "#1a73e8",
        "secondary_color": branding.secondary_color if branding else "#ea4335",
        "features": branding.feature_flags if branding else {},
    }


# =============================================================================
# Helpers
# =============================================================================

def _flash_error(request: Request, user: User, message: str) -> HTMLResponse:
    """Return a flash error partial."""
    context = get_template_context(
        request,
        user=user,
        flash_message=message,
        flash_type="error",
    )
    return templates.TemplateResponse("partials/flash.html", context)


