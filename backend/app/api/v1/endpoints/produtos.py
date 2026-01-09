from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from basecore.db import get_db
from basecore.deps import get_current_user, get_tenant_id
from app.models.produto import Produto
from app.models.user import User
from app.schemas.produto import ProdutoCreate, ProdutoResponse, ProdutoUpdate

router = APIRouter()


@router.get("/", response_model=list[ProdutoResponse])
async def list_produtos(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    search: str | None = None,
    ativo: bool | None = None,
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lista produtos do tenant"""
    query = db.query(Produto).filter(Produto.tenant_id == tenant_id)

    if ativo is not None:
        query = query.filter(Produto.ativo == ativo)

    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            or_(
                Produto.nome.ilike(search_filter),
                Produto.codigo.ilike(search_filter),
                Produto.descricao.ilike(search_filter),
            )
        )

    produtos = query.order_by(Produto.nome).offset(skip).limit(limit).all()
    return produtos


@router.get("/{produto_id}", response_model=ProdutoResponse)
async def get_produto(
    produto_id: UUID,
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Busca produto por ID"""
    produto = (
        db.query(Produto).filter(Produto.id == produto_id, Produto.tenant_id == tenant_id).first()
    )

    if not produto:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Produto não encontrado")

    return produto


@router.post("/", response_model=ProdutoResponse, status_code=status.HTTP_201_CREATED)
async def create_produto(
    produto_data: ProdutoCreate,
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cria novo produto"""
    # Se código fornecido, verifica se já existe no tenant
    if produto_data.codigo:
        existing = (
            db.query(Produto)
            .filter(Produto.tenant_id == tenant_id, Produto.codigo == produto_data.codigo)
            .first()
        )

        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Produto com este código já existe"
            )

    produto = Produto(tenant_id=tenant_id, **produto_data.model_dump())

    db.add(produto)
    db.commit()
    db.refresh(produto)

    return produto


@router.put("/{produto_id}", response_model=ProdutoResponse)
async def update_produto(
    produto_id: UUID,
    produto_data: ProdutoUpdate,
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Atualiza produto"""
    produto = (
        db.query(Produto).filter(Produto.id == produto_id, Produto.tenant_id == tenant_id).first()
    )

    if not produto:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Produto não encontrado")

    update_data = produto_data.model_dump(exclude_unset=True)

    # Se atualizando código, verifica duplicata
    if "codigo" in update_data and update_data["codigo"]:
        existing = (
            db.query(Produto)
            .filter(
                Produto.tenant_id == tenant_id,
                Produto.codigo == update_data["codigo"],
                Produto.id != produto_id,
            )
            .first()
        )

        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Produto com este código já existe"
            )

    for field, value in update_data.items():
        setattr(produto, field, value)

    db.commit()
    db.refresh(produto)

    return produto


@router.delete("/{produto_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_produto(
    produto_id: UUID,
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Deleta produto (soft delete - marca como inativo)"""
    produto = (
        db.query(Produto).filter(Produto.id == produto_id, Produto.tenant_id == tenant_id).first()
    )

    if not produto:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Produto não encontrado")

    produto.ativo = False
    db.commit()

    return None
