"""Web router for server-rendered HTMX pages."""

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, cast, Date
from sqlalchemy.orm import Session

from construction_app.application.services.cotacao_service import CotacaoService
from construction_app.application.services.pedido_service import PedidoService
from construction_app.core.database import get_db
from construction_app.domain.cotacao.exceptions import (
    CotacaoNaoPodeSerAprovadaException,
    CotacaoNaoPodeSerEditadaException,
    CotacaoNaoPodeSerEnviadaException,
)
from construction_app.domain.pedido.exceptions import (
    CotacaoNaoAprovadaException,
    CotacaoSemItensException,
    PedidoNaoPodeSerCanceladoException,
)
from construction_app.models.cotacao import Cotacao, CotacaoItem
from construction_app.models.pedido import Pedido, PedidoItem
from construction_app.models.produto import Produto
from construction_app.web.deps import UserClaims, get_optional_web_user, require_web_user
from construction_app.web.middleware import DefaultBranding

logger = logging.getLogger(__name__)

# Setup templates
TEMPLATES_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

web_router = APIRouter()


def get_template_context(
    request: Request,
    user: Optional[UserClaims] = None,
    **extra_context,
) -> dict:
    """Build common template context with tenant branding.
    
    Note: Tenant branding is now fetched client-side via /tenant.json
    which is served by the auth service.
    """
    tenant_slug = getattr(request.state, "tenant_slug", None)
    branding = DefaultBranding()
    
    return {
        "request": request,
        "user": user,
        "tenant_name": tenant_slug.capitalize() if tenant_slug else "BaseCommerce",
        "tenant_slug": tenant_slug,
        "branding": branding,
        **extra_context,
    }


# =============================================================================
# Authentication Routes (redirect to auth service)
# =============================================================================

@web_router.get("/login")
async def login_redirect():
    """Redirect to auth service login page."""
    return RedirectResponse(url="/auth/login", status_code=302)


@web_router.get("/logout")
async def logout_redirect():
    """Redirect to auth service logout."""
    return RedirectResponse(url="/auth/logout", status_code=302)


# =============================================================================
# Dashboard
# =============================================================================

@web_router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(
    request: Request,
    user: UserClaims = Depends(require_web_user),
    db: Session = Depends(get_db),
):
    """Render dashboard page with insights and action-oriented data."""
    tenant_id = user.tenant_id
    
    # Fetch insights data
    alerts = _get_alerts(db, tenant_id)
    recommended_actions = _get_recommended_actions(db, tenant_id, alerts)
    business_overview = _get_business_overview(db, tenant_id)
    construction_materials = _get_construction_materials(db, tenant_id)
    
    context = get_template_context(
        request,
        user=user,
        alerts=alerts,
        recommended_actions=recommended_actions,
        business_overview=business_overview,
        construction_materials=construction_materials,
    )
    return templates.TemplateResponse("pages/dashboard.html", context)


@web_router.get("/dashboard/alerts", response_class=HTMLResponse)
async def dashboard_alerts_partial(
    request: Request,
    user: UserClaims = Depends(require_web_user),
    db: Session = Depends(get_db),
):
    """HTMX partial: return just the alerts section for auto-refresh."""
    tenant_id = user.tenant_id
    alerts = _get_alerts(db, tenant_id)
    
    context = get_template_context(
        request,
        user=user,
        alerts=alerts,
    )
    return templates.TemplateResponse("partials/dashboard_alerts.html", context)


def _get_alerts(db: Session, tenant_id: UUID) -> list[dict[str, Any]]:
    """Get stock and price alerts from insights endpoints.
    
    TODO: Replace mock data with actual API calls to /api/v1/insights/stock/alerts
    and /api/v1/insights/supplier/price-alerts when available.
    """
    alerts = []
    
    try:
        # TODO: Call actual insights API endpoints
        # from construction_app.api.v1.endpoints.insights import get_stock_alerts, get_supplier_price_alerts
        # stock_alerts = await get_stock_alerts(tenant_id=tenant_id, db=db)
        # price_alerts = await get_supplier_price_alerts(tenant_id=tenant_id, db=db)
        
        # For now, use mock data as fallback
        alerts = [
            {
                "type": "stock_low",
                "severity": "warning",
                "title": "Cimento CP II abaixo do estoque ideal",
                "message": "Estoque atual: 50 sacos | Estoque mínimo recomendado: 150 sacos",
                "days_until_rupture": 2,
            },
            {
                "type": "price_increase",
                "severity": "info",
                "title": "Preço médio do cimento subiu 6% nos últimos 14 dias",
                "message": "Considere ajustar preço de venda ou buscar fornecedores alternativos",
            },
            {
                "type": "opportunity",
                "severity": "success",
                "title": "Areia média com alta procura e boa margem",
                "message": "Produto em alta demanda. Margem atual: 32%",
            },
        ]
    except Exception as e:
        logger.warning(f"Failed to fetch alerts: {e}. Using mock data.")
        # Keep mock data as fallback
    
    return alerts


