from sqlalchemy import Column, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from basecore.db import Base
from app.models.base import BaseModelMixin


class Cliente(Base, BaseModelMixin):
    __tablename__ = "clientes"

    tenant_id = Column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    tipo = Column(String(2), nullable=False)  # 'PF' ou 'PJ'
    nome = Column(String(255), nullable=False)
    documento = Column(String(20), nullable=False)  # CPF ou CNPJ
    email = Column(String(255))
    telefone = Column(String(20))
    endereco = Column(Text)
    cidade = Column(String(100))
    estado = Column(String(2))
    cep = Column(String(10))
    observacoes = Column(Text)

    tenant = relationship("Tenant", backref="clientes")
    obras = relationship("Obra", back_populates="cliente", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_clientes_tenant_documento", "tenant_id", "documento", unique=True),
    )
