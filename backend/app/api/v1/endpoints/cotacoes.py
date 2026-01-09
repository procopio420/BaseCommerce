from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.application.services.cotacao_service import CotacaoService
from basecore.db import get_db
from basecore.deps import get_current_user, get_tenant_id
from app.domain.cotacao.exceptions import (
    CotacaoNaoPodeSerAprovadaException,
    CotacaoNaoPodeSerEditadaException,
    CotacaoNaoPodeSerEnviadaException,
)
from app.models.cotacao import Cotacao
from app.models.user import User
from app.schemas.cotacao import CotacaoCreate, CotacaoResponse, CotacaoUpdate

router = APIRouter()


@router.get("/", response_model=list[CotacaoResponse])
async def list_cotacoes(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status_filter: str | None = None,
    cliente_id: UUID | None = None,
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lista cotações do tenant"""
    tenant_uuid = UUID(tenant_id)
    query = db.query(Cotacao).filter(Cotacao.tenant_id == tenant_uuid)

    if status_filter:
        query = query.filter(Cotacao.status == status_filter)

    if cliente_id:
        query = query.filter(Cotacao.cliente_id == cliente_id)

    cotacoes = query.order_by(Cotacao.created_at.desc()).offset(skip).limit(limit).all()
    return cotacoes


@router.get("/{cotacao_id}", response_model=CotacaoResponse)
async def get_cotacao(
    cotacao_id: UUID,
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Busca cotação por ID com itens"""
    tenant_uuid = UUID(tenant_id)
    cotacao = (
        db.query(Cotacao).filter(Cotacao.id == cotacao_id, Cotacao.tenant_id == tenant_uuid).first()
    )

    if not cotacao:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cotação não encontrada")

    return cotacao


@router.post("/", response_model=CotacaoResponse, status_code=status.HTTP_201_CREATED)
async def create_cotacao(
    cotacao_data: CotacaoCreate,
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cria nova cotação"""
    service = CotacaoService(db)

    try:
        # Converte tenant_id de string para UUID
        tenant_uuid = UUID(tenant_id)

        # Converte schema para formato esperado pelo serviço
        itens = [
            {
                "produto_id": item.produto_id,
                "quantidade": item.quantidade,
                "preco_unitario": item.preco_unitario if item.preco_unitario > 0 else None,
                "desconto_percentual": item.desconto_percentual,
                "observacoes": item.observacoes,
                "ordem": item.ordem,
            }
            for item in cotacao_data.itens
        ]

        cotacao = service.criar_cotacao(
            tenant_id=tenant_uuid,
            cliente_id=cotacao_data.cliente_id,
            usuario_id=current_user.id,
            itens=itens,
            obra_id=cotacao_data.obra_id,
            desconto_percentual=cotacao_data.desconto_percentual,
            observacoes=cotacao_data.observacoes,
            validade_dias=cotacao_data.validade_dias,
        )

        return cotacao

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.put("/{cotacao_id}", response_model=CotacaoResponse)
async def update_cotacao(
    cotacao_id: UUID,
    cotacao_data: CotacaoUpdate,
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Atualiza cotação (apenas se for rascunho)"""
    service = CotacaoService(db)

    try:
        # Converte tenant_id de string para UUID
        tenant_uuid = UUID(tenant_id)

        # Converte schema para formato esperado pelo serviço
        itens = None
        if cotacao_data.itens is not None:
            itens = [
                {
                    "produto_id": item.produto_id,
                    "quantidade": item.quantidade,
                    "preco_unitario": item.preco_unitario if item.preco_unitario > 0 else None,
                    "desconto_percentual": item.desconto_percentual,
                    "observacoes": item.observacoes,
                    "ordem": item.ordem,
                }
                for item in cotacao_data.itens
            ]

        cotacao = service.atualizar_cotacao(
            cotacao_id=cotacao_id,
            tenant_id=tenant_uuid,
            itens=itens,
            desconto_percentual=cotacao_data.desconto_percentual,
            observacoes=cotacao_data.observacoes,
            validade_dias=cotacao_data.validade_dias,
        )

        return cotacao

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except CotacaoNaoPodeSerEditadaException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{cotacao_id}/enviar", response_model=CotacaoResponse)
async def enviar_cotacao(
    cotacao_id: UUID,
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Envia cotação (muda status para 'enviada')"""
    service = CotacaoService(db)

    try:
        # Converte tenant_id de string para UUID
        tenant_uuid = UUID(tenant_id)

        cotacao = service.enviar_cotacao(cotacao_id=cotacao_id, tenant_id=tenant_uuid)

        return cotacao

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except CotacaoNaoPodeSerEnviadaException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{cotacao_id}/aprovar", response_model=CotacaoResponse)
async def aprovar_cotacao(
    cotacao_id: UUID,
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Aprova cotação (muda status para 'aprovada')"""
    service = CotacaoService(db)

    try:
        # Converte tenant_id de string para UUID
        tenant_uuid = UUID(tenant_id)

        cotacao = service.aprovar_cotacao(cotacao_id=cotacao_id, tenant_id=tenant_uuid)

        return cotacao

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except CotacaoNaoPodeSerAprovadaException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{cotacao_id}/cancelar", response_model=CotacaoResponse)
async def cancelar_cotacao(
    cotacao_id: UUID,
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cancela cotação"""
    service = CotacaoService(db)

    try:
        # Converte tenant_id de string para UUID
        tenant_uuid = UUID(tenant_id)

        cotacao = service.cancelar_cotacao(cotacao_id=cotacao_id, tenant_id=tenant_uuid)

        return cotacao

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except CotacaoNaoPodeSerEditadaException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
