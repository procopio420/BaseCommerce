from sqlalchemy import Boolean, Column, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from basecore.db import Base
from app.models.base import BaseModelMixin


class Produto(Base, BaseModelMixin):
    __tablename__ = "produtos"

    tenant_id = Column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    codigo = Column(String(50))
    nome = Column(String(255), nullable=False)
    descricao = Column(Text)
    unidade = Column(String(20), nullable=False)  # 'UN', 'KG', 'M', 'M2', 'M3'
    preco_base = Column(Numeric(10, 2), nullable=False)
    ativo = Column(Boolean, default=True)

    tenant = relationship("Tenant", backref="produtos")
    historico_precos = relationship(
        "HistoricoPreco", back_populates="produto", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_produtos_tenant_ativo", "tenant_id", "ativo"),
        Index("idx_produtos_tenant_codigo", "tenant_id", "codigo", unique=True),
    )
