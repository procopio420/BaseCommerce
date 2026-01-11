"""Web router for server-rendered HTMX pages."""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, cast, Date, or_
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
from construction_app.models.cliente import Cliente
from construction_app.models.cotacao import Cotacao, CotacaoItem
from construction_app.models.obra import Obra
from construction_app.models.pedido import Pedido, PedidoItem
from construction_app.models.produto import Produto
from construction_app.web.deps import UserClaims, get_optional_web_user, require_web_user
from construction_app.web.middleware import DefaultBranding

logger = logging.getLogger(__name__)

# Wizard state storage (in-memory, simple approach)
# In production, consider using Redis or session middleware
_wizard_states: dict[str, dict[str, Any]] = {}

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

@web_router.get("/ui-kit", response_class=HTMLResponse)
async def ui_kit_page(
    request: Request,
    user: UserClaims = Depends(require_web_user),
):
    """UI Kit page for design system validation."""
    context = get_template_context(request, user=user)
    return templates.TemplateResponse("pages/ui_kit.html", context)


@web_router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(
    request: Request,
    user: UserClaims = Depends(require_web_user),
    db: Session = Depends(get_db),
):
    """Render dashboard page with insights and action-oriented data."""
    tenant_id = user.tenant_id
    
    # Fetch insights data
    alerts = _get_alerts(db, tenant_id, user)
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
    alerts = _get_alerts(db, tenant_id, user)
    
    context = get_template_context(
        request,
        user=user,
        alerts=alerts,
    )
    return templates.TemplateResponse("partials/dashboard_alerts.html", context)


