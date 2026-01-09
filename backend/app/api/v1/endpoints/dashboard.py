from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from app.models.cotacao import Cotacao
from app.models.pedido import Pedido
from app.models.user import User
from basecore.db import get_db
from basecore.deps import get_current_user, get_tenant_id

router = APIRouter()


@router.get("/", response_model=dict[str, Any])
async def get_dashboard(
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Dashboard simples com:
    - Cotações do dia
    - Pedidos do dia
    - Receita da semana (soma de pedidos entregues)
    """
    hoje = datetime.utcnow().date()
    inicio_semana = hoje - timedelta(days=hoje.weekday())

    # Converte tenant_id de string para UUID
    tenant_uuid = UUID(tenant_id)
    
    # Cotações do dia
    cotacoes_hoje = (
        db.query(func.count(Cotacao.id))
        .filter(and_(Cotacao.tenant_id == tenant_uuid, func.date(Cotacao.created_at) == hoje))
        .scalar()
        or 0
    )

    # Pedidos do dia
    pedidos_hoje = (
        db.query(func.count(Pedido.id))
        .filter(and_(Pedido.tenant_id == tenant_uuid, func.date(Pedido.created_at) == hoje))
        .scalar()
        or 0
    )

    # Receita da semana (soma de pedidos entregues)
    # Para calcular receita, precisamos somar os itens dos pedidos
    # Por enquanto, retornamos contagem simples
    # TODO: Calcular receita real somando pedido_itens.valor_total

    pedidos_semana = (
        db.query(func.count(Pedido.id))
        .filter(
            and_(
                Pedido.tenant_id == tenant_uuid,
                Pedido.status == "entregue",
                func.date(Pedido.entregue_em) >= inicio_semana,
            )
        )
        .scalar()
        or 0
    )

    # Cotações recentes (últimas 5)
    cotacoes_recentes = (
        db.query(Cotacao)
        .filter(Cotacao.tenant_id == tenant_uuid)
        .order_by(Cotacao.created_at.desc())
        .limit(5)
        .all()
    )

    cotacoes_recentes_data = [
        {
            "id": str(cotacao.id),
            "numero": cotacao.numero,
            "cliente_id": str(cotacao.cliente_id),
            "status": cotacao.status,
            "created_at": cotacao.created_at.isoformat(),
        }
        for cotacao in cotacoes_recentes
    ]

    return {
        "cotacoes_hoje": cotacoes_hoje,
        "pedidos_hoje": pedidos_hoje,
        "pedidos_semana": pedidos_semana,
        "cotacoes_recentes": cotacoes_recentes_data,
    }
