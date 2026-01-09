"""
Serviço de aplicação para pedidos

Orquestra a criação, conversão de cotações e gestão de pedidos.
Não contém lógica de domínio (fica no domínio), apenas orquestra.

NOTE: Engine calls removed - all engine processing now happens via events.
Verticals only publish events to outbox, engines consume asynchronously.
"""

import logging
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.domain.pedido.exceptions import (
    CotacaoNaoAprovadaException,
    CotacaoSemItensException,
    PedidoNaoPodeSerCanceladoException,
)
from app.domain.pedido.validators import calcular_valor_total_item
from app.models.cliente import Cliente
from app.models.cotacao import Cotacao, CotacaoItem
from app.models.obra import Obra
from app.models.pedido import Pedido, PedidoItem
from app.models.produto import Produto
from app.platform.events.publisher import publish_event
from app.platform.events.types import EventType

logger = logging.getLogger(__name__)


class PedidoService:
    """Serviço de aplicação para gestão de pedidos"""

    def __init__(self, db: Session):
        self.db = db
        # NOTE: Engine implementations removed - all processing via events

    def gerar_numero_pedido(self, tenant_id: UUID) -> str:
        """
        Gera número sequencial de pedido para o tenant.

        Formato: PED-001, PED-002, etc.
        """
        ultimo_pedido = (
            self.db.query(Pedido)
            .filter(Pedido.tenant_id == tenant_id)
            .order_by(Pedido.created_at.desc())
            .first()
        )

        if ultimo_pedido and ultimo_pedido.numero:
            try:
                ultimo_numero = int(ultimo_pedido.numero.split("-")[-1])
                novo_numero = ultimo_numero + 1
            except (ValueError, IndexError):
                novo_numero = 1
        else:
            novo_numero = 1

        return f"PED-{novo_numero:03d}"

    def criar_pedido(
        self,
        tenant_id: UUID,
        cliente_id: UUID,
        usuario_id: UUID,
        itens: list,
        obra_id: UUID | None = None,
        cotacao_id: UUID | None = None,
        desconto_percentual: Decimal = Decimal("0"),
        observacoes: str | None = None,
    ) -> Pedido:
        """
        Cria novo pedido diretamente (sem cotação).

        Validações:
        - Cliente deve existir
        - Obra deve existir e pertencer ao cliente (se fornecida)
        - Produtos devem existir e estar ativos
        - Deve ter pelo menos 1 item
        """
        # Valida cliente
        cliente = (
            self.db.query(Cliente)
            .filter(Cliente.id == cliente_id, Cliente.tenant_id == tenant_id)
            .first()
        )

        if not cliente:
            raise ValueError("Cliente não encontrado")

        # Valida obra se fornecida
        if obra_id:
            obra = (
                self.db.query(Obra)
                .filter(
                    Obra.id == obra_id, Obra.tenant_id == tenant_id, Obra.cliente_id == cliente_id
                )
                .first()
            )

            if not obra:
                raise ValueError("Obra não encontrada ou não pertence ao cliente")

        # Valida produtos e cria itens
        pedido_itens = []
        for idx, item_data in enumerate(itens):
            produto = (
                self.db.query(Produto)
                .filter(
                    Produto.id == item_data["produto_id"],
                    Produto.tenant_id == tenant_id,
                    Produto.ativo is True,
                )
                .first()
            )

            if not produto:
                raise ValueError(f"Produto {item_data['produto_id']} não encontrado ou inativo")

            # Usa preço do produto se não fornecido ou se fornecido mas é 0
            preco_unitario_fornecido = item_data.get("preco_unitario")
            if preco_unitario_fornecido is None or preco_unitario_fornecido == 0:
                preco_unitario = produto.preco_base
            else:
                preco_unitario = preco_unitario_fornecido
            desconto_item = item_data.get("desconto_percentual", Decimal("0"))

            valor_total = calcular_valor_total_item(
                item_data["quantidade"], preco_unitario, desconto_item
            )

            pedido_itens.append(
                {
                    "produto": produto,
                    "quantidade": item_data["quantidade"],
                    "preco_unitario": preco_unitario,
                    "desconto_percentual": desconto_item,
                    "valor_total": valor_total,
                    "observacoes": item_data.get("observacoes"),
                    "ordem": item_data.get("ordem", idx),
                }
            )

        if not pedido_itens:
            raise ValueError("Pedido deve ter pelo menos um item")

        # Cria pedido
        numero = self.gerar_numero_pedido(tenant_id)

        pedido = Pedido(
            tenant_id=tenant_id,
            cotacao_id=cotacao_id,
            cliente_id=cliente_id,
            obra_id=obra_id,
            numero=numero,
            status="pendente",
            desconto_percentual=desconto_percentual,
            observacoes=observacoes,
            usuario_id=usuario_id,
        )

        self.db.add(pedido)
        self.db.flush()

        # Cria itens
        for item_data in pedido_itens:
            item = PedidoItem(
                tenant_id=tenant_id,
                pedido_id=pedido.id,
                produto_id=item_data["produto"].id,
                quantidade=item_data["quantidade"],
                preco_unitario=item_data["preco_unitario"],
                desconto_percentual=item_data["desconto_percentual"],
                valor_total=item_data["valor_total"],
                observacoes=item_data["observacoes"],
                ordem=item_data["ordem"],
            )
            self.db.add(item)

        self.db.commit()
        self.db.refresh(pedido)

        return pedido

    def converter_cotacao_em_pedido(
        self,
        cotacao_id: UUID,
        tenant_id: UUID,
        usuario_id: UUID,
    ) -> Pedido:
        """
        Converte cotação aprovada em pedido (1 clique).

        Esta é a funcionalidade principal do MVP 1.

        Endpoint IDEMPOTENTE: Se a cotação já foi convertida, retorna o pedido existente.
        Operação TRANSACIONAL com lock pessimista para evitar condições de corrida.

        Validações:
        - Cotação deve existir
        - Cotação deve estar aprovada
        - Cotação deve ter pelo menos 1 item

        Processo:
        1. Busca cotação com lock pessimista (com proteção contra concorrência)
        2. Verifica se já foi convertida (idempotência)
        3. Valida status (deve estar aprovada)
        4. Cria pedido copiando dados da cotação (transacional)
        5. Copia todos os itens da cotação para o pedido (preços "congelados")
        6. Atualiza cotação para status "convertida"
        7. Publica evento quote_converted (engines processam via outbox)
        """
        # Busca cotação com LOCK PESSIMISTA (proteção contra concorrência)
        cotacao = (
            self.db.query(Cotacao)
            .filter(Cotacao.id == cotacao_id, Cotacao.tenant_id == tenant_id)
            .with_for_update()
            .first()
        )

        if not cotacao:
            raise ValueError("Cotação não encontrada")

        # IDEMPOTÊNCIA: Se já foi convertida, retorna o pedido existente
        pedido_existente = (
            self.db.query(Pedido)
            .filter(Pedido.cotacao_id == cotacao_id, Pedido.tenant_id == tenant_id)
            .first()
        )

        if pedido_existente:
            return pedido_existente

        # Validações de domínio
        if cotacao.status != "aprovada":
            raise CotacaoNaoAprovadaException(
                "Apenas cotações aprovadas podem ser convertidas em pedido"
            )

        # Busca itens da cotação
        cotacao_itens = (
            self.db.query(CotacaoItem)
            .filter(CotacaoItem.cotacao_id == cotacao_id, CotacaoItem.tenant_id == tenant_id)
            .order_by(CotacaoItem.ordem)
            .all()
        )

        if not cotacao_itens:
            raise CotacaoSemItensException("Cotação não possui itens")

        # OPERAÇÃO TRANSACIONAL
        try:
            numero = self.gerar_numero_pedido(tenant_id)

            pedido = Pedido(
                tenant_id=tenant_id,
                cotacao_id=cotacao.id,
                cliente_id=cotacao.cliente_id,
                obra_id=cotacao.obra_id,
                numero=numero,
                status="pendente",
                desconto_percentual=cotacao.desconto_percentual,
                observacoes=cotacao.observacoes,
                usuario_id=usuario_id,
            )

            self.db.add(pedido)
            self.db.flush()

            # Copia itens da cotação para o pedido
            for idx, cotacao_item in enumerate(cotacao_itens):
                pedido_item = PedidoItem(
                    tenant_id=tenant_id,
                    pedido_id=pedido.id,
                    produto_id=cotacao_item.produto_id,
                    quantidade=cotacao_item.quantidade,
                    preco_unitario=cotacao_item.preco_unitario,
                    desconto_percentual=cotacao_item.desconto_percentual,
                    valor_total=cotacao_item.valor_total,
                    observacoes=cotacao_item.observacoes,
                    ordem=cotacao_item.ordem if cotacao_item.ordem > 0 else idx,
                )
                self.db.add(pedido_item)

            # Atualiza status da cotação
            cotacao.status = "convertida"
            cotacao.convertida_em = datetime.utcnow()

            # PUBLICA EVENTO: quote_converted
            # Engines consume this event asynchronously via outbox
            # Payload contains all data needed - no vertical DB queries by engines
            try:
                publish_event(
                    db=self.db,
                    event_type=EventType.QUOTE_CONVERTED,
                    tenant_id=tenant_id,
                    payload={
                        "quote_id": str(cotacao.id),
                        "order_id": str(pedido.id),
                        "client_id": str(cotacao.cliente_id),
                        "user_id": str(usuario_id),
                        "work_id": str(pedido.obra_id) if pedido.obra_id else None,
                        "total_value": str(sum(item.valor_total for item in pedido.itens)),
                        "converted_at": datetime.utcnow().isoformat(),
                        "vertical": "materials",
                        "items": [
                            {
                                "product_id": str(item.produto_id),
                                "quantity": str(item.quantidade),
                                "unit_price": str(item.preco_unitario),
                                "total_value": str(item.valor_total),
                            }
                            for item in pedido.itens
                        ],
                    },
                    version="1.0",
                )
            except Exception as e:
                logger.warning(
                    "Falha ao publicar evento quote_converted",
                    extra={
                        "tenant_id": str(tenant_id),
                        "quote_id": str(cotacao.id),
                        "order_id": str(pedido.id),
                        "error": str(e),
                    },
                    exc_info=True,
                )

            # COMMIT TRANSACIONAL
            self.db.commit()
            self.db.refresh(pedido)

            return pedido

        except Exception:
            self.db.rollback()
            raise

    def cancelar_pedido(self, pedido_id: UUID, tenant_id: UUID) -> Pedido:
        """
        Cancela pedido.

        Validações:
        - Pedido deve existir
        - Pedido não pode estar entregue
        """
        pedido = (
            self.db.query(Pedido)
            .filter(Pedido.id == pedido_id, Pedido.tenant_id == tenant_id)
            .first()
        )

        if not pedido:
            raise ValueError("Pedido não encontrado")

        if pedido.status == "entregue":
            raise PedidoNaoPodeSerCanceladoException("Não é possível cancelar pedido já entregue")

        pedido.status = "cancelado"

        self.db.commit()
        self.db.refresh(pedido)

        return pedido

    def atualizar_status_pedido(
        self,
        pedido_id: UUID,
        tenant_id: UUID,
        novo_status: str,
        usuario_id: UUID | None = None,
    ) -> Pedido:
        """
        Atualiza status do pedido.

        Validações:
        - Pedido deve existir
        - Status deve ser válido

        Events published:
        - sale_recorded: when status becomes "entregue"
        - order_status_changed: on any status change
        """
        pedido = (
            self.db.query(Pedido)
            .filter(Pedido.id == pedido_id, Pedido.tenant_id == tenant_id)
            .first()
        )

        if not pedido:
            raise ValueError("Pedido não encontrado")

        status_validos = ["pendente", "em_preparacao", "saiu_entrega", "entregue", "cancelado"]
        if novo_status not in status_validos:
            raise ValueError(f"Status inválido: {novo_status}")

        status_antigo = pedido.status

        # Se status for "entregue", registra data de entrega e publica sale_recorded
        if novo_status == "entregue":
            pedido.entregue_em = datetime.utcnow()

            # PUBLICA EVENTO: sale_recorded
            # This event has ALL data for engines to compute stock/sales insights
            try:
                publish_event(
                    db=self.db,
                    event_type=EventType.SALE_RECORDED,
                    tenant_id=tenant_id,
                    payload={
                        "order_id": str(pedido_id),
                        "quote_id": str(pedido.cotacao_id) if pedido.cotacao_id else None,
                        "client_id": str(pedido.cliente_id),
                        "work_id": str(pedido.obra_id) if pedido.obra_id else None,
                        "delivered_at": pedido.entregue_em.isoformat(),
                        "total_value": str(sum(item.valor_total for item in pedido.itens)),
                        "vertical": "materials",
                        "items": [
                            {
                                "product_id": str(item.produto_id),
                                "quantity": str(item.quantidade),
                                "unit_price": str(item.preco_unitario),
                                "total_value": str(item.valor_total),
                            }
                            for item in pedido.itens
                        ],
                    },
                    version="1.0",
                )
            except Exception as e:
                logger.warning(
                    "Falha ao publicar evento sale_recorded",
                    extra={
                        "tenant_id": str(tenant_id),
                        "pedido_id": str(pedido_id),
                        "error": str(e),
                    },
                    exc_info=True,
                )

        # PUBLICA EVENTO: order_status_changed
        try:
            publish_event(
                db=self.db,
                event_type=EventType.ORDER_STATUS_CHANGED,
                tenant_id=tenant_id,
                payload={
                    "order_id": str(pedido_id),
                    "old_status": status_antigo,
                    "new_status": novo_status,
                    "changed_at": datetime.utcnow().isoformat(),
                    "changed_by": str(usuario_id) if usuario_id else None,
                    "vertical": "materials",
                },
                version="1.0",
            )
        except Exception as e:
            logger.warning(
                "Falha ao publicar evento order_status_changed",
                extra={"tenant_id": str(tenant_id), "pedido_id": str(pedido_id), "error": str(e)},
                exc_info=True,
            )

        pedido.status = novo_status

        self.db.commit()
        self.db.refresh(pedido)

        return pedido