def _get_alerts(db: Session, tenant_id: UUID, user: Optional[UserClaims] = None) -> list[dict[str, Any]]:
    """Get stock and price alerts from insights endpoints."""
    alerts = []
    
    try:
        from construction_app.api.v1.endpoints.insights import get_stock_alerts, get_supplier_price_alerts
        from sqlalchemy import text
        
        # Get stock alerts
        stock_query = """
            SELECT 
                id, product_id, alert_type, risk_level, 
                current_stock, minimum_stock, days_until_rupture,
                explanation, status, created_at, updated_at
            FROM engine_stock_alerts
            WHERE tenant_id = :tenant_id AND status = 'active'
            ORDER BY created_at DESC LIMIT 5
        """
        stock_result = db.execute(text(stock_query), {"tenant_id": tenant_id})
        stock_alerts_data = []
        product_ids = set()
        for row in stock_result:
            stock_alerts_data.append({
                "id": str(row[0]),
                "product_id": str(row[1]),
                "alert_type": row[2],
                "risk_level": row[3],
                "current_stock": row[4],
                "minimum_stock": row[5],
                "days_until_rupture": row[6],
                "explanation": row[7],
            })
            product_ids.add(UUID(str(row[1])))
        
        # Get price alerts
        price_query = """
            SELECT 
                id, product_id, alert_type,
                current_price, reference_price, price_change_percent,
                explanation, status, created_at, updated_at
            FROM engine_supplier_price_alerts
            WHERE tenant_id = :tenant_id AND status = 'active'
            ORDER BY created_at DESC LIMIT 5
        """
        price_result = db.execute(text(price_query), {"tenant_id": tenant_id})
        price_alerts_data = []
        for row in price_result:
            price_alerts_data.append({
                "id": str(row[0]),
                "product_id": str(row[1]),
                "alert_type": row[2],
                "current_price": row[4],
                "reference_price": row[5],
                "price_change_percent": row[6],
                "explanation": row[7],
            })
            product_ids.add(UUID(str(row[1])))
        
        # Fetch product names
        produtos_map = {}
        if product_ids:
            produtos = db.query(Produto).filter(Produto.id.in_(product_ids), Produto.tenant_id == tenant_id).all()
            produtos_map = {str(p.id): p for p in produtos}
        
        # Convert stock alerts
        for alert_data in stock_alerts_data[:3]:  # Limit to 3
            produto = produtos_map.get(alert_data["product_id"])
            produto_nome = produto.nome if produto else f"Produto {alert_data['product_id'][:8]}"
            
            risk_level = alert_data.get("risk_level", "medio")
            severity_map = {"alto": "danger", "medio": "warning", "baixo": "info"}
            severity = severity_map.get(risk_level, "warning")
            
            alert = {
                "type": "stock_low",
                "severity": severity,
                "title": f"{produto_nome} abaixo do estoque ideal",
                "message": f"Estoque atual: {alert_data.get('current_stock', 0)} | Estoque mínimo: {alert_data.get('minimum_stock', 0)}",
                "days_until_rupture": alert_data.get("days_until_rupture"),
                "actions": [
                    {"label": "Gerar Pedido de Compra", "href": f"/web/alerts/{alert_data['id']}/create-purchase-order"},
                    {"label": "Ajustar Estoque", "href": f"/web/alerts/{alert_data['id']}/adjust-stock"}
                ],
            }
            alerts.append(alert)
        
        # Convert price alerts
        for alert_data in price_alerts_data[:2]:  # Limit to 2
            produto = produtos_map.get(alert_data["product_id"])
            produto_nome = produto.nome if produto else f"Produto {alert_data['product_id'][:8]}"
            
            price_change = alert_data.get("price_change_percent", 0)
            alert = {
                "type": "price_increase" if price_change > 0 else "price_decrease",
                "severity": "info",
                "title": f"Preço de {produto_nome} {'subiu' if price_change > 0 else 'desceu'} {abs(price_change):.1f}%",
                "message": alert_data.get("explanation", "Considere ajustar preço de venda"),
                "actions": [
                    {"label": "Ajustar Preços", "href": f"/web/alerts/{alert_data['id']}/adjust-price"}
                ],
            }
            alerts.append(alert)
        
    except Exception as e:
        logger.warning(f"Failed to fetch alerts: {e}. Using mock data.", exc_info=True)
        # Fallback to mock data
        alerts = [
            {
                "type": "stock_low",
                "severity": "warning",
                "title": "Cimento CP II abaixo do estoque ideal",
                "message": "Estoque atual: 50 sacos | Estoque mínimo recomendado: 150 sacos",
                "days_until_rupture": 2,
                "actions": [
                    {"label": "Gerar Pedido de Compra", "href": "/web/alerts/1/create-purchase-order"},
                    {"label": "Ajustar Estoque", "href": "/web/alerts/1/adjust-stock"}
                ],
            },
            {
                "type": "price_increase",
                "severity": "info",
                "title": "Preço médio do cimento subiu 6% nos últimos 14 dias",
                "message": "Considere ajustar preço de venda ou buscar fornecedores alternativos",
                "actions": [
                    {"label": "Ajustar Preços", "href": "/web/alerts/2/adjust-price"}
                ],
            },
        ]
    
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
    status: str = Query(None),
    cliente_id: str = Query(None),
    periodo: str = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    """HTMX partial: return just the cotações table."""
    tenant_id = user.tenant_id
    
    query = db.query(Cotacao).filter(Cotacao.tenant_id == tenant_id)
    
    # Apply filters
    if status:
        query = query.filter(Cotacao.status == status)
    
    if cliente_id:
        try:
            cliente_uuid = UUID(cliente_id)
            query = query.filter(Cotacao.cliente_id == cliente_uuid)
        except (ValueError, TypeError):
            pass
    
    if periodo:
        hoje = datetime.utcnow().date()
        if periodo == "hoje":
            data_inicial = hoje
        elif periodo == "semana":
            data_inicial = hoje - timedelta(days=hoje.weekday())
        elif periodo == "mes":
            data_inicial = hoje.replace(day=1)
        else:
            data_inicial = None
        
        if data_inicial:
            query = query.filter(cast(Cotacao.created_at, Date) >= data_inicial)
    
    # Get total count for pagination
    total_items = query.count()
    total_pages = (total_items + limit - 1) // limit if limit > 0 else 1
    current_page = (skip // limit) + 1 if limit > 0 else 1
    
    # Apply pagination
    cotacoes = query.order_by(Cotacao.created_at.desc()).offset(skip).limit(limit).all()
    
    context = get_template_context(
        request, 
        user=user, 
        cotacoes=cotacoes,
        total_items=total_items,
        total_pages=total_pages,
        current_page=current_page,
        limit=limit,
        filters={"status": status, "cliente_id": cliente_id, "periodo": periodo}
    )
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
    status: str = Query(None),
    periodo: str = Query(None),
):
    """Render pedidos list page."""
    tenant_id = user.tenant_id
    
    context = get_template_context(
        request, 
        user=user,
        filters={"status": status, "periodo": periodo}
    )
    return templates.TemplateResponse("pages/pedidos_list.html", context)


