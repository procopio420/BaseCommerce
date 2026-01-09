"""
Model de Fornecedor

Armazena dados de fornecedores.
Consumido pelo Pricing & Supplier Intelligence Engine para comparação de preços.
"""

from sqlalchemy import Boolean, Column, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from basecore.db import Base
from app.models.base import BaseModelMixin


class Fornecedor(Base, BaseModelMixin):
    __tablename__ = "fornecedores"

    tenant_id = Column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    nome = Column(String(255), nullable=False)
    documento = Column(String(20))  # CNPJ
    email = Column(String(255))
    telefone = Column(String(20))
    endereco = Column(Text)
    ativo = Column(Boolean, default=True)

    tenant = relationship("Tenant", backref="fornecedores")
    precos = relationship(
        "FornecedorPreco", back_populates="fornecedor", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_fornecedores_tenant_ativo", "tenant_id", "ativo"),
        Index("idx_fornecedores_tenant_documento", "tenant_id", "documento", unique=True),
    )


class FornecedorPreco(Base, BaseModelMixin):
    __tablename__ = "fornecedor_precos"

    tenant_id = Column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    fornecedor_id = Column(
        UUID(as_uuid=True), ForeignKey("fornecedores.id", ondelete="CASCADE"), nullable=False
    )
    produto_id = Column(
        UUID(as_uuid=True), ForeignKey("produtos.id", ondelete="CASCADE"), nullable=False
    )
    preco = Column(Numeric(10, 2), nullable=False)
    quantidade_minima = Column(Numeric(10, 3))  # Quantidade mínima de compra
    prazo_pagamento = Column(Numeric(5, 0))  # Dias para pagamento
    valido = Column(Boolean, default=True)  # Preço ainda válido

    tenant = relationship("Tenant", backref="fornecedor_precos")
    fornecedor = relationship("Fornecedor", back_populates="precos")
    produto = relationship("Produto", backref="fornecedor_precos")

    __table_args__ = (
        Index(
            "idx_fornecedor_precos_tenant_fornecedor_produto",
            "tenant_id",
            "fornecedor_id",
            "produto_id",
        ),
        Index("idx_fornecedor_precos_tenant_produto", "tenant_id", "produto_id"),
        Index("idx_fornecedor_precos_valido", "tenant_id", "valido"),
    )
