from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from basecore.db import get_db
from basecore.deps import get_current_user, get_tenant_id
from app.models.cliente import Cliente
from app.models.obra import Obra
from app.models.user import User
from app.schemas.obra import ObraCreate, ObraResponse, ObraUpdate

router = APIRouter()


@router.get("/", response_model=list[ObraResponse])
async def list_obras(
    cliente_id: UUID | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lista obras do tenant"""
    query = db.query(Obra).filter(Obra.tenant_id == tenant_id)

    if cliente_id:
        query = query.filter(Obra.cliente_id == cliente_id)

    obras = query.order_by(Obra.nome).offset(skip).limit(limit).all()
    return obras


@router.get("/{obra_id}", response_model=ObraResponse)
async def get_obra(
    obra_id: UUID,
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Busca obra por ID"""
    obra = db.query(Obra).filter(Obra.id == obra_id, Obra.tenant_id == tenant_id).first()

    if not obra:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Obra não encontrada")

    return obra


@router.post("/", response_model=ObraResponse, status_code=status.HTTP_201_CREATED)
async def create_obra(
    obra_data: ObraCreate,
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cria nova obra"""
    # Verifica se cliente existe e pertence ao tenant
    cliente = (
        db.query(Cliente)
        .filter(Cliente.id == obra_data.cliente_id, Cliente.tenant_id == tenant_id)
        .first()
    )

    if not cliente:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado")

    obra = Obra(tenant_id=tenant_id, **obra_data.model_dump())

    db.add(obra)
    db.commit()
    db.refresh(obra)

    return obra


@router.put("/{obra_id}", response_model=ObraResponse)
async def update_obra(
    obra_id: UUID,
    obra_data: ObraUpdate,
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Atualiza obra"""
    obra = db.query(Obra).filter(Obra.id == obra_id, Obra.tenant_id == tenant_id).first()

    if not obra:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Obra não encontrada")

    update_data = obra_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(obra, field, value)

    db.commit()
    db.refresh(obra)

    return obra


@router.delete("/{obra_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_obra(
    obra_id: UUID,
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Deleta obra"""
    obra = db.query(Obra).filter(Obra.id == obra_id, Obra.tenant_id == tenant_id).first()

    if not obra:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Obra não encontrada")

    db.delete(obra)
    db.commit()

    return None
