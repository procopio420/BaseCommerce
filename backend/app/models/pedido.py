from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from basecore.db import Base
from app.models.base import BaseModelMixin


class Pedido(Base, BaseModelMixin):
    __tablename__ = "pedidos"

    tenant_id = Column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    cotacao_id = Column(UUID(as_uuid=True), ForeignKey("cotacoes.id"))
    cliente_id = Column(UUID(as_uuid=True), ForeignKey("clientes.id"), nullable=False)
    obra_id = Column(UUID(as_uuid=True), ForeignKey("obras.id"))
    numero = Column(String(50), nullable=False)
    status = Column(
        String(20), nullable=False, default="pendente"
    )  # pendente, em_preparacao, saiu_entrega, entregue, cancelado
    desconto_percentual = Column(Numeric(5, 2), default=0)
    observacoes = Column(Text)
    usuario_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    entregue_em = Column(DateTime(timezone=True))

    tenant = relationship("Tenant", backref="pedidos")
    cotacao = relationship("Cotacao")
    cliente = relationship("Cliente")
    obra = relationship("Obra")
    usuario = relationship("User")
    itens = relationship(
        "PedidoItem",
        back_populates="pedido",
        cascade="all, delete-orphan",
        order_by="PedidoItem.ordem",
    )

    __table_args__ = (
        Index("idx_pedidos_tenant_status", "tenant_id", "status"),
        Index("idx_pedidos_cliente", "tenant_id", "cliente_id"),
        Index("idx_pedidos_created", "tenant_id", "created_at"),
        Index("idx_pedidos_tenant_numero", "tenant_id", "numero", unique=True),
    )


class PedidoItem(Base, BaseModelMixin):
    __tablename__ = "pedido_itens"

    tenant_id = Column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    pedido_id = Column(
        UUID(as_uuid=True), ForeignKey("pedidos.id", ondelete="CASCADE"), nullable=False
    )
    produto_id = Column(UUID(as_uuid=True), ForeignKey("produtos.id"), nullable=False)
    quantidade = Column(Numeric(10, 3), nullable=False)
    preco_unitario = Column(Numeric(10, 2), nullable=False)
    desconto_percentual = Column(Numeric(5, 2), default=0)
    valor_total = Column(Numeric(10, 2), nullable=False)
    observacoes = Column(Text)
    ordem = Column(Integer, default=0)

    tenant = relationship("Tenant", backref="pedido_itens")
    pedido = relationship("Pedido", back_populates="itens")
    produto = relationship("Produto")

    __table_args__ = (Index("idx_pedido_itens_pedido", "tenant_id", "pedido_id"),)
