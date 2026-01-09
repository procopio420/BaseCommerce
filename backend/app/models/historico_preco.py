from sqlalchemy import Column, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from basecore.db import Base
from app.models.base import BaseModelMixin


class HistoricoPreco(Base, BaseModelMixin):
    __tablename__ = "historico_precos"

    tenant_id = Column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    produto_id = Column(
        UUID(as_uuid=True), ForeignKey("produtos.id", ondelete="CASCADE"), nullable=False
    )
    preco = Column(Numeric(10, 2), nullable=False)
    usuario_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))

    tenant = relationship("Tenant", backref="historico_precos")
    produto = relationship("Produto", back_populates="historico_precos")
    usuario = relationship("User")