@web_router.get("/pedidos/table", response_class=HTMLResponse)
async def pedidos_table_partial(
    request: Request,
    user: UserClaims = Depends(require_web_user),
    db: Session = Depends(get_db),
    status: str = Query(None),
    periodo: str = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    """HTMX partial: return just the pedidos table."""
    tenant_id = user.tenant_id
    
    query = db.query(Pedido).filter(Pedido.tenant_id == tenant_id)
    
    # Apply filters
    if status:
        query = query.filter(Pedido.status == status)
    
    if periodo:
        hoje = datetime.utcnow().date()
        if periodo == "hoje":
            data_inicial = hoje
        elif periodo == "semana":
            data_inicial = hoje - timedelta(days=hoje.weekday())
        elif periodo == "mes":
            data_inicial = hoje.replace(day=1)
        else:
            data_inicial = None
        
        if data_inicial:
            query = query.filter(cast(Pedido.created_at, Date) >= data_inicial)
    
    # Get total count for pagination
    total_items = query.count()
    total_pages = (total_items + limit - 1) // limit if limit > 0 else 1
    current_page = (skip // limit) + 1 if limit > 0 else 1
    
    # Apply pagination
    pedidos = query.order_by(Pedido.created_at.desc()).offset(skip).limit(limit).all()
    
    context = get_template_context(
        request, 
        user=user, 
        pedidos=pedidos,
        total_items=total_items,
        total_pages=total_pages,
        current_page=current_page,
        limit=limit,
        filters={"status": status, "periodo": periodo}
    )
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


@web_router.get("/pedidos/{pedido_id}/details", response_class=HTMLResponse)
async def pedido_details_partial(
    request: Request,
    pedido_id: UUID,
    user: UserClaims = Depends(require_web_user),
    db: Session = Depends(get_db),
):
    """HTMX partial: return pedido details for drawer."""
    tenant_id = user.tenant_id
    
    pedido = (
        db.query(Pedido)
        .filter(Pedido.id == pedido_id, Pedido.tenant_id == tenant_id)
        .first()
    )
    
    if not pedido:
        return _flash_error(request, user, "Pedido não encontrado")
    
    context = get_template_context(request, user=user, pedido=pedido)
    return templates.TemplateResponse("partials/pedido_details.html", context)


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
# Insights
# =============================================================================

@web_router.get("/insights", response_class=HTMLResponse)
async def insights_page(
    request: Request,
    user: UserClaims = Depends(require_web_user),
):
    """Insights hub page."""
    context = get_template_context(request, user=user)
    return templates.TemplateResponse("pages/insights.html", context)


@web_router.get("/insights/estoque", response_class=HTMLResponse)
async def insights_estoque_partial(
    request: Request,
    user: UserClaims = Depends(require_web_user),
    db: Session = Depends(get_db),
    cursor: str = Query(None),
    limit: int = Query(10, ge=1, le=50),
):
    """Stock insights partial."""
    tenant_id = user.tenant_id
    
    try:
        from sqlalchemy import text
        from datetime import datetime
        
        # Parse cursor
        cursor_dt = None
        if cursor:
            try:
                cursor_dt = datetime.fromisoformat(cursor.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                pass
        
        # Get stock alerts
        query = """
            SELECT 
                id, product_id, alert_type, risk_level, 
                current_stock, minimum_stock, days_until_rupture,
                explanation, status, created_at, updated_at
            FROM engine_stock_alerts
            WHERE tenant_id = :tenant_id AND status = 'active'
        """
        params = {"tenant_id": tenant_id, "limit": limit + 1}
        if cursor_dt:
            query += " AND created_at < :cursor"
            params["cursor"] = cursor_dt
        
        query += " ORDER BY created_at DESC LIMIT :limit"
        result = db.execute(text(query), params)
        
        stock_alerts_data = []
        product_ids = set()
        for row in result:
            stock_alerts_data.append({
                "id": str(row[0]),
                "product_id": str(row[1]),
                "alert_type": row[2],
                "risk_level": row[3],
                "current_stock": row[4],
                "minimum_stock": row[5],
                "days_until_rupture": row[6],
                "explanation": row[7],
                "created_at": row[9].isoformat() if row[9] else None,
            })
            product_ids.add(UUID(str(row[1])))
        
        has_more = len(stock_alerts_data) > limit
        if has_more:
            stock_alerts_data = stock_alerts_data[:limit]
            next_cursor = stock_alerts_data[-1]["created_at"] if stock_alerts_data else None
        else:
            next_cursor = None
        
        # Get replenishment suggestions
        repl_query = """
            SELECT 
                id, product_id, suggested_quantity, current_stock,
                minimum_stock, maximum_stock, priority,
                explanation, status, created_at, updated_at
            FROM engine_replenishment_suggestions
            WHERE tenant_id = :tenant_id AND status = 'pending'
            ORDER BY created_at DESC LIMIT 10
        """
        repl_result = db.execute(text(repl_query), {"tenant_id": tenant_id})
        replenishment_data = []
        for row in repl_result:
            replenishment_data.append({
                "id": str(row[0]),
                "product_id": str(row[1]),
                "suggested_quantity": row[2],
                "current_stock": row[3],
                "priority": row[6],
                "explanation": row[7],
            })
            product_ids.add(UUID(str(row[1])))
        
        # Fetch product names
        produtos_map = {}
        if product_ids:
            produtos = db.query(Produto).filter(Produto.id.in_(product_ids), Produto.tenant_id == tenant_id).all()
            produtos_map = {str(p.id): p for p in produtos}
        
        # Format alerts with product names
        stock_alerts = []
        for alert_data in stock_alerts_data:
            produto = produtos_map.get(alert_data["product_id"])
            alert_data["produto"] = produto
            stock_alerts.append(alert_data)
        
        # Format replenishment with product names
        replenishment_suggestions = []
        for sugg_data in replenishment_data:
            produto = produtos_map.get(sugg_data["product_id"])
            sugg_data["produto"] = produto
            replenishment_suggestions.append(sugg_data)
        
    except Exception as e:
        logger.warning(f"Failed to fetch stock insights: {e}", exc_info=True)
        stock_alerts = []
        replenishment_suggestions = []
        has_more = False
        next_cursor = None
    
    context = get_template_context(
        request,
        user=user,
        stock_alerts=stock_alerts,
        replenishment_suggestions=replenishment_suggestions,
        has_more=has_more,
        next_cursor=next_cursor,
    )
    return templates.TemplateResponse("partials/insights_estoque.html", context)


@web_router.get("/insights/precos", response_class=HTMLResponse)
async def insights_precos_partial(
    request: Request,
    user: UserClaims = Depends(require_web_user),
    db: Session = Depends(get_db),
    cursor: str = Query(None),
    limit: int = Query(10, ge=1, le=50),
):
    """Price insights partial."""
    tenant_id = user.tenant_id
    
    try:
        from sqlalchemy import text
        from datetime import datetime
        
        # Parse cursor
        cursor_dt = None
        if cursor:
            try:
                cursor_dt = datetime.fromisoformat(cursor.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                pass
        
        # Get price alerts
        query = """
            SELECT 
                id, product_id, supplier_id, alert_type,
                current_price, reference_price, price_change_percent,
                explanation, status, created_at, updated_at
            FROM engine_supplier_price_alerts
            WHERE tenant_id = :tenant_id AND status = 'active'
        """
        params = {"tenant_id": tenant_id, "limit": limit + 1}
        if cursor_dt:
            query += " AND created_at < :cursor"
            params["cursor"] = cursor_dt
        
        query += " ORDER BY created_at DESC LIMIT :limit"
        result = db.execute(text(query), params)
        
        price_alerts_data = []
        product_ids = set()
        for row in result:
            price_alerts_data.append({
                "id": str(row[0]),
                "product_id": str(row[1]),
                "supplier_id": str(row[2]) if row[2] else None,
                "alert_type": row[3],
                "current_price": row[4],
                "reference_price": row[5],
                "price_change_percent": row[6],
                "explanation": row[7],
                "created_at": row[9].isoformat() if row[9] else None,
            })
            product_ids.add(UUID(str(row[1])))
        
        has_more = len(price_alerts_data) > limit
        if has_more:
            price_alerts_data = price_alerts_data[:limit]
            next_cursor = price_alerts_data[-1]["created_at"] if price_alerts_data else None
        else:
            next_cursor = None
        
        # Fetch product names
        produtos_map = {}
        if product_ids:
            produtos = db.query(Produto).filter(Produto.id.in_(product_ids), Produto.tenant_id == tenant_id).all()
            produtos_map = {str(p.id): p for p in produtos}
        
        # Format alerts with product names
        price_alerts = []
        for alert_data in price_alerts_data:
            produto = produtos_map.get(alert_data["product_id"])
            alert_data["produto"] = produto
            price_alerts.append(alert_data)
        
    except Exception as e:
        logger.warning(f"Failed to fetch price insights: {e}", exc_info=True)
        price_alerts = []
        has_more = False
        next_cursor = None
    
    context = get_template_context(
        request,
        user=user,
        price_alerts=price_alerts,
        has_more=has_more,
        next_cursor=next_cursor,
    )
    return templates.TemplateResponse("partials/insights_precos.html", context)


@web_router.get("/insights/vendas", response_class=HTMLResponse)
async def insights_vendas_partial(
    request: Request,
    user: UserClaims = Depends(require_web_user),
    db: Session = Depends(get_db),
    cursor: str = Query(None),
    limit: int = Query(10, ge=1, le=50),
):
    """Sales insights partial."""
    tenant_id = user.tenant_id
    
    try:
        from sqlalchemy import text
        from datetime import datetime
        
        # Parse cursor
        cursor_dt = None
        if cursor:
            try:
                cursor_dt = datetime.fromisoformat(cursor.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                pass
        
        # Get sales suggestions
        query = """
            SELECT 
                id, suggestion_type, source_product_id, suggested_product_id,
                frequency, priority, explanation, status, created_at, updated_at
            FROM engine_sales_suggestions
            WHERE tenant_id = :tenant_id AND status = 'active'
        """
        params = {"tenant_id": tenant_id, "limit": limit + 1}
        if cursor_dt:
            query += " AND created_at < :cursor"
            params["cursor"] = cursor_dt
        
        query += " ORDER BY created_at DESC LIMIT :limit"
        result = db.execute(text(query), params)
        
        sales_suggestions_data = []
        product_ids = set()
        for row in result:
            sales_suggestions_data.append({
                "id": str(row[0]),
                "suggestion_type": row[1],
                "source_product_id": str(row[2]) if row[2] else None,
                "suggested_product_id": str(row[3]) if row[3] else None,
                "frequency": row[4],
                "priority": row[5],
                "explanation": row[6],
                "created_at": row[8].isoformat() if row[8] else None,
            })
            if row[2]:
                product_ids.add(UUID(str(row[2])))
            if row[3]:
                product_ids.add(UUID(str(row[3])))
        
        has_more = len(sales_suggestions_data) > limit
        if has_more:
            sales_suggestions_data = sales_suggestions_data[:limit]
            next_cursor = sales_suggestions_data[-1]["created_at"] if sales_suggestions_data else None
        else:
            next_cursor = None
        
        # Fetch product names
        produtos_map = {}
        if product_ids:
            produtos = db.query(Produto).filter(Produto.id.in_(product_ids), Produto.tenant_id == tenant_id).all()
            produtos_map = {str(p.id): p for p in produtos}
        
        # Format suggestions with product names
        sales_suggestions = []
        for sugg_data in sales_suggestions_data:
            if sugg_data["source_product_id"]:
                produto = produtos_map.get(sugg_data["source_product_id"])
                sugg_data["source_produto"] = produto
            if sugg_data["suggested_product_id"]:
                produto = produtos_map.get(sugg_data["suggested_product_id"])
                sugg_data["suggested_produto"] = produto
            sales_suggestions.append(sugg_data)
        
    except Exception as e:
        logger.warning(f"Failed to fetch sales insights: {e}", exc_info=True)
        sales_suggestions = []
        has_more = False
        next_cursor = None
    
    context = get_template_context(
        request,
        user=user,
        sales_suggestions=sales_suggestions,
        has_more=has_more,
        next_cursor=next_cursor,
    )
    return templates.TemplateResponse("partials/insights_vendas.html", context)


@web_router.get("/insights/entregas", response_class=HTMLResponse)
async def insights_entregas_partial(
    request: Request,
    user: UserClaims = Depends(require_web_user),
):
    """Delivery insights partial."""
    context = get_template_context(request, user=user)
    return templates.TemplateResponse("partials/insights_entregas.html", context)


# =============================================================================
# Cotacoes New (Wizard)
# =============================================================================

@web_router.get("/cotacoes/new", response_class=HTMLResponse)
async def cotacoes_new_page(
    request: Request,
    user: UserClaims = Depends(require_web_user),
    step: int = Query(1, ge=1, le=4),
    db: Session = Depends(get_db),
):
    """New cotação wizard page."""
    state = _get_wizard_state(user.id)
    state["step"] = step
    _save_wizard_state(user.id, state)
    
    # Load clientes and obras for step 1
    clientes = []
    obras = []
    if step == 1:
        clientes = db.query(Cliente).filter(Cliente.tenant_id == user.tenant_id).order_by(Cliente.nome).all()
        if state.get("cliente_id"):
            try:
                cliente_uuid = UUID(state["cliente_id"])
                obras = db.query(Obra).filter(
                    Obra.tenant_id == user.tenant_id,
                    Obra.cliente_id == cliente_uuid
                ).order_by(Obra.nome).all()
            except (ValueError, TypeError):
                pass
    
    # Calculate summary
    summary = _calculate_cotacao_summary(state, db, user.tenant_id)
    
    context = get_template_context(
        request,
        user=user,
        step=step,
        wizard_state=state,
        clientes=clientes,
        obras=obras,
        summary=summary,
    )
    return templates.TemplateResponse("pages/cotacoes_new.html", context)


@web_router.post("/cotacoes/new/step1", response_class=HTMLResponse)
async def cotacoes_new_step1(
    request: Request,
    user: UserClaims = Depends(require_web_user),
    cliente_id: str = Form(None),
    obra_id: str = Form(None),
):
    """Step 1: Save cliente/obra and move to step 2."""
    state = _get_wizard_state(user.id)
    
    if not cliente_id:
        context = get_template_context(request, user=user, error="Cliente é obrigatório")
        return templates.TemplateResponse("pages/cotacoes_new.html", context, status_code=400)
    
    state["cliente_id"] = cliente_id
    state["obra_id"] = obra_id if obra_id else None
    state["step"] = 2
    _save_wizard_state(user.id, state)
    
    return RedirectResponse(url="/web/cotacoes/new?step=2", status_code=302)


@web_router.get("/cotacoes/new/search-products", response_class=HTMLResponse)
async def cotacoes_new_search_products(
    request: Request,
    user: UserClaims = Depends(require_web_user),
    q: str = Query(""),
    db: Session = Depends(get_db),
):
    """Search products for wizard step 2."""
    if not q or len(q) < 2:
        context = get_template_context(request, user=user, produtos=[], search_query=q)
        return templates.TemplateResponse("partials/product_search_results.html", context)
    
    produtos = db.query(Produto).filter(
        Produto.tenant_id == user.tenant_id,
        Produto.ativo == True,
        or_(
            Produto.nome.ilike(f"%{q}%"),
            Produto.codigo.ilike(f"%{q}%"),
            Produto.descricao.ilike(f"%{q}%"),
        )
    ).order_by(Produto.nome).limit(10).all()
    
    context = get_template_context(request, user=user, produtos=produtos, search_query=q)
    return templates.TemplateResponse("partials/product_search_results.html", context)


@web_router.post("/cotacoes/new/add-item", response_class=HTMLResponse)
async def cotacoes_new_add_item(
    request: Request,
    user: UserClaims = Depends(require_web_user),
    produto_id: str = Form(...),
    quantidade: str = Form(...),
    preco_unitario: str = Form(None),
    db: Session = Depends(get_db),
):
    """Add item to wizard cart."""
    state = _get_wizard_state(user.id)
    
    try:
        produto_uuid = UUID(produto_id)
        produto = db.query(Produto).filter(
            Produto.id == produto_uuid,
            Produto.tenant_id == user.tenant_id,
            Produto.ativo == True
        ).first()
        
        if not produto:
            return _flash_error(request, user, "Produto não encontrado ou inativo")
        
        preco = Decimal(preco_unitario) if preco_unitario and Decimal(preco_unitario) > 0 else produto.preco_base
        qtd = Decimal(quantidade)
        
        # Check if produto already in cart
        item_index = None
        for idx, item in enumerate(state.get("itens", [])):
            if item["produto_id"] == produto_id:
                item_index = idx
                break
        
        item_data = {
            "produto_id": produto_id,
            "quantidade": str(qtd),
            "preco_unitario": str(preco),
            "desconto_percentual": "0",
            "observacoes": "",
        }
        
        if item_index is not None:
            # Update existing item
            old_qtd = Decimal(state["itens"][item_index]["quantidade"])
            state["itens"][item_index] = item_data
            state["itens"][item_index]["quantidade"] = str(old_qtd + qtd)
        else:
            # Add new item
            if "itens" not in state:
                state["itens"] = []
            state["itens"].append(item_data)
        
        _save_wizard_state(user.id, state)
        
        # Return updated summary (will update via hx-swap-oob)
        summary = _calculate_cotacao_summary(state, db, user.tenant_id)
        context = get_template_context(request, user=user, wizard_state=state, summary=summary)
        response = templates.TemplateResponse("partials/cotacao_summary.html", context)
        # Also update cart items via oob
        cart_response = templates.TemplateResponse("partials/cotacao_cart_items.html", context)
        cart_html = str(cart_response.body, 'utf-8')
        # Use hx-swap-oob to update both summary and cart
        response.headers["HX-Trigger-After-Swap"] = 'cartUpdated'
        return response
        
    except (ValueError, TypeError) as e:
        return _flash_error(request, user, f"Erro ao adicionar item: {str(e)}")


@web_router.post("/cotacoes/new/remove-item", response_class=HTMLResponse)
async def cotacoes_new_remove_item(
    request: Request,
    user: UserClaims = Depends(require_web_user),
    item_index: int = Form(...),
    db: Session = Depends(get_db),
):
    """Remove item from wizard cart."""
    state = _get_wizard_state(user.id)
    
    try:
        if 0 <= item_index < len(state.get("itens", [])):
            state["itens"].pop(item_index)
            _save_wizard_state(user.id, state)
        
        summary = _calculate_cotacao_summary(state, db, user.tenant_id)
        context = get_template_context(request, user=user, wizard_state=state, summary=summary)
        return templates.TemplateResponse("partials/cotacao_summary.html", context)
    except (ValueError, IndexError):
        return _flash_error(request, user, "Item não encontrado")


@web_router.post("/cotacoes/new/step3", response_class=HTMLResponse)
async def cotacoes_new_step3(
    request: Request,
    user: UserClaims = Depends(require_web_user),
    desconto_percentual: str = Form("0"),
    observacoes: str = Form(""),
):
    """Step 3: Save discounts/observations and move to step 4."""
    state = _get_wizard_state(user.id)
    
    if not state.get("itens"):
        return _flash_error(request, user, "Adicione pelo menos um item antes de continuar")
    
    state["desconto_percentual"] = str(Decimal(desconto_percentual) if desconto_percentual else Decimal("0"))
    state["observacoes"] = observacoes
    state["step"] = 4
    _save_wizard_state(user.id, state)
    
    return RedirectResponse(url="/web/cotacoes/new?step=4", status_code=302)


@web_router.post("/cotacoes/new/finalize", response_class=HTMLResponse)
async def cotacoes_new_finalize(
    request: Request,
    user: UserClaims = Depends(require_web_user),
    db: Session = Depends(get_db),
):
    """Finalize wizard and create cotação."""
    state = _get_wizard_state(user.id)
    
    # Validate
    if not state.get("cliente_id"):
        return _flash_error(request, user, "Cliente é obrigatório")
    
    if not state.get("itens"):
        return _flash_error(request, user, "Adicione pelo menos um item")
    
    try:
        service = CotacaoService(db)
        
        # Convert state to service format
        itens = []
        for item in state["itens"]:
            itens.append({
                "produto_id": UUID(item["produto_id"]),
                "quantidade": Decimal(item["quantidade"]),
                "preco_unitario": Decimal(item.get("preco_unitario", 0)),
                "desconto_percentual": Decimal(item.get("desconto_percentual", 0)),
                "observacoes": item.get("observacoes"),
                "ordem": len(itens),
            })
        
        cotacao = service.criar_cotacao(
            tenant_id=user.tenant_id,
            cliente_id=UUID(state["cliente_id"]),
            usuario_id=user.id,
            itens=itens,
            obra_id=UUID(state["obra_id"]) if state.get("obra_id") else None,
            desconto_percentual=Decimal(state.get("desconto_percentual", 0)),
            observacoes=state.get("observacoes"),
            validade_dias=state.get("validade_dias", 7),
        )
        
        # Clear wizard state
        _clear_wizard_state(user.id)
        
        # Redirect to cotação detail or list
        return RedirectResponse(url=f"/web/cotacoes?created={cotacao.id}", status_code=302)
        
    except ValueError as e:
        return _flash_error(request, user, str(e))
    except Exception as e:
        logger.error(f"Error creating cotação: {e}", exc_info=True)
        return _flash_error(request, user, "Erro ao criar cotação. Tente novamente.")


# =============================================================================
# Stub Endpoints for Alert Actions
# =============================================================================

@web_router.post("/alerts/{alert_id}/create-purchase-order", response_class=HTMLResponse)
async def create_purchase_order_stub(
    request: Request,
    alert_id: UUID,
    user: UserClaims = Depends(require_web_user),
):
    """Stub endpoint: Create purchase order from alert."""
    context = get_template_context(
        request,
        user=user,
        flash_message="Funcionalidade em desenvolvimento. Em breve você poderá gerar pedidos de compra automaticamente.",
        flash_type="info",
    )
    response = templates.TemplateResponse("partials/flash.html", context)
    response.headers["HX-Trigger"] = "showToast"
    return response


@web_router.get("/alerts/{alert_id}/adjust-price", response_class=HTMLResponse)
async def adjust_price_stub(
    request: Request,
    alert_id: UUID,
    user: UserClaims = Depends(require_web_user),
):
    """Stub endpoint: Adjust price modal."""
    context = get_template_context(
        request,
        user=user,
        flash_message="Funcionalidade em desenvolvimento. Em breve você poderá ajustar preços diretamente dos alertas.",
        flash_type="info",
    )
    response = templates.TemplateResponse("partials/flash.html", context)
    response.headers["HX-Trigger"] = "showToast"
    return response


@web_router.post("/insights/{insight_id}/create-quotation", response_class=HTMLResponse)
async def create_quotation_from_insight_stub(
    request: Request,
    insight_id: UUID,
    user: UserClaims = Depends(require_web_user),
):
    """Stub endpoint: Create quotation from insight."""
    context = get_template_context(
        request,
        user=user,
        flash_message="Funcionalidade em desenvolvimento. Em breve você poderá criar cotações sugeridas automaticamente.",
        flash_type="info",
    )
    response = templates.TemplateResponse("partials/flash.html", context)
    response.headers["HX-Trigger"] = "showToast"
    return response


# =============================================================================
# Wizard State Management
# =============================================================================

def _get_wizard_state_key(user_id: UUID) -> str:
    """Get wizard state key for user."""
    return f"wizard_{user_id}"


def _get_wizard_state(user_id: UUID) -> dict[str, Any]:
    """Get wizard state for user."""
    key = _get_wizard_state_key(user_id)
    return _wizard_states.get(key, {
        "step": 1,
        "cliente_id": None,
        "obra_id": None,
        "itens": [],
        "desconto_percentual": Decimal("0"),
        "observacoes": "",
        "validade_dias": 7,
    })


def _save_wizard_state(user_id: UUID, state: dict[str, Any]):
    """Save wizard state for user."""
    key = _get_wizard_state_key(user_id)
    _wizard_states[key] = state


def _clear_wizard_state(user_id: UUID):
    """Clear wizard state for user."""
    key = _get_wizard_state_key(user_id)
    _wizard_states.pop(key, None)


def _calculate_cotacao_summary(state: dict[str, Any], db: Session, tenant_id: UUID) -> dict[str, Any]:
    """Calculate summary from wizard state."""
    subtotal = Decimal("0")
    produtos_info = {}
    
    for item in state.get("itens", []):
        produto_id = UUID(item["produto_id"])
        quantidade = Decimal(str(item["quantidade"]))
        preco_unitario = Decimal(str(item.get("preco_unitario", 0)))
        desconto_item = Decimal(str(item.get("desconto_percentual", 0)))
        
        valor_item = quantidade * preco_unitario * (1 - desconto_item / 100)
        subtotal += valor_item
        
        if produto_id not in produtos_info:
            produto = db.query(Produto).filter(Produto.id == produto_id, Produto.tenant_id == tenant_id).first()
            if produto:
                produtos_info[str(produto_id)] = produto
    
    desconto_percentual = Decimal(str(state.get("desconto_percentual", 0)))
    desconto_valor = subtotal * (desconto_percentual / 100)
    total = subtotal - desconto_valor
    
    return {
        "subtotal": subtotal,
        "desconto_percentual": desconto_percentual,
        "desconto_valor": desconto_valor,
        "total": total,
        "itens_count": len(state.get("itens", [])),
        "produtos_info": produtos_info,
    }


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
