from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from basecore.db import get_db
from basecore.deps import get_current_user, get_tenant_id
from app.models.cliente import Cliente
from app.models.user import User
from app.schemas.cliente import ClienteCreate, ClienteResponse, ClienteUpdate

router = APIRouter()


@router.get("/", response_model=list[ClienteResponse])
async def list_clientes(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    search: str | None = None,
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lista clientes do tenant"""
    query = db.query(Cliente).filter(Cliente.tenant_id == tenant_id)

    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            or_(
                Cliente.nome.ilike(search_filter),
                Cliente.documento.ilike(search_filter),
                Cliente.email.ilike(search_filter),
            )
        )

    clientes = query.order_by(Cliente.nome).offset(skip).limit(limit).all()
    return clientes


@router.get("/{cliente_id}", response_model=ClienteResponse)
async def get_cliente(
    cliente_id: UUID,
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Busca cliente por ID"""
    cliente = (
        db.query(Cliente).filter(Cliente.id == cliente_id, Cliente.tenant_id == tenant_id).first()
    )

    if not cliente:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado")

    return cliente


@router.post("/", response_model=ClienteResponse, status_code=status.HTTP_201_CREATED)
async def create_cliente(
    cliente_data: ClienteCreate,
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cria novo cliente"""
    # Verifica se já existe cliente com mesmo documento no tenant
    existing = (
        db.query(Cliente)
        .filter(Cliente.tenant_id == tenant_id, Cliente.documento == cliente_data.documento)
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Cliente com este documento já existe"
        )

    cliente = Cliente(tenant_id=tenant_id, **cliente_data.model_dump())

    db.add(cliente)
    db.commit()
    db.refresh(cliente)

    return cliente


@router.put("/{cliente_id}", response_model=ClienteResponse)
async def update_cliente(
    cliente_id: UUID,
    cliente_data: ClienteUpdate,
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Atualiza cliente"""
    cliente = (
        db.query(Cliente).filter(Cliente.id == cliente_id, Cliente.tenant_id == tenant_id).first()
    )

    if not cliente:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado")

    update_data = cliente_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(cliente, field, value)

    db.commit()
    db.refresh(cliente)

    return cliente


@router.delete("/{cliente_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cliente(
    cliente_id: UUID,
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Deleta cliente"""
    cliente = (
        db.query(Cliente).filter(Cliente.id == cliente_id, Cliente.tenant_id == tenant_id).first()
    )

    if not cliente:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado")

    db.delete(cliente)
    db.commit()

    return None
