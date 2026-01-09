from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.application.services.pedido_service import PedidoService
from basecore.db import get_db
from basecore.deps import get_current_user, get_tenant_id
from app.domain.pedido.exceptions import (
    CotacaoNaoAprovadaException,
    CotacaoSemItensException,
    PedidoNaoPodeSerCanceladoException,
)
from app.models.pedido import Pedido
from app.models.user import User
from app.schemas.pedido import PedidoCreate, PedidoResponse, PedidoUpdate

router = APIRouter()


@router.get("/", response_model=list[PedidoResponse])
async def list_pedidos(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status_filter: str | None = None,
    cliente_id: UUID | None = None,
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lista pedidos do tenant"""
    tenant_uuid = UUID(tenant_id)
    query = db.query(Pedido).filter(Pedido.tenant_id == tenant_uuid)

    if status_filter:
        query = query.filter(Pedido.status == status_filter)

    if cliente_id:
        query = query.filter(Pedido.cliente_id == cliente_id)

    pedidos = query.order_by(Pedido.created_at.desc()).offset(skip).limit(limit).all()
    return pedidos


@router.get("/{pedido_id}", response_model=PedidoResponse)
async def get_pedido(
    pedido_id: UUID,
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Busca pedido por ID com itens"""
    tenant_uuid = UUID(tenant_id)
    pedido = (
        db.query(Pedido).filter(Pedido.id == pedido_id, Pedido.tenant_id == tenant_uuid).first()
    )

    if not pedido:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido não encontrado")

    return pedido


@router.post("/", response_model=PedidoResponse, status_code=status.HTTP_201_CREATED)
async def create_pedido(
    pedido_data: PedidoCreate,
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cria novo pedido diretamente (sem cotação)"""
    service = PedidoService(db)

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
            for item in pedido_data.itens
        ]

        pedido = service.criar_pedido(
            tenant_id=tenant_uuid,
            cliente_id=pedido_data.cliente_id,
            usuario_id=current_user.id,
            itens=itens,
            obra_id=pedido_data.obra_id,
            cotacao_id=pedido_data.cotacao_id,
            desconto_percentual=pedido_data.desconto_percentual,
            observacoes=pedido_data.observacoes,
        )

        return pedido

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post(
    "/from-cotacao/{cotacao_id}", response_model=PedidoResponse, status_code=status.HTTP_201_CREATED
)
async def criar_pedido_from_cotacao(
    cotacao_id: UUID,
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Converte cotação aprovada em pedido (1 clique).
    Esta é a funcionalidade principal do MVP 1.
    """
    service = PedidoService(db)

    try:
        # Converte tenant_id de string para UUID
        tenant_uuid = UUID(tenant_id)

        pedido = service.converter_cotacao_em_pedido(
            cotacao_id=cotacao_id, tenant_id=tenant_uuid, usuario_id=current_user.id
        )

        return pedido

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except (CotacaoNaoAprovadaException, CotacaoSemItensException) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    # Nota: CotacaoJaConvertidaException não é mais lançada porque o endpoint é idempotente
    # O serviço retorna o pedido existente se a cotação já foi convertida


@router.put("/{pedido_id}", response_model=PedidoResponse)
async def update_pedido(
    pedido_id: UUID,
    pedido_data: PedidoUpdate,
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Atualiza pedido (apenas status e campos permitidos)"""
    service = PedidoService(db)
    tenant_uuid = UUID(tenant_id)

    # Se status foi fornecido, usa o método específico
    if pedido_data.status is not None:
        try:
            pedido = service.atualizar_status_pedido(
                pedido_id=pedido_id, tenant_id=tenant_uuid, novo_status=pedido_data.status
            )

            # Se houver outros campos para atualizar, atualiza diretamente no modelo
            # (apenas campos não críticos)
            if pedido_data.observacoes is not None:
                pedido.observacoes = pedido_data.observacoes

            db.commit()
            db.refresh(pedido)

            return pedido

        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    else:
        # Atualiza apenas campos não críticos
        pedido = (
            db.query(Pedido).filter(Pedido.id == pedido_id, Pedido.tenant_id == tenant_uuid).first()
        )

        if not pedido:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Pedido não encontrado"
            )

        if pedido.status in ["entregue", "cancelado"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Não é possível atualizar pedido entregue ou cancelado",
            )

        if pedido_data.observacoes is not None:
            pedido.observacoes = pedido_data.observacoes

        db.commit()
        db.refresh(pedido)

        return pedido


@router.post("/{pedido_id}/cancelar", response_model=PedidoResponse)
async def cancelar_pedido(
    pedido_id: UUID,
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cancela pedido"""
    service = PedidoService(db)

    try:
        # Converte tenant_id de string para UUID
        tenant_uuid = UUID(tenant_id)

        pedido = service.cancelar_pedido(pedido_id=pedido_id, tenant_id=tenant_uuid)

        return pedido

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PedidoNaoPodeSerCanceladoException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
