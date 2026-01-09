from sqlalchemy import Boolean, Column, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from basecore.db import Base
from app.models.base import BaseModelMixin


class Obra(Base, BaseModelMixin):
    __tablename__ = "obras"

    tenant_id = Column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    cliente_id = Column(
        UUID(as_uuid=True), ForeignKey("clientes.id", ondelete="CASCADE"), nullable=False
    )
    nome = Column(String(255), nullable=False)
    endereco = Column(Text)
    cidade = Column(String(100))
    estado = Column(String(2))
    observacoes = Column(Text)
    ativa = Column(Boolean, default=True)

    tenant = relationship("Tenant", backref="obras")
    cliente = relationship("Cliente", back_populates="obras")