def _get_recommended_actions(
    db: Session, tenant_id: UUID, alerts: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Get recommended actions based on insights and business state.
    
    TODO: Enhance with actual insights from /api/v1/insights/stock/replenishment,
    /api/v1/insights/supplier/price-alerts, and /api/v1/insights/sales/suggestions.
    """
    actions = []
    
    # Always show default actions
    actions.append({
        "id": "create_quotation",
        "title": "Criar novo orçamento",
        "description": "Crie um orçamento para sua obra ou cliente",
        "url": "/web/cotacoes",
        "priority": "primary",
        "icon": "document-text",
    })
    
    # Check if there are stock alerts to suggest replenishment
    stock_alerts = [a for a in alerts if a.get("type") == "stock_low"]
    if stock_alerts:
        actions.append({
            "id": "replenish_stock",
            "title": "Repor estoque sugerido",
            "description": f"{len(stock_alerts)} material(is) com estoque abaixo do ideal",
            "url": "/web/produtos",
            "priority": "warning",
            "icon": "package",
        })
    
    # Check for price alerts
    price_alerts = [a for a in alerts if a.get("type") == "price_increase"]
    if price_alerts:
        actions.append({
            "id": "adjust_prices",
            "title": "Ajustar preços",
            "description": "Materiais com variação de preço recente",
            "url": "/web/produtos",
            "priority": "info",
            "icon": "currency-dollar",
        })
    
    # Check for opportunities
    opportunities = [a for a in alerts if a.get("type") == "opportunity"]
    if opportunities:
        actions.append({
            "id": "view_opportunities",
            "title": "Ver oportunidades de venda",
            "description": f"{len(opportunities)} oportunidade(s) identificada(s)",
            "url": "/web/pedidos",
            "priority": "success",
            "icon": "trending-up",
        })
    
    # Always show view quotations
    cotacoes_ativas = (
        db.query(Cotacao)
        .filter(
            Cotacao.tenant_id == tenant_id,
            Cotacao.status.in_(["rascunho", "enviada", "aprovada"]),
        )
        .count()
    )
    if cotacoes_ativas > 0:
        actions.append({
            "id": "view_quotations",
            "title": "Ver orçamentos ativos",
            "description": f"{cotacoes_ativas} orçamento(s) em andamento",
            "url": "/web/cotacoes",
            "priority": "secondary",
            "icon": "document-search",
        })
    
    return actions


def _get_business_overview(db: Session, tenant_id: UUID) -> dict[str, Any]:
    """Get business overview metrics."""
    hoje = datetime.utcnow().date()
    inicio_semana = hoje - timedelta(days=hoje.weekday())
    
    # Vendas da semana (pedidos entregues)
    vendas_semana = (
        db.query(func.sum(PedidoItem.valor_total))
        .join(Pedido, PedidoItem.pedido_id == Pedido.id)
        .filter(
            Pedido.tenant_id == tenant_id,
            Pedido.status == "entregue",
            Pedido.entregue_em.isnot(None),
            cast(Pedido.entregue_em, Date) >= inicio_semana,
        )
        .scalar()
        or 0
    )
    
    # Orçamentos ativos por status
    cotacoes_por_status = (
        db.query(Cotacao.status, func.count(Cotacao.id))
        .filter(
            Cotacao.tenant_id == tenant_id,
            Cotacao.status.in_(["rascunho", "enviada", "aprovada"]),
        )
        .group_by(Cotacao.status)
        .all()
    )
    
    orcamentos_ativos = {
        "total": sum(count for _, count in cotacoes_por_status),
        "por_status": {status: count for status, count in cotacoes_por_status},
    }
    
    # Produtos mais vendidos (últimos 30 dias)
    inicio_periodo = hoje - timedelta(days=30)
    produtos_mais_vendidos = (
        db.query(
            Produto.id,
            Produto.nome,
            Produto.unidade,
            func.sum(PedidoItem.quantidade).label("quantidade_total"),
            func.count(PedidoItem.id).label("num_vendas"),
        )
        .join(PedidoItem, Produto.id == PedidoItem.produto_id)
        .join(Pedido, PedidoItem.pedido_id == Pedido.id)
        .filter(
            Pedido.tenant_id == tenant_id,
            Pedido.status == "entregue",
            Pedido.entregue_em.isnot(None),
            cast(Pedido.entregue_em, Date) >= inicio_periodo,
        )
        .group_by(Produto.id, Produto.nome, Produto.unidade)
        .order_by(func.sum(PedidoItem.quantidade).desc())
        .limit(5)
        .all()
    )
    
    top_produtos = [
        {
            "id": str(p.id),
            "nome": p.nome,
            "unidade": p.unidade,
            "quantidade_total": float(p.quantidade_total),
            "num_vendas": p.num_vendas,
        }
        for p in produtos_mais_vendidos
    ]
    
    # Format currency value
    vendas_value = float(vendas_semana) if vendas_semana else 0.0
    vendas_formatted = f"R$ {vendas_value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    
    return {
        "week_sales": {
            "value": vendas_value,
            "formatted": vendas_formatted,
        },
        "active_quotations": orcamentos_ativos,
        "top_products": top_produtos,
    }


def _get_construction_materials(db: Session, tenant_id: UUID) -> dict[str, Any]:
    """Get construction materials specific data.
    
    TODO: Enhance with actual insights from engines when available.
    """
    # Materiais mais vendidos (já calculado em business_overview, mas específico aqui)
    inicio_periodo = datetime.utcnow().date() - timedelta(days=90)
    
    materiais_mais_vendidos = (
        db.query(
            Produto.id,
            Produto.nome,
            Produto.unidade,
            func.sum(PedidoItem.quantidade).label("quantidade_total"),
        )
        .join(PedidoItem, Produto.id == PedidoItem.produto_id)
        .join(Pedido, PedidoItem.pedido_id == Pedido.id)
        .filter(
            Pedido.tenant_id == tenant_id,
            Pedido.status == "entregue",
            Pedido.entregue_em.isnot(None),
            cast(Pedido.entregue_em, Date) >= inicio_periodo,
        )
        .group_by(Produto.id, Produto.nome, Produto.unidade)
        .order_by(func.sum(PedidoItem.quantidade).desc())
        .limit(5)
        .all()
    )
    
    # TODO: Materiais parados (sem vendas nos últimos 90 dias)
    # TODO: Itens críticos com estoque baixo (usar insights de stock alerts)
    
    return {
        "top_selling": [
            {
                "id": str(m.id),
                "nome": m.nome,
                "unidade": m.unidade,
                "quantidade_total": float(m.quantidade_total),
            }
            for m in materiais_mais_vendidos
        ],
        "stagnant": [],  # TODO: Implement with actual data
        "critical_items": [],  # TODO: Implement with stock alerts insights
    }


# =============================================================================
# Cotações
# =============================================================================

@web_router.get("/cotacoes", response_class=HTMLResponse)
async def cotacoes_list_page(
    request: Request,
    user: UserClaims = Depends(require_web_user),
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
    user: UserClaims = Depends(require_web_user),
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
    user: UserClaims = Depends(require_web_user),
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
    user: UserClaims = Depends(require_web_user),
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
    user: UserClaims = Depends(require_web_user),
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
    user: UserClaims = Depends(require_web_user),
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
    user: UserClaims = Depends(require_web_user),
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
    user: UserClaims = Depends(require_web_user),
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
    user: UserClaims = Depends(require_web_user),
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
# Helpers
# =============================================================================

def _flash_error(request: Request, user: UserClaims, message: str) -> HTMLResponse:
    """Return a flash error partial."""
    context = get_template_context(
        request,
        user=user,
        flash_message=message,
        flash_type="error",
    )
    return templates.TemplateResponse("partials/flash.html", context)
